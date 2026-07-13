#!/usr/bin/env bash
set -euo pipefail

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install_dir="$HOME/.local/share/horseflow/linux"
config_dir="$HOME/.config/horseflow"
service_dir="$HOME/.config/systemd/user"

for command in python3 pw-record wl-copy ydotool notify-send systemctl; do
    command -v "$command" >/dev/null || {
        printf 'missing required command: %s\n' "$command" >&2
        exit 1
    }
done

[[ -f "$config_dir/client.env" ]] || {
    printf 'create %s from client.env.example before installing\n' \
        "$config_dir/client.env" >&2
    exit 1
}

mkdir -p "$install_dir" "$service_dir"
install -m 755 "$source_dir/horseflow_ptt.py" "$install_dir/horseflow_ptt.py"
install -m 644 "$source_dir/requirements.txt" "$install_dir/requirements.txt"
install -m 644 "$source_dir/horseflow.service" "$service_dir/horseflow.service"

python3 -m venv "$install_dir/.venv"
"$install_dir/.venv/bin/pip" install --disable-pip-version-check \
    -r "$install_dir/requirements.txt"

systemctl --user daemon-reload
systemctl --user enable --now horseflow.service
