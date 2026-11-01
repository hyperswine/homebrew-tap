# Hyperswine Homebrew tap

Install tested release binaries on Apple Silicon with macOS 15 or newer:

```sh
brew install hyperswine/tap/infera hyperswine/tap/coscad
infera --version
coscad --version
```

These formulae download the versioned macOS ARM64 archives from each project's
GitHub release. Homebrew verifies the archive checksum and installs the binary,
examples and documentation. They do not build from source, install GHC/Cabal,
or require a development checkout. Intel Macs and Linux are not supported by
these initial formulae; upstream Linux archives remain separate downloads.

Use `brew upgrade hyperswine/tap/infera hyperswine/tap/coscad` for updates.

## FP-RISC and QOS: fprmeta and qosmeta

FP-RISC toolchains and QOS Portable SDKs are installed by two small managers,
not by versioned formulas. Homebrew installs only the managers:

```sh
brew install hyperswine/tap/fprmeta     # fprmeta, fpr, sol
brew install hyperswine/tap/qosmeta     # qosmeta, qos
fprmeta install                         # newest FP-RISC toolchain into ~/.fpr
qosmeta install                         # newest QOS SDK into ~/.qos
```

`fpr`, `sol` and `qos` are launchers: each runs the version a project pins
(`fpr.toml` `[toolchain] fpr`, `qos.toml` `[sdk] version`; `"0.12.0"` means
0.12.0 or a later 0.12.x, `"=0.12.3"` exactly that one) or the default. Several
versions can be installed side by side; `brew upgrade` only updates the
managers. The versions on offer are listed in `toolchains/fprisc.json` and
`toolchains/qos-portable.json`, which the managers read from this repository;
`fprmeta available` and `qosmeta available` show them.

The old `fprisc` and `qos-portable` formulas are renamed to `fprmeta` and
`qosmeta` (`formula_renames.json`). After the move, run `fprmeta install
0.12.0` and `qosmeta install`.

To offer a new version, add an entry with the release archive's URL and
SHA-256 to the matching list and push it. Never change the hash of an
existing version; publish a new one instead.

## Installed files

- Infera examples and their module map: `$(brew --prefix)/share/infera`.
  Copy that directory into a writable project before experimenting with module
  registration or REPL history. Existing project configurations stay unchanged.
- CoScad examples: `$(brew --prefix)/share/coscad/examples`; manual: `man coscad`.
  The native geometry kernel is included. OpenSCAD/BOSL2 remain optional for the
  OpenSCAD backend and planner/site images. The full `coscad doctor` checks that
  optional toolchain as well. Homebrew's current OpenSCAD distribution is
  `brew install --cask openscad@snapshot`.
- Build metadata and license notices are installed with each package's docs.

No service is started and no user project data is stored in the Homebrew Cellar.

## Updating a release

After the upstream release build and tests pass:

```sh
python3 scripts/update-release.py infera v2.1.0
python3 scripts/update-release.py coscad v1.4.0.0
```

The updater uses the authenticated `gh` CLI to download the published archive
and checksum. It independently hashes the archive, validates its version,
platform, source revision and runtime-library metadata, and writes the formula.
It never executes the downloaded binary. Commit the result and open a PR;
CI installs and tests the exact binary packages on macOS ARM64.

The upstream release must provide `release.json` in the archive and a sibling
`.tar.gz.sha256` asset. Existing release assets must not be replaced with different
code under the same version. Publish a new version for changes.

The original tools and their bundled dependencies retain their own licenses;
see the license files distributed with each release.
