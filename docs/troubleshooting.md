# Troubleshooting

## Server

Check service state:

```bash
docker compose -f deploy/compose.yaml ps
docker compose -f deploy/compose.yaml logs -f api ollama
nvidia-smi
```

If startup fails, confirm the configured GPU UUID exists, both model storage
directories exist, and the NVIDIA Container Toolkit works with Docker.

If `/dictate` returns an Ollama error, confirm the exact configured model is
installed:

```bash
docker compose -f deploy/compose.yaml exec ollama ollama list
```

## Linux

Inspect the daemon:

```bash
systemctl --user status horseflow.service
journalctl --user -u horseflow.service -f
```

If no keyboard is found, verify the user can read `/dev/input/event*`. If the
virtual keyboard cannot be created, verify the user can write `/dev/uinput` and
the `uinput` module is loaded.

If audio is empty, confirm `HORSEFLOW_MIC` exactly matches a PipeWire source.

## macOS

Inspect:

```bash
launchctl print gui/$(id -u)/dev.horseflow.client
tail -f ~/Library/Logs/Horseflow.log
```

If Command+Space opens Spotlight, enable Horseflow in Accessibility and Input
Monitoring, then restart the agent:

```bash
launchctl kickstart -k gui/$(id -u)/dev.horseflow.client
```

If recording fails, enable Microphone access for Horseflow and restart it.
