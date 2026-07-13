import asyncio
import io
from pathlib import Path

import httpx
import numpy as np
import pytest
import soundfile as sf
from horseflow_server.app import polish, transcribe
from horseflow_server.audio import normalize_to_wav
from horseflow_server.config import Settings


def settings(**overrides: object) -> Settings:
    values = {
        "ollama_url": "http://ollama:11434",
        "llm_model": "qwen3:8b",
        "asr_model": "large-v3",
        "language": "en",
        "compute_type": "float16",
        "dictionary": ("Horseflow", "Whisper"),
        "asr_prompt": "Accurate dictation.",
        "request_timeout_seconds": 120.0,
    }
    values.update(overrides)
    return Settings(**values)


def test_settings_fail_fast_without_required_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.delenv("HORSEFLOW_LLM_MODEL", raising=False)
    with pytest.raises(KeyError):
        Settings.from_env()


def test_settings_parse_dictionary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434/")
    monkeypatch.setenv("HORSEFLOW_LLM_MODEL", "qwen3:8b")
    monkeypatch.setenv("HORSEFLOW_DICTIONARY", "Horseflow, Whisper,")
    active = Settings.from_env()
    assert active.ollama_url == "http://localhost:11434"
    assert active.dictionary == ("Horseflow", "Whisper")


def test_normalize_to_wav(tmp_path: Path) -> None:
    source = io.BytesIO()
    sf.write(source, np.full(8_000, 0.1), 8_000, format="WAV")
    output = tmp_path / "normalized.wav"

    duration = normalize_to_wav(source.getvalue(), str(output))
    audio, rate = sf.read(output)

    assert duration == pytest.approx(1.0)
    assert rate == 16_000
    assert np.abs(audio).max() == pytest.approx(0.95, abs=0.001)


def test_transcribe_passes_prompt_and_hotwords() -> None:
    class Segment:
        def __init__(self, text: str) -> None:
            self.text = text

    class ASR:
        arguments: dict[str, object]

        def transcribe(self, path: str, **arguments: object):
            self.arguments = arguments
            return [Segment(" hello "), Segment("world")], None

    asr = ASR()
    result = transcribe(asr, "/tmp/audio.wav", settings())

    assert result == "hello world"
    assert asr.arguments["hotwords"] == "Horseflow,Whisper"
    assert "Horseflow, Whisper" in str(asr.arguments["initial_prompt"])


def test_polish_returns_ollama_message() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        assert "<transcript>hello world</transcript>" in body
        return httpx.Response(
            200,
            json={"message": {"content": "Hello world."}},
        )

    async def run() -> str:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await polish(client, settings(), "hello world")

    assert asyncio.run(run()) == "Hello world."
