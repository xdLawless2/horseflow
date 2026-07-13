import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str
    llm_model: str
    asr_model: str
    language: str
    compute_type: str
    dictionary: tuple[str, ...]
    asr_prompt: str
    request_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        dictionary = tuple(
            word.strip()
            for word in os.getenv("HORSEFLOW_DICTIONARY", "").split(",")
            if word.strip()
        )
        return cls(
            ollama_url=os.environ["OLLAMA_URL"].rstrip("/"),
            llm_model=os.environ["HORSEFLOW_LLM_MODEL"],
            asr_model=os.getenv("HORSEFLOW_ASR_MODEL", "large-v3"),
            language=os.getenv("HORSEFLOW_LANGUAGE", "en"),
            compute_type=os.getenv("HORSEFLOW_COMPUTE_TYPE", "float16"),
            dictionary=dictionary,
            asr_prompt=os.getenv(
                "HORSEFLOW_ASR_PROMPT",
                "Accurate conversational dictation containing technical terms and proper nouns.",
            ),
            request_timeout_seconds=float(
                os.getenv("HORSEFLOW_REQUEST_TIMEOUT_SECONDS", "120")
            ),
        )
