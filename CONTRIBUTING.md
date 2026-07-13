# Contributing

## Development setup

Install Python 3.10 or newer and uv:

```bash
uv sync
uv run pytest
uv run ruff check .
```

Docker changes should pass:

```bash
docker compose -f deploy/compose.yaml config
docker build -f server/Dockerfile .
```

macOS client changes should compile on macOS 15 or newer:

```bash
make -C clients/macos clean build
```

## Design rules

- Keep speech recognition and cleanup local.
- Keep server and device configuration explicit.
- Fail immediately when required configuration is missing.
- Do not add service discovery, silent fallback models, or compatibility
  branches.
- Never commit personal vocabulary, private addresses, credentials, audio, or
  transcripts.
- Preserve the invariant that the push-to-talk Space event never reaches the
  focused application.

## Pull requests

Keep changes focused, add tests for behavior changes, and document configuration
changes in the README.
