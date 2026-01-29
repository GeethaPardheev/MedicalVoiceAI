from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from livekit import api as lk_api
from pydantic import BaseModel, Field

from services import SlotGenerator, SupabaseClient
from settings import get_settings
from tools import fetch_slots


logger = logging.getLogger("voice-agent.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="AI Voice Agent Backend",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)

origins = settings.cors_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_supabase = SupabaseClient()
_slot_generator = SlotGenerator(settings.default_timezone)


class SessionRequest(BaseModel):
    display_name: str = Field(..., max_length=64)
    phone_number: str = Field(..., description="Raw or formatted caller phone number")
    room_name: str | None = Field(default=None, description="Optional room override")


class SessionResponse(BaseModel):
    room_name: str
    identity: str
    token: str
    expires_at: float
    livekit_url: str


def _build_access_token(identity: str, name: str, room: str) -> str:
    logger.debug("building access token", extra={"identity": identity, "room": room})
    grant = lk_api.VideoGrants(room_join=True, room=room)
    token = (
        lk_api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_ttl(timedelta(seconds=settings.livekit_token_ttl))
        .with_grants(grant)
    )
    return token.to_jwt()


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    logger.debug("/api/health invoked")
    supabase_ok = await _supabase.health()
    status = "ok" if supabase_ok else "degraded"
    return {"status": status, "supabase": supabase_ok}


@app.post("/api/session", response_model=SessionResponse)
async def create_session(payload: SessionRequest) -> SessionResponse:
    room_name = payload.room_name or f"room-{secrets.token_hex(6)}"
    identity = f"user-{secrets.token_hex(8)}"
    logger.info(
        "issuing session token",
        extra={
            "room_name": room_name,
            "display_name": payload.display_name,
            "phone_number": payload.phone_number,
        },
    )
    token = _build_access_token(identity, payload.display_name, room_name)
    expires_at = time.time() + settings.livekit_token_ttl
    return SessionResponse(
        room_name=room_name,
        identity=identity,
        token=token,
        expires_at=expires_at,
        livekit_url=settings.livekit_url,
    )


@app.get("/api/appointments")
async def list_appointments(phone: str, days_ahead: int = 30, status: Optional[str] = None) -> List[Dict[str, Any]]:
    logger.info(
        "listing appointments",
        extra={"phone": phone, "days_ahead": days_ahead, "status": status},
    )
    start_from = datetime.now(tz=timezone.utc) - timedelta(days=1)
    end_at = datetime.now(tz=timezone.utc) + timedelta(days=days_ahead)
    return await _supabase.list_appointments(
        user_phone=phone,
        status=status,
        start_from=start_from,
        start_to=end_at,
    )


@app.get("/api/summaries")
async def list_summaries(phone: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    logger.info("listing summaries", extra={"phone": phone, "limit": limit})
    return await _supabase.list_call_summaries(user_phone=phone, limit=limit)


@app.get("/api/slots")
async def list_slots(date: Optional[str] = None, service_type: Optional[str] = None) -> List[Dict[str, Any]]:
    logger.info("fetching slots", extra={"date": date, "service_type": service_type})
    return await fetch_slots.execute(
        _supabase,
        _slot_generator,
        date=date,
        service_type=service_type,
    )


@app.get("/api/config")
async def get_config() -> Dict[str, Any]:
    logger.debug("serving config", extra={"livekit_url": settings.livekit_url})
    return {
        "livekit_url": settings.livekit_url,
        "default_timezone": settings.default_timezone,
    }


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("API shutdown requested; closing Supabase client")
    await _supabase.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
