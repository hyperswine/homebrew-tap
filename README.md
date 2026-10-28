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
