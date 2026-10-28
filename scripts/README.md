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
