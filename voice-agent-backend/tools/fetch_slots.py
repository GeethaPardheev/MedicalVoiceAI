from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil import parser

from services.slot_generator import SlotGenerator
from services.supabase_client import SupabaseClient


async def execute(
    db: SupabaseClient,
    slots: SlotGenerator,
    date: Optional[str] = None,
    service_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if date:
        parsed_date = parser.parse(date).date()
    else:
        parsed_date = datetime.now(tz=slots.zone).date()
    generated = slots.generate_for_date(parsed_date, service_type)
    booked = await db.list_booked_slots_for_day(datetime.combine(parsed_date, datetime.min.time(), tzinfo=slots.zone))
    booked_set = {b["start_time"] for b in booked if b.get("status") == "booked"}
    available = [slot.to_dict() for slot in generated if slot.start_time.isoformat() not in booked_set]
    return available
