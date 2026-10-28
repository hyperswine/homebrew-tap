class Coscad < Formula
  desc "CAD language with native geometry, assemblies and stress analysis"
  homepage "https://github.com/hyperswine/coscad"
  url "https://github.com/hyperswine/coscad/releases/download/v1.4.0.0/coscad-macos-arm64.tar.gz"
  version "1.4.0.0"
  sha256 "dc21f44798ed72b62603750e281ace0f911c5429990db78b312ad9f569327b7d"
  license "GPL-3.0-only"

  depends_on arch: :arm64
  depends_on macos: :sequoia

  def install
    bin.install "coscad"
    pkgshare.install "examples"
    doc.install "README.md", "LICENSE", "docs", "release.json"
    man1.install "man/coscad.1"
    doc.install "CHANGELOG.md", "third-party", "native-kernel.lock.json"
  end

  def caveats
    <<~EOS
      The pinned native geometry kernel is included. OpenSCAD and BOSL2 are
      optional for the OpenSCAD backend and planner/site images.
      The full `coscad doctor` checks those optional tools as well.
      Examples: #{opt_pkgshare}/examples    Manual: man coscad
    EOS
  end

  test do
    assert_match "coscad #{version}", shell_output("#{bin}/coscad --version")
    capabilities = JSON.parse(shell_output("#{bin}/coscad capabilities --json"))
    assert_equal "native-experimental", capabilities.fetch("default_backend")
    (testpath/"box.coscad").write "main = box 2 3 4\n"
    system bin/"coscad", "box.coscad"
    assert_match "cuboid", (testpath/"box.scad").read
    output = shell_output("#{bin}/coscad stl box.coscad --backend=native -o box.stl")
    assert_match "volume 24.000", output
    assert_match "facet normal", (testpath/"box.stl").read
  end
end
