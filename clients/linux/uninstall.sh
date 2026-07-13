#!/usr/bin/env bash
set -euo pipefail

systemctl --user disable --now horseflow.service 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/horseflow.service"
rm -rf "$HOME/.local/share/horseflow/linux"
systemctl --user daemon-reload

printf 'kept configuration at %s\n' "$HOME/.config/horseflow/client.env"
