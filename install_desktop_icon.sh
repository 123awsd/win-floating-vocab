#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/catword"
LAUNCH_SCRIPT="$SCRIPT_DIR/launch_w2r.sh"
DESKTOP_FILE_NAME="W2R_Cattoon.desktop"
APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

if [[ ! -d "$APP_DIR" ]]; then
  echo "找不到应用目录: $APP_DIR" >&2
  exit 1
fi

if [[ ! -f "$LAUNCH_SCRIPT" ]]; then
  echo "找不到启动脚本: $LAUNCH_SCRIPT" >&2
  exit 1
fi

if command -v xdg-user-dir >/dev/null 2>&1; then
  DESKTOP_DIR="$(xdg-user-dir DESKTOP)"
else
  DESKTOP_DIR="$HOME/Desktop"
fi

if [[ -z "$DESKTOP_DIR" ]]; then
  DESKTOP_DIR="$HOME/Desktop"
fi

ICON_FILE="$APP_DIR/assets/cattoon_v1/cat_badge.svg"
if [[ ! -f "$ICON_FILE" ]]; then
  ICON_FILE="$APP_DIR/assets/app_icon/app.ico"
fi

mkdir -p "$APPLICATIONS_DIR" "$DESKTOP_DIR"
chmod +x "$LAUNCH_SCRIPT"

write_desktop_entry() {
  local target="$1"
  cat >"$target" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=W2R Cattoon
Comment=Desktop floating vocabulary window
Exec=$LAUNCH_SCRIPT
TryExec=$LAUNCH_SCRIPT
Path=$APP_DIR
Icon=$ICON_FILE
Terminal=false
Categories=Education;Languages;
StartupNotify=true
EOF
}

APP_MENU_ENTRY="$APPLICATIONS_DIR/$DESKTOP_FILE_NAME"
DESKTOP_ENTRY="$DESKTOP_DIR/$DESKTOP_FILE_NAME"

write_desktop_entry "$APP_MENU_ENTRY"
write_desktop_entry "$DESKTOP_ENTRY"

chmod 644 "$APP_MENU_ENTRY"
chmod 755 "$DESKTOP_ENTRY"

if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate "$APP_MENU_ENTRY"
fi

if command -v gio >/dev/null 2>&1; then
  gio set "$DESKTOP_ENTRY" metadata::trusted true >/dev/null 2>&1 || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

echo "已安装应用菜单项: $APP_MENU_ENTRY"
echo "已安装桌面图标: $DESKTOP_ENTRY"
echo "如果你之后移动了仓库目录，请重新运行本脚本。"
