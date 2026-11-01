# The QOS Portable SDK manager: the same binary as fprmeta, acting as qosmeta.
# SDKs live in ~/.qos (QOSMETA_HOME), never in the Cellar; see
# toolchains/qos-portable.json for the versions offered.
class Qosmeta < Formula
  desc "QOS Portable SDK manager: installs SDKs in ~/.qos and launches qos"
  homepage "https://github.com/hyperswine/qos"
  url "https://github.com/hyperswine/fprisc/releases/download/fprmeta-v0.1.0/fprmeta-0.1.0-macos-arm64.tar.gz"
  version "0.1.0"
  sha256 "977e7147644d4c945d6065a1a4d4aa9ac694a9d3af5e6c0f65bca0b6b1b2809e"
  license "MIT"

  depends_on arch: :arm64
  depends_on macos: :golden_gate
  # SDK 0.3.0's private compiler loads libgit2 and libarchive, and its GL
  # host loads glfw, from Homebrew.
  depends_on "glfw"
  depends_on "libarchive"
  depends_on "libgit2"

  def install
    libexec.install "bin/fprmeta"
    %w[qosmeta qos].each { |name| bin.install_symlink libexec/"fprmeta" => name }
  end

  def caveats
    <<~EOS
      qosmeta installs QOS Portable SDKs in ~/.qos (QOSMETA_HOME overrides it).
      Install the newest one, which becomes the default:
        qosmeta install
      `qos` runs the SDK pinned by qos.toml ([sdk] version), or the default.
      Each SDK carries its own compiler and ld.lld; building needs Clang from
      the Xcode Command Line Tools:
        xcode-select --install
      SDKs, projects and QOS disks stay when this formula is removed.
    EOS
  end

  test do
    ENV["QOSMETA_HOME"] = testpath/"qos"
    assert_match "qosmeta 0.1.0", shell_output("#{bin}/qosmeta --version")
    assert_match "no qos-portable versions installed", shell_output("#{bin}/qosmeta list")
    output = shell_output("#{bin}/qos --version 2>&1", 2)
    assert_match "qosmeta install", output
  end
end
