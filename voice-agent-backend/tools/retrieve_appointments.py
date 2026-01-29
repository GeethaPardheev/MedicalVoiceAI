from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from services.supabase_client import SupabaseClient


async def execute(
    db: SupabaseClient,
    user_phone: str,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    start_from = datetime.fromisoformat(since) if since else datetime.now(tz=timezone.utc) - timedelta(days=365)
    records = await db.list_appointments(user_phone=user_phone, start_from=start_from)
    return records
