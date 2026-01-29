from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from dateutil import parser

from services.supabase_client import SupabaseClient


async def execute(
    db: SupabaseClient,
    user_phone: str,
    slot_start: str,
    slot_end: Optional[str],
    reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    start_dt = _parse(slot_start)
    end_dt = _parse(slot_end) if slot_end else start_dt + timedelta(minutes=30)
    await db.ensure_slot_free(start_dt)
    await db.enforce_no_overlap(user_phone, start_dt, end_dt)
    record = await db.create_appointment(user_phone, start_dt, end_dt, reason=reason, notes=notes)
    return record


def _parse(value: str) -> datetime:
    dt = parser.isoparse(value)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
