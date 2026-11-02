# The FP-RISC toolchain manager. Toolchains live in ~/.fpr (FPRMETA_HOME),
# never in the Cellar; see toolchains/fprisc.json for the versions offered.
class Fprmeta < Formula
  desc "FP-RISC toolchain manager: installs versions in ~/.fpr and launches fpr and sol"
  homepage "https://github.com/hyperswine/fprisc"
  url "https://github.com/hyperswine/fprisc/releases/download/fprmeta-v0.2.0/fprmeta-0.2.0-macos-arm64.tar.gz"
  version "0.2.0"
  sha256 "f5f9ee18878496e670a7cca0c35f72c0d49c799eee79f3aebb28c1867e86fc3b"
  license "MIT"

  depends_on arch: :arm64
  # The binary records its own minimum macOS.
  depends_on macos: :golden_gate
  # FP-RISC 0.12.0's compiler loads these from Homebrew. Toolchains that
  # bundle them (self-contained archives) will not need them.
  depends_on "libarchive"
  depends_on "libgit2"

  def install
    libexec.install "bin/fprmeta"
    # One binary that acts on its own name: the manager, and the launchers
    # that run the version a project pins (or the default).
    %w[fprmeta fpr sol].each { |name| bin.install_symlink libexec/"fprmeta" => name }
  end

  def caveats
    <<~EOS
      fprmeta installs FP-RISC toolchains in ~/.fpr (FPRMETA_HOME overrides it).
      Install the newest one, which becomes the default:
        fprmeta install
      `fpr` and `sol` run the version pinned by fpr.toml ([toolchain] fpr),
      or the default. `fprmeta available` lists the published versions.
      Native builds need the Xcode Command Line Tools:
        xcode-select --install
      Published indexes are signature-verified; project pins never auto-install.
      Toolchains, projects and Sol state stay when this formula is removed.
    EOS
  end

  test do
    ENV["FPRMETA_HOME"] = testpath/"fpr"
    assert_match "fprmeta 0.2.0", shell_output("#{bin}/fprmeta --version")
    assert_match "no fprisc versions installed", shell_output("#{bin}/fprmeta list")
    index = testpath/"index.json"
    index.write <<~JSON
      {"format": 1, "component": "fprisc", "entries": []}
    JSON
    (testpath/"index.json.sig").write <<~SIGNATURE
      -----BEGIN SSH SIGNATURE-----
      U1NIU0lHAAAAAQAAADMAAAALc3NoLWVkMjU1MTkAAAAg+ODgacFIMfZBKjhHcgCsVHIqE3
      1IN7rfrDDYGoin/7kAAAANZnBybWV0YS1pbmRleAAAAAAAAAAGc2hhNTEyAAAAUwAAAAtz
      c2gtZWQyNTUxOQAAAEDdZ0jkqzcJL9ZwgInsLOe0m6wxbK7l0XIRjG7d7HVYZ2/+YpZ+Rn
      Cki9uB+ienmPXFxuWxtMZRKg6f1/jM3GIC
      -----END SSH SIGNATURE-----
    SIGNATURE
    assert_match "offers no fprisc release", shell_output("#{bin}/fprmeta available --index #{index}")
    index.append_lines " "
    assert_match "verification failed", shell_output("#{bin}/fprmeta available --index #{index} 2>&1", 1)
    output = shell_output("#{bin}/fpr --version 2>&1", 2)
    assert_match "fprmeta install", output
  end
end
