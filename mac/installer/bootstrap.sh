#!/bin/bash
# Run by "Install LCA Wrench.app" (signed and notarized, so macOS opens it without the "Open Anyway" detour).
# Copies the LCA Wrench folder out of the app to a permanent place and starts the installation there
# ("Install LCA Wrench.command", in a Terminal window that shows the progress).
#
# The app may run from a read-only, randomized path (macOS "app translocation" for downloaded apps), so everything
# it needs is inside the app, and nothing is written next to it.
#
# For tests: LCA_WRENCH_INSTALL_DIR=<folder> skips the dialogs, LCA_WRENCH_INSTALL_NO_RUN=1 only copies.
set -u
RES="$(cd "$(dirname "$0")" && pwd)"
PAYLOAD="$RES/payload"
NAME="LCA Wrench"
FOLDER="LCA-Wrench"

alert() { /usr/bin/osascript - "$1" <<'AS' >/dev/null 2>&1
on run argv
  tell me to activate
  display alert "LCA Wrench" message (item 1 of argv) as critical
end run
AS
}

[ -f "$PAYLOAD/Install LCA Wrench.command" ] || { alert "This installer is incomplete. Download it again."; exit 1; }

TARGET="${LCA_WRENCH_INSTALL_DIR:-}"
if [ -z "$TARGET" ]; then
  TARGET="$HOME/$FOLDER"
  while :; do
    CHOICE="$(/usr/bin/osascript - "$TARGET" <<'AS' 2>/dev/null
on run argv
  tell me to activate
  set msg to "LCA Wrench will be installed in this folder:" & return & return & (item 1 of argv) & return & return & ¬
    "It sets up its own Python and the packages inside that folder (internet needed, 3 to 5 minutes, no administrator password). A Terminal window shows the progress."
  set r to display dialog msg with title "Install LCA Wrench" buttons {"Cancel", "Other folder…", "Install"} default button "Install" cancel button "Cancel"
  return button returned of r
end run
AS
)" || exit 0
    case "$CHOICE" in
      Install) break ;;
      "Other folder…")
        PARENT="$(/usr/bin/osascript <<'AS' 2>/dev/null
tell me to activate
POSIX path of (choose folder with prompt "LCA Wrench gets its own folder \"LCA-Wrench\" inside the folder you choose:")
AS
)" || continue
        TARGET="${PARENT%/}/$FOLDER" ;;
      *) exit 0 ;;
    esac
  done
fi

# an existing folder is only used when it is an LCA Wrench folder (then this is an update: the app files are
# replaced, its Python, the packages and the log stay)
if [ -e "$TARGET" ] && [ ! -f "$TARGET/VERSION" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  alert "The folder $TARGET exists and is not an LCA Wrench folder. Choose another place."
  exit 1
fi
mkdir -p "$TARGET" 2>/dev/null || { alert "No write access to $TARGET. Choose another place."; exit 1; }
# --noqtn: the copies do not carry the "downloaded from the internet" mark of this app
/usr/bin/ditto --noqtn --norsrc "$PAYLOAD" "$TARGET" || { alert "Copying to $TARGET failed."; exit 1; }
/usr/bin/xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null

[ -n "${LCA_WRENCH_INSTALL_NO_RUN:-}" ] && exit 0
/usr/bin/open "$TARGET/Install LCA Wrench.command"
