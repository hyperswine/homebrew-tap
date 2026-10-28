#!/usr/bin/env python3
"""Update a binary formula only from a verified published upstream release."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {'infera': 'NeoProlog', 'coscad': 'coscad'}


def run(*args):
    return subprocess.check_output(args, text=True)


def formula(name, version, url, digest):
    common = f'''class {name.capitalize()} < Formula
  desc "{'Prolog-inspired logic language with sorts, tabling and CLP(Z)' if name == 'infera' else 'CAD language with native geometry, assemblies and stress analysis'}"
  homepage "https://github.com/hyperswine/{PROJECTS[name]}"
  url "{url}"
  version "{version}"
  sha256 "{digest}"
  license "GPL-3.0-only"

  depends_on arch: :arm64
  depends_on macos: :sequoia

  def install
    bin.install "{name}"
    pkgshare.install "examples"
    doc.install "README.md", "LICENSE", "docs", "release.json"
'''
    if name == 'infera':
        common += '''    pkgshare.install "infera.conf"
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
    output = pipe_output("#{bin}/infera hello.nprolog", ":q\\n")
    assert_match "X = world", output
    assert_match "Y = 42", output
    cp_r opt_pkgshare/"examples", testpath/"examples"
    cp opt_pkgshare/"infera.conf", testpath/"infera.conf"
    system bin/"infera", "check", "examples/facts2.nprolog"
  end
end
'''
    else:
        common += '''    man1.install "man/coscad.1"
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
    (testpath/"box.coscad").write "main = box 2 3 4\\n"
    system bin/"coscad", "box.coscad"
    assert_match "cuboid", (testpath/"box.scad").read
    output = shell_output("#{bin}/coscad stl box.coscad --backend=native -o box.stl")
    assert_match "volume 24.000", output
    assert_match "facet normal", (testpath/"box.stl").read
  end
end
'''
    return common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', choices=PROJECTS)
    parser.add_argument('tag')
    args = parser.parse_args()
    if not re.fullmatch(r'v\d+(?:\.\d+){2,3}', args.tag):
        parser.error('tag must be a version such as v2.1.0 or v1.4.0.0')
    name, version = args.project, args.tag[1:]
    repo = f'hyperswine/{PROJECTS[name]}'
    release = json.loads(run('gh', 'release', 'view', args.tag, '-R', repo,
                             '--json', 'tagName,isDraft,isPrerelease,assets'))
    if release['tagName'] != args.tag or release['isDraft'] or release['isPrerelease']:
        raise SystemExit('Expected a published stable release')
    filename = f'{name}-macos-arm64.tar.gz'
    assets = {asset['name']: asset for asset in release['assets']}
    for asset in (filename, filename+'.sha256'):
        if asset not in assets:
            raise SystemExit(f'Missing release asset: {asset}')
    with tempfile.TemporaryDirectory(prefix='tap-release-') as tmp:
        run('gh', 'release', 'download', args.tag, '-R', repo, '-D', tmp,
            '-p', filename, '-p', filename+'.sha256')
        archive = Path(tmp) / filename
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksum = (Path(tmp) / (filename+'.sha256')).read_text().split()
        if checksum != [digest, filename]:
            raise SystemExit('Published archive checksum does not match')
        with tarfile.open(archive) as tar:
            member = tar.getmember(f'{name}-macos-arm64/release.json')
            meta = json.load(tar.extractfile(member))
        expected = {'name': name, 'version': version, 'system': 'macos',
                    'arch': 'arm64', 'minimum_macos': '15.0'}
        if any(meta.get(key) != value for key, value in expected.items()):
            raise SystemExit(f'Unexpected release metadata: {meta}')
        revision = run('gh', 'api', f'repos/{repo}/commits/{args.tag}', '--jq', '.sha').strip()
        if meta.get('revision') != revision:
            raise SystemExit('Archive source revision does not match the release tag')
        libs = meta.get('runtime_libraries')
        if not libs or any(not lib.startswith(('/usr/lib/', '/System/Library/')) for lib in libs):
            raise SystemExit('Archive has undeclared non-system runtime libraries')
    url = assets[filename]['url']
    target = ROOT / 'Formula' / f'{name}.rb'
    target.write_text(formula(name, version, url, digest))
    print(f'{target}: {version} ({digest})')


if __name__ == '__main__':
    main()
