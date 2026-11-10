#!/usr/bin/env python3
"""Decide whether a Homebrew formula can be installed on this runner.

Used by .github/workflows/test.yml so CI on an older macOS image skips
formulas whose declared macOS or architecture requirements the runner
cannot satisfy, instead of failing at `brew install`. Formulas the
runner can install (infera, coscad on macos-15) are still tested.

Prefers `brew info --json=v2` when Homebrew can load the formula, because
that is the same requirement brew itself enforces. Falls back to parsing
`depends_on macos:` and `depends_on arch:` in the formula file so the
check can be run and tested without Homebrew (for example on Linux).

Exit codes:
  0  formula is supported on this runner
  2  formula should be skipped (a SKIP notice is printed to stdout)
  1  usage or parse error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Iterable, Optional


# Homebrew macOS marketing-name symbols and their numeric versions, from
# Library/Homebrew/macos_version.rb RELEASES (Homebrew 7, 2026). Keep this
# table in step when Homebrew adds a new macOS name; an unknown symbol is
# an error, not a silent skip or install.
MACOS_RELEASES = {
    "golden_gate": "27",
    "tahoe": "26",
    "sequoia": "15",
    "sonoma": "14",
    "ventura": "13",
    "monterey": "12",
    "big_sur": "11",
    "catalina": "10.15",
    "mojave": "10.14",
    "high_sierra": "10.13",
    "sierra": "10.12",
    "el_capitan": "10.11",
}

# Inverse map for SKIP messages, e.g. 27 -> Golden Gate.
MACOS_NAMES = {version: symbol.replace("_", " ").title() for symbol, version in MACOS_RELEASES.items()}


class CheckError(Exception):
    """Unrecoverable parse or usage failure (exit 1)."""


def parse_version(text: str) -> tuple[int, ...]:
    parts = text.split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise CheckError(f"invalid version {text!r}")
    return tuple(int(part) for part in parts)


def version_at_least(have: str, need: str) -> bool:
    have_parts = parse_version(have)
    need_parts = parse_version(need)
    width = max(len(have_parts), len(need_parts))
    have_parts = have_parts + (0,) * (width - len(have_parts))
    need_parts = need_parts + (0,) * (width - len(need_parts))
    return have_parts >= need_parts


def macos_symbol_version(symbol: str) -> str:
    try:
        return MACOS_RELEASES[symbol]
    except KeyError as exc:
        raise CheckError(
            f"unknown macOS symbol :{symbol}; update MACOS_RELEASES in "
            "scripts/formula-supported.py to match Homebrew's RELEASES table"
        ) from exc


def normalize_arch(arch: str) -> str:
    aliases = {
        "aarch64": "arm64",
        "arm64": "arm64",
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "x64": "x86_64",
    }
    key = arch.strip().lower()
    if key not in aliases:
        return key
    return aliases[key]


def formula_name(path: str) -> str:
    base = os.path.basename(path)
    if base.endswith(".rb"):
        return base[:-3]
    return base


def macos_label(version: str) -> str:
    # "27" and "27.0" should both show as Golden Gate when that is the
    # marketing name for the major version.
    major = version.split(".")[0]
    for candidate in (version, major):
        name = MACOS_NAMES.get(candidate)
        if name:
            if candidate == version or version == f"{candidate}.0":
                return f"macOS {version} ({name})"
            # A tighter floor such as 27.2 is still Golden Gate.
            if parse_version(version)[:1] == parse_version(candidate):
                return f"macOS {version} ({name})"
    return f"macOS {version}"


def _uncommented_lines(text: str) -> Iterable[str]:
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        yield stripped.split("#", 1)[0].strip()


# depends_on macos: :sequoia
# depends_on macos: ">= :sequoia"
# depends_on macos: ">= 13.3"
# depends_on macos: "12.3"
MACOS_SYMBOL_RE = re.compile(r'^depends_on\s+macos:\s*:([A-Za-z_][A-Za-z0-9_]*)$')
MACOS_SYMBOL_STR_RE = re.compile(
    r'^depends_on\s+macos:\s*["\']>=?\s*:([A-Za-z_][A-Za-z0-9_]*)["\']$'
)
MACOS_VERSION_RE = re.compile(
    r'^depends_on\s+macos:\s*["\'](?:>=\s*)?([0-9]+(?:\.[0-9]+)*)["\']$'
)
ARCH_SINGLE_RE = re.compile(r'^depends_on\s+arch:\s*:([A-Za-z0-9_]+)$')
ARCH_LIST_RE = re.compile(r'^depends_on\s+arch:\s*\[([^\]]+)\]$')
ARCH_ITEM_RE = re.compile(r':([A-Za-z0-9_]+)|["\']([A-Za-z0-9_]+)["\']')


def requirements_from_formula_file(path: str) -> tuple[Optional[str], list[str]]:
    """Return (minimum macOS version or None, allowed archs; empty means any)."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        raise CheckError(f"cannot read {path}: {exc}") from exc

    macos: Optional[str] = None
    archs: list[str] = []
    for line in _uncommented_lines(text):
        m = MACOS_SYMBOL_RE.match(line) or MACOS_SYMBOL_STR_RE.match(line)
        if m:
            ver = macos_symbol_version(m.group(1))
            macos = ver if macos is None else (macos if version_at_least(macos, ver) else ver)
            continue
        m = MACOS_VERSION_RE.match(line)
        if m:
            ver = m.group(1)
            macos = ver if macos is None else (macos if version_at_least(macos, ver) else ver)
            continue
        m = ARCH_SINGLE_RE.match(line)
        if m:
            archs.append(normalize_arch(m.group(1)))
            continue
        m = ARCH_LIST_RE.match(line)
        if m:
            found = [normalize_arch(a or b) for a, b in ARCH_ITEM_RE.findall(m.group(1))]
            if not found:
                raise CheckError(f"could not parse arch list in {path}: {line}")
            archs.extend(found)
            continue
    # de-duplicate archs, keep order
    seen = set()
    unique_archs = []
    for arch in archs:
        if arch not in seen:
            seen.add(arch)
            unique_archs.append(arch)
    return macos, unique_archs


def requirements_from_brew(path: str) -> tuple[Optional[str], list[str]]:
    proc = subprocess.run(
        ["brew", "info", "--json=v2", "--formula", path],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise CheckError(
            f"brew info --json=v2 failed for {path}: {proc.stderr.strip() or proc.stdout.strip() or proc.returncode}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CheckError(f"brew info --json=v2 for {path} was not JSON: {exc}") from exc

    formulae = data.get("formulae") or []
    if not formulae:
        raise CheckError(f"brew info --json=v2 for {path} listed no formulae")

    macos: Optional[str] = None
    archs: list[str] = []
    for formula in formulae:
        for req in formula.get("requirements") or []:
            name = req.get("name")
            version = req.get("version")
            if name == "macos" and version:
                ver = str(version)
                macos = ver if macos is None else (macos if version_at_least(macos, ver) else ver)
            elif name == "arch" and version:
                archs.append(normalize_arch(str(version)))
    seen = set()
    unique_archs = []
    for arch in archs:
        if arch not in seen:
            seen.add(arch)
            unique_archs.append(arch)
    return macos, unique_archs


def load_requirements(path: str, source: str) -> tuple[Optional[str], list[str], str]:
    if source not in {"auto", "brew", "file"}:
        raise CheckError(f"unknown source {source!r}")
    if source == "file":
        macos, archs = requirements_from_formula_file(path)
        return macos, archs, "file"
    if source == "brew":
        macos, archs = requirements_from_brew(path)
        return macos, archs, "brew"
    if shutil.which("brew"):
        try:
            macos, archs = requirements_from_brew(path)
            return macos, archs, "brew"
        except CheckError as exc:
            # Homebrew may be present but unusable on Linux; fall back.
            print(f"warning: {exc}; falling back to parsing {path}", file=sys.stderr)
    macos, archs = requirements_from_formula_file(path)
    return macos, archs, "file"


def detect_macos(override: Optional[str]) -> str:
    if override:
        # Validate early.
        parse_version(override)
        return override
    try:
        proc = subprocess.run(
            ["sw_vers", "-productVersion"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        proc = None
    if proc is not None and proc.returncode == 0 and proc.stdout.strip():
        version = proc.stdout.strip()
        parse_version(version)
        return version
    raise CheckError(
        "cannot detect macOS version (sw_vers failed); pass --macos VERSION, "
        "for example --macos 15.0"
    )


def detect_arch(override: Optional[str]) -> str:
    if override:
        return normalize_arch(override)
    proc = subprocess.run(["uname", "-m"], check=True, capture_output=True, text=True)
    return normalize_arch(proc.stdout.strip())


def evaluate(
    path: str,
    runner_macos: str,
    runner_arch: str,
    source: str,
) -> tuple[int, str]:
    if not os.path.isfile(path):
        raise CheckError(f"formula not found: {path}")
    macos, archs, _used = load_requirements(path, source)
    name = formula_name(path)
    if archs and runner_arch not in archs:
        allowed = ", ".join(archs)
        return (
            2,
            f"SKIP {name}: requires arch {allowed}; runner is {runner_arch}",
        )
    if macos is not None and not version_at_least(runner_macos, macos):
        return (
            2,
            f"SKIP {name}: requires {macos_label(macos)} or later; runner is {runner_macos}",
        )
    return 0, ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether a Homebrew formula can be installed on this runner."
    )
    parser.add_argument("formula", help="path to a formula .rb file")
    parser.add_argument(
        "--macos",
        help="runner macOS product version (default: sw_vers -productVersion)",
    )
    parser.add_argument(
        "--arch",
        help="runner architecture (default: uname -m; aarch64 is treated as arm64)",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "brew", "file"),
        default="auto",
        help="how to read requirements (default: brew info when available, else the formula file)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        runner_macos = detect_macos(args.macos)
        runner_arch = detect_arch(args.arch)
        status, message = evaluate(args.formula, runner_macos, runner_arch, args.source)
    except CheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if message:
        print(message)
    return status


if __name__ == "__main__":
    sys.exit(main())
