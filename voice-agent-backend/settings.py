from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv


_BASE_DIR = Path(__file__).resolve().parent
# Always load the env file that lives next to this settings module.
load_dotenv(_BASE_DIR / ".env")


def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"{key} must be set")
    return value


def _csv_env(key: str, default: str | None = None) -> list[str]:
    raw = os.getenv(key, default or "")
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    livekit_token_ttl: int
    default_timezone: str
    stt_model: str
    llm_model: str
    tts_model: str
    tts_voice_id: str | None
    openai_model: str
    llm_fallback: str
    cors_origins: List[str]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        livekit_url=_required("LIVEKIT_URL"),
        livekit_api_key=_required("LIVEKIT_API_KEY"),
        livekit_api_secret=_required("LIVEKIT_API_SECRET"),
        livekit_token_ttl=int(os.getenv("LIVEKIT_TOKEN_TTL", "3600")),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "America/Los_Angeles"),
        stt_model=os.getenv("DEEPGRAM_STT_MODEL", "deepgram/nova-3"),
        llm_model=os.getenv("LIVEKIT_LLM_MODEL", "openai/gpt-4o-mini"),
        tts_model=os.getenv("CARTESIA_TTS_MODEL", "cartesia/sonic-3"),
        tts_voice_id=os.getenv("CARTESIA_VOICE_ID"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        llm_fallback=os.getenv("LLM_FALLBACK", "anthropic"),
        cors_origins=_csv_env("BACKEND_CORS_ORIGINS", "*"),
    )
