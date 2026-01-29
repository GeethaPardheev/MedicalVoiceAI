from __future__ import annotations

from typing import Any, Dict, Optional

from services.supabase_client import SupabaseClient


async def execute(db: SupabaseClient, phone_number: str, name: Optional[str] = None) -> Dict[str, Any]:
    user = await db.get_user(phone_number)
    if user:
        return user
    return await db.upsert_user(phone_number, name=name)
