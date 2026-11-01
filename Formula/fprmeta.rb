# The FP-RISC toolchain manager. Toolchains live in ~/.fpr (FPRMETA_HOME),
# never in the Cellar; see toolchains/fprisc.json for the versions offered.
class Fprmeta < Formula
  desc "FP-RISC toolchain manager: installs versions in ~/.fpr and launches fpr and sol"
  homepage "https://github.com/hyperswine/fprisc"
  url "https://github.com/hyperswine/fprisc/releases/download/fprmeta-v0.1.0/fprmeta-0.1.0-macos-arm64.tar.gz"
  version "0.1.0"
  sha256 "977e7147644d4c945d6065a1a4d4aa9ac694a9d3af5e6c0f65bca0b6b1b2809e"
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
      Toolchains, projects and Sol state stay when this formula is removed.
    EOS
  end

  test do
    ENV["FPRMETA_HOME"] = testpath/"fpr"
    assert_match "fprmeta 0.1.0", shell_output("#{bin}/fprmeta --version")
    assert_match "no fprisc versions installed", shell_output("#{bin}/fprmeta list")
    output = shell_output("#{bin}/fpr --version 2>&1", 2)
    assert_match "fprmeta install", output
  end
end
