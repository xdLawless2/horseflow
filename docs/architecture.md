# Architecture

## Request flow

1. A client detects the platform hotkey at the global input layer.
2. Recording begins on the modifier key-down event to preserve the first
   syllable.
3. Pressing Space confirms dictation. Any other shortcut aborts and deletes the
   speculative recording.
4. Releasing Space or the modifier records a short tail and finalizes the WAV.
5. The client sends a multipart request to `POST /dictate`.
6. The server decodes, resamples, and peak-normalizes the audio.
7. Whisper transcribes with a configured prompt and hotword dictionary.
8. Ollama minimally cleans punctuation, fillers, false starts, and lists.
9. The client copies the cleaned text and injects the platform paste shortcut.

## Input suppression

The Linux client exclusively grabs physical keyboards with evdev and forwards
events through a uinput clone. Ctrl+Space events are omitted from the clone.

The macOS client installs a Core Graphics event tap. Command+Space callbacks
return `NULL`, preventing Spotlight and the focused application from receiving
the Space event.

Both clients begin recording speculatively on modifier-down. A regular shortcut
such as Ctrl+C or Command+C aborts the recording and forwards the shortcut
normally.

## Server process

The FastAPI lifespan loads one `faster-whisper` model into GPU memory. Audio
decoding and transcription run outside the event loop. The cleanup request is
sent to Ollama through its `/api/chat` endpoint with deterministic generation
settings.

The server is stateless. Model caches are the only persistent volumes in the
reference deployment.
