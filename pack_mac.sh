#!/bin/zsh
# Packs LCA Wrench for another Mac: dist/LCA-Wrench-Mac.zip with the app as committed (default HEAD),
# the two double-click scripts, the instructions and the licence. Nothing uncommitted, no tests, no venv.
#
# Two forms:
# - Without a signing identity: the folder "LCA-Wrench" with the double-click scripts. macOS blocks them the first
#   time (System Settings, Privacy & Security, "Open Anyway").
# - With LCA_WRENCH_SIGN_IDENTITY (a "Developer ID Application: ..." certificate in the keychain): the same folder
#   inside "Install LCA Wrench.app", signed with the hardened runtime. With LCA_WRENCH_NOTARY_PROFILE (a profile
#   stored with `xcrun notarytool store-credentials`) the app is also notarized by Apple and the ticket stapled,
#   so it opens on another Mac without that detour. The app copies the folder to a place the user chooses and runs
#   the installation there (mac/installer/).
#     LCA_WRENCH_SIGN_IDENTITY="Developer ID Application: Name (TEAMID)" LCA_WRENCH_NOTARY_PROFILE=profile ./pack_mac.sh
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
rm -rf "$OUT/mac/installer"   # the sources of the installer app, not part of the folder
mv "$OUT"/mac/* "$OUT"/ && rmdir "$OUT/mac"
VERSION_NO="$(git show "${REF}:lca_wrench/__init__.py" | sed -n 's/^__version__ = "\(.*\)"/\1/p')"
echo "$VERSION_NO $(git rev-parse --short "$REF") $(git log -1 --format=%cs "$REF")" > "$OUT/VERSION"  # written to lca-wrench.log
# FILES.txt: every file of the package; the installer checks they are all there (a partial copy over an older
# folder lost lca_wrench/data on one PC)
(cd "$OUT" && find . -type f ! -name FILES.txt | sed 's|^\./||' | LC_ALL=C sort > FILES.txt)
IDENTITY="${LCA_WRENCH_SIGN_IDENTITY:-}"
if [ -z "$IDENTITY" ]; then
  ditto -c -k --norsrc --noextattr --keepParent "$OUT" "$ZIP"
else
  # "Install LCA Wrench.app": Mach-O launcher, bootstrap.sh and the folder as payload
  APP="dist/mac/Install LCA Wrench.app"
  mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
  git show "$REF:mac/installer/launcher.c" > dist/mac/launcher.c
  clang -Os -Wall -arch arm64 -arch x86_64 -mmacosx-version-min=11.0 -o "$APP/Contents/MacOS/install-lca-wrench" dist/mac/launcher.c
  rm dist/mac/launcher.c
  git show "$REF:mac/installer/bootstrap.sh" > "$APP/Contents/Resources/bootstrap.sh"
  cp "$OUT/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
  mv "$OUT" "$APP/Contents/Resources/payload"
  cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Install LCA Wrench</string>
  <key>CFBundleDisplayName</key><string>Install LCA Wrench</string>
  <key>CFBundleIdentifier</key><string>ch.lca-wrench.installer</string>
  <key>CFBundleExecutable</key><string>install-lca-wrench</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>${VERSION_NO:-0}</string>
  <key>CFBundleVersion</key><string>${VERSION_NO:-0}</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PLIST
  codesign --force --timestamp --options runtime --sign "$IDENTITY" "$APP"
  codesign --verify --strict --verbose=2 "$APP"
  PROFILE="${LCA_WRENCH_NOTARY_PROFILE:-}"
  if [ -n "$PROFILE" ]; then
    ditto -c -k --keepParent "$APP" dist/mac/notarize.zip
    xcrun notarytool submit dist/mac/notarize.zip --keychain-profile "$PROFILE" --wait | tee dist/mac/notary.txt
    if ! grep -q "status: Accepted" dist/mac/notary.txt; then
      echo "Notarization not accepted. Reason: xcrun notarytool log <id> --keychain-profile \"$PROFILE\"" >&2
      exit 1
    fi
    xcrun stapler staple "$APP"
    xcrun stapler validate "$APP"
  else
    echo "Signed but not notarized (LCA_WRENCH_NOTARY_PROFILE not set): other Macs still ask for \"Open Anyway\"."
  fi
  ditto -c -k --keepParent "$APP" "$ZIP"
fi
rm -rf dist/mac
echo "$ZIP ($(du -h "$ZIP" | cut -f1)) from $(git rev-parse --short "$REF")"
