# Release verification

`update-release.py PROJECT TAG` only updates a formula after it has downloaded
and checked the complete published macOS ARM64 archive. Checks include:

- SHA-256 against the separate published checksum asset;
- package name, version, OS, architecture and minimum macOS version;
- source revision against the commit referenced by the release tag;
- macOS dynamic dependencies restricted to system libraries.

If a new release needs a non-system dynamic library, add an explicit Homebrew
runtime dependency and update the verifier as part of that reviewed change.
Do not bypass the dependency check or install an unverified candidate.

For each release, the final installation is tested with `brew test` and
`brew linkage --test`, followed by running the program outside its checkout.

# CI formula support check

`formula-supported.py FORMULA.rb` exits 0 if the current runner (or
`--macos` / `--arch`) satisfies the formula's `depends_on macos:` and
`depends_on arch:` requirements, and exits 2 with a `SKIP ...` notice
when it does not. The binary-installs workflow uses this to skip
formulas the runner cannot install, such as fprmeta and qosmeta on a
macos-15 image, while still testing infera and coscad.

The script prefers `brew info --json=v2` when Homebrew can load the
formula, and otherwise parses the formula file. `--source file` forces
the parser, which is what the tests use. Run them with:

```sh
python3 -m unittest -v scripts/test-formula-supported.py
```
