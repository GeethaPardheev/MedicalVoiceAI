from __future__ import annotations

from typing import Any, Dict

from services.supabase_client import SupabaseClient


async def execute(db: SupabaseClient, appointment_id: str) -> Dict[str, Any]:
    record = await db.cancel_appointment(appointment_id)
    return record
