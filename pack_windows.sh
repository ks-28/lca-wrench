#!/bin/zsh
# Packs LCA Wrench for a Windows PC: dist/LCA-Wrench-Windows.zip with the app as committed (default HEAD),
# the two double-click scripts, the installer, the instructions and the licence. Nothing uncommitted, no tests, no venv.
# Windows needs CRLF in .cmd/.ps1/.txt and a UTF-8 BOM in install.ps1 (else PowerShell 5.1 reads non-ASCII as ANSI).
set -euo pipefail
cd "$(dirname "$0")"
REF="${1:-HEAD}"
SUFFIX=""
OUT="dist/windows/LCA-Wrench$SUFFIX"
ZIP="dist/LCA-Wrench$SUFFIX-Windows.zip"
rm -rf dist/windows "$ZIP"
mkdir -p "$OUT"
EXTRA=()  # the licence, if the packed version has one (older commits do not)
git cat-file -e "$REF:LICENSE" 2>/dev/null && EXTRA+=(LICENSE)
git archive "$REF" lca_wrench requirements-lock.txt requirements-app.txt windows $EXTRA | tar -x -C "$OUT"
mv "$OUT"/windows/* "$OUT"/ && rmdir "$OUT/windows"
echo "$(git show "${REF}:lca_wrench/__init__.py" | sed -n 's/^__version__ = "\(.*\)"/\1/p') $(git rev-parse --short "$REF") $(git log -1 --format=%cs "$REF")" > "$OUT/VERSION"  # written to lca-wrench.log
# FILES.txt: every file of the package; the installer checks they are all there (a partial copy over an older
# folder lost lca_wrench/data on one PC)
(cd "$OUT" && find . -type f ! -name FILES.txt | sed 's|^\./||' | LC_ALL=C sort > FILES.txt)
for f in "$OUT"/*.cmd "$OUT"/*.ps1 "$OUT"/*.txt "$OUT"/*.env(N); do
  perl -pi -e 's/\r?\n/\r\n/' "$f"
done
printf '\xef\xbb\xbf' | cat - "$OUT/install.ps1" > "$OUT/install.ps1.bom" && mv "$OUT/install.ps1.bom" "$OUT/install.ps1"
(cd dist/windows && zip -qrX "../${ZIP:t}" "${OUT:t}")
rm -rf dist/windows
echo "$ZIP ($(du -h "$ZIP" | cut -f1)) from $(git rev-parse --short "$REF")"
