#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || {
    printf 'usage: %s http://server:8100/dictate\n' "$0" >&2
    exit 2
}

api_url=$1
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
app="$HOME/Applications/Horseflow.app"
config_dir="$HOME/Library/Application Support/Horseflow"
config="$config_dir/config.plist"
agent="$HOME/Library/LaunchAgents/dev.horseflow.client.plist"
label="dev.horseflow.client"
uid=$(id -u)

for command in clang codesign make plutil launchctl; do
    command -v "$command" >/dev/null || {
        printf 'missing required command: %s\n' "$command" >&2
        exit 1
    }
done

make -C "$source_dir" clean build
launchctl bootout "gui/$uid/$label" 2>/dev/null || true
pkill -x Horseflow 2>/dev/null || true

mkdir -p "$HOME/Applications" "$config_dir" "$HOME/Library/LaunchAgents"
rm -rf "$app"
cp -R "$source_dir/build/Horseflow.app" "$app"

plutil -create xml1 "$config"
plutil -insert APIURL -string "$api_url" "$config"

cat >"$agent" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$label</string>
    <key>ProgramArguments</key>
    <array>
        <string>$app/Contents/MacOS/Horseflow</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/Horseflow.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/Horseflow.log</string>
</dict>
</plist>
EOF

plutil -lint "$agent"
launchctl bootstrap "gui/$uid" "$agent"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

printf '%s\n' \
    'Horseflow is running.' \
    'Grant Horseflow Accessibility, Input Monitoring, and Microphone access.'
