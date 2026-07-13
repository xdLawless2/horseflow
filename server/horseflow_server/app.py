import asyncio
import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from .audio import normalize_to_wav
from .config import Settings
from .prompts import POLISH_EXAMPLES, POLISH_PROMPT


class HealthResponse(BaseModel):
    status: str
    asr: str
    llm: str


class DictateResponse(BaseModel):
    raw: str
    text: str


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        from faster_whisper import WhisperModel

        active_settings = settings or Settings.from_env()
        app.state.settings = active_settings
        app.state.asr = WhisperModel(
            active_settings.asr_model,
            device="cuda",
            compute_type=active_settings.compute_type,
        )
        yield

    app = FastAPI(
        title="Horseflow",
        description="Self-hosted speech-to-text with local LLM cleanup.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        active_settings: Settings = app.state.settings
        return HealthResponse(
            status="ok",
            asr=active_settings.asr_model,
            llm=active_settings.llm_model,
        )

    @app.post("/dictate", response_model=DictateResponse)
    async def dictate(audio: Annotated[UploadFile, File()]) -> DictateResponse:
        active_settings: Settings = app.state.settings
        data = await audio.read()

        with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
            duration = await asyncio.to_thread(normalize_to_wav, data, wav.name)
            if duration < 0.4:
                return DictateResponse(raw="", text="")
            raw = await asyncio.to_thread(
                transcribe,
                app.state.asr,
                wav.name,
                active_settings,
            )

        if not raw:
            return DictateResponse(raw="", text="")

        async with httpx.AsyncClient(
            timeout=active_settings.request_timeout_seconds
        ) as client:
            cleaned = await polish(client, active_settings, raw)

        return DictateResponse(raw=raw, text=cleaned)

    return app


def transcribe(asr: Any, path: str, settings: Settings) -> str:
    vocabulary = ", ".join(settings.dictionary)
    prompt = settings.asr_prompt
    if vocabulary:
        prompt = f"{prompt} Relevant vocabulary: {vocabulary}."

    segments, _ = asr.transcribe(
        path,
        language=settings.language,
        beam_size=5,
        vad_filter=True,
        initial_prompt=prompt,
        hotwords=",".join(settings.dictionary) or None,
        condition_on_previous_text=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


async def polish(
    client: httpx.AsyncClient,
    settings: Settings,
    transcript: str,
) -> str:
    response = await client.post(
        f"{settings.ollama_url}/api/chat",
        json={
            "model": settings.llm_model,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": len(transcript.split()) * 3 + 24,
            },
            "messages": [
                {"role": "system", "content": POLISH_PROMPT},
                *POLISH_EXAMPLES,
                {
                    "role": "user",
                    "content": f"<transcript>{transcript}</transcript>",
                },
            ],
        },
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "horseflow_server.app:app",
        host=os.getenv("HORSEFLOW_HOST", "127.0.0.1"),
        port=int(os.getenv("HORSEFLOW_PORT", "8100")),
    )
