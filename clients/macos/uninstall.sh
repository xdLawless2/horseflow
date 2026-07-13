#!/usr/bin/env bash
set -euo pipefail

label="dev.horseflow.client"
uid=$(id -u)

launchctl bootout "gui/$uid/$label" 2>/dev/null || true
pkill -x Horseflow 2>/dev/null || true
rm -rf \
    "$HOME/Applications/Horseflow.app" \
    "$HOME/Library/LaunchAgents/dev.horseflow.client.plist" \
    "$HOME/Library/Application Support/Horseflow" \
    "$HOME/Library/Logs/Horseflow.log" \
    /tmp/horseflow
tccutil reset All "$label" >/dev/null 2>&1 || true
