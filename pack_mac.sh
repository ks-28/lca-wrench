#!/bin/zsh
# Packs LCA Wrench for another Mac: dist/LCA-Wrench-Mac.zip with the app as committed (default HEAD),
# the two double-click scripts, the instructions and the licence. Nothing uncommitted, no tests, no venv.
set -euo pipefail
cd "$(dirname "$0")"
REF="${1:-HEAD}"
SUFFIX=""
OUT="dist/mac/LCA-Wrench$SUFFIX"
ZIP="dist/LCA-Wrench$SUFFIX-Mac.zip"
rm -rf dist/mac "$ZIP"
mkdir -p "$OUT"
EXTRA=()  # the licence, if the packed version has one (older commits do not)
git cat-file -e "$REF:LICENSE" 2>/dev/null && EXTRA+=(LICENSE)
git archive "$REF" lca_wrench requirements-lock.txt requirements-app.txt mac $EXTRA | tar -x -C "$OUT"
mv "$OUT"/mac/* "$OUT"/ && rmdir "$OUT/mac"
echo "$(git show "${REF}:lca_wrench/__init__.py" | sed -n 's/^__version__ = "\(.*\)"/\1/p') $(git rev-parse --short "$REF") $(git log -1 --format=%cs "$REF")" > "$OUT/VERSION"  # written to lca-wrench.log
# FILES.txt: every file of the package; the installer checks they are all there (a partial copy over an older
# folder lost lca_wrench/data on one PC)
(cd "$OUT" && find . -type f ! -name FILES.txt | sed 's|^\./||' | LC_ALL=C sort > FILES.txt)
ditto -c -k --norsrc --noextattr --keepParent "$OUT" "$ZIP"
rm -rf dist/mac
echo "$ZIP ($(du -h "$ZIP" | cut -f1)) from $(git rev-parse --short "$REF")"
