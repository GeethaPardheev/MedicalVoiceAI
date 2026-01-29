from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def execute(notes: str = "", action_items: List[str] | None = None) -> Dict[str, Any]:
    return {
        "closed": True,
        "notes": notes,
        "action_items": action_items or [],
        "ended_at": datetime.now(tz=timezone.utc).isoformat(),
    }
