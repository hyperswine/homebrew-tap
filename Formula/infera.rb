class Infera < Formula
  desc "Prolog-inspired logic language with sorts, tabling and CLP(Z)"
  homepage "https://github.com/hyperswine/NeoProlog"
  url "https://github.com/hyperswine/NeoProlog/releases/download/v2.5.0/infera-macos-arm64.tar.gz"
  version "2.5.0"
  sha256 "04caeb7fc34b2a28a081f49d401cfdc77eb217710583439127ef90dd026997f2"
  license "GPL-3.0-only"

  depends_on arch: :arm64
  depends_on macos: :sequoia

  def install
    bin.install "infera"
    pkgshare.install "examples"
    doc.install "README.md", "LICENSE", "docs", "release.json"
    pkgshare.install "infera.conf"
  end

  def caveats
    <<~EOS
      Copy #{opt_pkgshare} into a writable project to use the examples and
      their module map together. No source checkout, GHC or Cabal is needed.
    EOS
  end

  test do
    assert_match "infera #{version}", shell_output("#{bin}/infera --version")
    (testpath/"hello.nprolog").write <<~PROLOG
      greet world.
      double : det (int: <=) (int: =>).
      double X Y <- Y is X * 2.
      > greet X?
      > double 21 Y?
    PROLOG
    assert_equal [], JSON.parse(shell_output("#{bin}/infera check --json hello.nprolog"))
    output = pipe_output("#{bin}/infera hello.nprolog", ":q\n")
    assert_match "X = world", output
    assert_match "Y = 42", output
    cp_r opt_pkgshare/"examples", testpath/"examples"
    cp opt_pkgshare/"infera.conf", testpath/"infera.conf"
    system bin/"infera", "check", "examples/facts2.nprolog"
  end
end
