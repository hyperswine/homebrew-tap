#!/usr/bin/env python3
"""Tests for formula-supported.py, runnable on Linux without Homebrew."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path(__file__).resolve().parent / "formula-supported.py"
FORMULA = ROOT / "Formula"


def run_check(formula: Path, macos: str, arch: str, source: str = "file", extra: list[str] | None = None):
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--source",
        source,
        "--macos",
        macos,
        "--arch",
        arch,
        str(formula),
    ]
    if extra:
        cmd[1:1] = extra
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


class VersionAndArchTests(unittest.TestCase):
    def test_real_formulas_on_macos_15_arm64(self):
        # This is the current CI runner. infera and coscad must still be tested;
        # fprmeta and qosmeta require Golden Gate (macOS 27).
        cases = {
            "infera.rb": (0, ""),
            "coscad.rb": (0, ""),
            "fprmeta.rb": (
                2,
                "SKIP fprmeta: requires macOS 27 (Golden Gate) or later; runner is 15.0",
            ),
            "qosmeta.rb": (
                2,
                "SKIP qosmeta: requires macOS 27 (Golden Gate) or later; runner is 15.0",
            ),
        }
        for name, (status, stdout) in cases.items():
            with self.subTest(name=name):
                result = run_check(FORMULA / name, "15.0", "arm64")
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout.strip(), stdout)
                self.assertEqual(result.stderr, "")

    def test_sequoia_formulas_skip_on_sonoma(self):
        for name in ("infera.rb", "coscad.rb"):
            with self.subTest(name=name):
                result = run_check(FORMULA / name, "14.6.1", "arm64")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("requires macOS 15 (Sequoia) or later", result.stdout)
                self.assertIn("runner is 14.6.1", result.stdout)

    def test_arm64_formulas_skip_on_x86_64(self):
        result = run_check(FORMULA / "infera.rb", "15.0", "x86_64")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "SKIP infera: requires arch arm64; runner is x86_64",
        )

    def test_aarch64_alias_matches_arm64(self):
        result = run_check(FORMULA / "infera.rb", "15.2", "aarch64")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_golden_gate_accepted_on_27(self):
        for version in ("27", "27.0", "27.2"):
            with self.subTest(version=version):
                result = run_check(FORMULA / "fprmeta.rb", version, "arm64")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_golden_gate_skipped_on_tahoe(self):
        result = run_check(FORMULA / "qosmeta.rb", "26.2", "arm64")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("requires macOS 27 (Golden Gate) or later", result.stdout)
        self.assertIn("runner is 26.2", result.stdout)

    def test_missing_formula_is_an_error(self):
        result = run_check(FORMULA / "no-such.rb", "15.0", "arm64")
        self.assertEqual(result.returncode, 1)
        self.assertIn("formula not found", result.stderr)

    def test_invalid_macos_is_an_error(self):
        result = run_check(FORMULA / "infera.rb", "fifteen", "arm64")
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid version", result.stderr)

    def test_unknown_macos_symbol_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "future.rb"
            path.write_text(
                'class Future < Formula\n  depends_on macos: :next_release\n  depends_on arch: :arm64\nend\n',
                encoding="utf-8",
            )
            result = run_check(path, "15.0", "arm64")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("unknown macOS symbol :next_release", result.stderr)

    def test_quoted_minimum_and_arch_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mixed.rb"
            path.write_text(
                'class Mixed < Formula\n'
                '  depends_on macos: ">= 27.2"\n'
                '  depends_on arch: [:arm64, :x86_64]\n'
                'end\n',
                encoding="utf-8",
            )
            skip = run_check(path, "27.1", "arm64")
            ok = run_check(path, "27.2", "x86_64")
        self.assertEqual(skip.returncode, 2, skip.stderr)
        self.assertEqual(
            skip.stdout.strip(),
            "SKIP mixed: requires macOS 27.2 (Golden Gate) or later; runner is 27.1",
        )
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(ok.stdout, "")

    def test_quoted_symbol_and_comments_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "commented.rb"
            path.write_text(
                'class Commented < Formula\n'
                '  # depends_on macos: :golden_gate\n'
                '  depends_on macos: ">= :sequoia"\n'
                '  # depends_on arch: :x86_64\n'
                'end\n',
                encoding="utf-8",
            )
            ok = run_check(path, "15.0", "x86_64")
            skip = run_check(path, "14.0", "arm64")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(skip.returncode, 2, skip.stderr)
        self.assertIn("macOS 15 (Sequoia)", skip.stdout)

    def test_no_requirements_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "anyhost.rb"
            path.write_text("class Anyhost < Formula\nend\n", encoding="utf-8")
            result = run_check(path, "11.0", "x86_64")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_version_compare_across_10_15_and_11(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.rb"
            path.write_text(
                'class Old < Formula\n  depends_on macos: :catalina\nend\n',
                encoding="utf-8",
            )
            self.assertEqual(run_check(path, "10.15", "x86_64").returncode, 0)
            self.assertEqual(run_check(path, "10.14.6", "x86_64").returncode, 2)
            self.assertEqual(run_check(path, "11.0", "x86_64").returncode, 0)

    def test_usage_without_formula_is_an_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)  # argparse missing required arg
        self.assertIn("formula", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
