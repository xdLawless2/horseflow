# Horseflow

Horseflow is self-hosted push-to-talk dictation. It records while a global
hotkey is held, transcribes locally with Whisper, cleans punctuation and false
starts with a local LLM, then pastes the result into the focused application.

- Local speech recognition with `faster-whisper`
- Local cleanup through Ollama
- Linux client: hold **Ctrl+Space**
- macOS client: hold **Command+Space**
- The hotkey's Space event is swallowed before the focused application sees it
- No cloud API or account required

## Architecture

```text
keyboard hotkey -> local recording -> Horseflow API
                                      |-> Whisper large-v3
                                      `-> Ollama cleanup model
                                           -> clipboard -> synthetic paste
```

The server and clients may run on the same machine or communicate over a
private network such as Tailscale.

## Server

### Requirements

- Linux host with Docker Compose
- NVIDIA GPU and NVIDIA Container Toolkit
- Approximately 11 GB VRAM for Whisper large-v3 and an 8B/9B quantized LLM

### Configure

```bash
cd deploy
cp .env.example .env
nvidia-smi --query-gpu=uuid,name --format=csv
```

Edit `.env`. Set:

- `HORSEFLOW_GPU` to the selected GPU UUID
- `HORSEFLOW_BIND_ADDRESS` to `127.0.0.1`
- model storage paths
- custom vocabulary and ASR context

### Start

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3:8b
docker compose up -d --build api
curl http://127.0.0.1:8100/health
```

The API documentation is available at `/docs`.

## Run the server and clients on different machines

Use Tailscale Serve to expose the localhost-bound API as a stable, tailnet-only
HTTPS endpoint. Linux and macOS clients can use the same endpoint:

```text
https://horseflow-server.example-tailnet.ts.net/dictate
```

Follow the complete [cross-machine Tailscale setup](docs/tailscale.md). Do not
bind Horseflow publicly or use Tailscale Funnel.

## Linux client

The Linux client exclusively grabs physical keyboards through evdev, forwards
normal input through a virtual keyboard, and swallows Ctrl+Space. It records
through PipeWire and pastes through ydotool.

### Requirements

- Python 3.10+
- `pw-record`
- `wl-copy`
- `ydotool`
- `notify-send`
- Permission to read `/dev/input/event*` and write `/dev/uinput`

On many distributions, the user must belong to the `input` and `uinput`
groups. Log out after changing group membership.

### Install

```bash
mkdir -p ~/.config/horseflow
cp clients/linux/client.env.example ~/.config/horseflow/client.env
```

Set `HORSEFLOW_API_URL` and `HORSEFLOW_MIC`. Find the PipeWire microphone name
with `wpctl status`, then run:

```bash
clients/linux/install.sh
journalctl --user -u horseflow.service -f
```

Hold Ctrl+Space, speak, and release either key.

## macOS client

The macOS client is a native menu-bar-less application built with system
frameworks. A Core Graphics event tap swallows Command+Space, AVFoundation
records the current default microphone, and the resulting text is pasted with
a synthetic Command+V.

### Requirements

- macOS 15 or newer
- Xcode Command Line Tools

### Install

```bash
clients/macos/install.sh \
  https://horseflow-server.example-tailnet.ts.net/dictate
```

macOS will require Horseflow access under:

- Privacy & Security → Accessibility
- Privacy & Security → Input Monitoring
- Privacy & Security → Microphone

Command+Space remains suppressed only while Horseflow is running. Hold the
shortcut, speak, and release either key.

## Configuration

Server settings are environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `OLLAMA_URL` | yes | Ollama base URL |
| `HORSEFLOW_LLM_MODEL` | yes | Cleanup model |
| `HORSEFLOW_ASR_MODEL` | no | Whisper model; default `large-v3` |
| `HORSEFLOW_LANGUAGE` | no | Transcription language; default `en` |
| `HORSEFLOW_COMPUTE_TYPE` | no | Whisper compute type; default `float16` |
| `HORSEFLOW_DICTIONARY` | no | Comma-separated vocabulary |
| `HORSEFLOW_ASR_PROMPT` | no | Natural-language ASR context |

Client installers use one explicit endpoint and do not perform service
discovery.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

Build the macOS client on a Mac:

```bash
make -C clients/macos clean build
```

## Security

Horseflow has no application authentication. Bind it only to localhost or a
trusted private network. See [SECURITY.md](SECURITY.md).

## License

Horseflow source code is available under the [MIT License](LICENSE). Whisper,
Ollama, and downloaded model weights have their own licenses.
