from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from dateutil import parser

from services.supabase_client import SupabaseClient


async def execute(
    db: SupabaseClient,
    appointment_id: str,
    new_slot_start: str,
    new_slot_end: str,
) -> Dict[str, Any]:
    start_dt = _parse(new_slot_start)
    end_dt = _parse(new_slot_end) if new_slot_end else start_dt + timedelta(minutes=30)
    existing = await db.get_appointment(appointment_id)
    if not existing:
        raise ValueError("Appointment not found")
    user_phone = existing["user_phone"]
    await db.ensure_slot_free(start_dt)
    await db.enforce_no_overlap(user_phone, start_dt, end_dt)
    updated = await db.update_appointment(
        appointment_id,
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
    )
    return updated


def _parse(value: str) -> datetime:
    dt = parser.isoparse(value)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
