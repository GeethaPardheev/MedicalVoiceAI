from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, Awaitable, Callable, Dict, List

from services.slot_generator import SlotGenerator
from services.supabase_client import SupabaseClient

from . import (
    book_appointment,
    cancel_appointment,
    end_conversation,
    fetch_slots,
    identify_user,
    modify_appointment,
    retrieve_appointments,
)

ToolHandler = Callable[..., Awaitable[Any]]


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "identify_user",
        "description": "Upsert and fetch user metadata by phone number.",
        "parameters": {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "User phone number"},
                "name": {"type": "string"},
            },
            "required": ["phone_number"],
        },
    },
    {
        "name": "fetch_slots",
        "description": "Get available appointment slots for a given date (defaults next 30 days).",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date"},
                "service_type": {"type": "string"},
            },
        },
    },
    {
        "name": "book_appointment",
        "description": "Book an appointment for a user using start/end datetimes.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_phone": {"type": "string"},
                "slot_start": {"type": "string", "description": "ISO datetime"},
                "slot_end": {"type": "string"},
                "reason": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["user_phone", "slot_start"],
        },
    },
    {
        "name": "retrieve_appointments",
        "description": "List all appointments for a caller.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_phone": {"type": "string"},
                "since": {"type": "string"},
            },
            "required": ["user_phone"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel an existing appointment by ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string"},
            },
            "required": ["appointment_id"],
        },
    },
    {
        "name": "modify_appointment",
        "description": "Move appointment to a new slot.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string"},
                "new_slot_start": {"type": "string"},
                "new_slot_end": {"type": "string"},
            },
            "required": ["appointment_id", "new_slot_start"],
        },
    },
    {
        "name": "end_conversation",
        "description": "Signal that the call is complete and trigger summary generation.",
        "parameters": {
            "type": "object",
            "properties": {
                "notes": {"type": "string"},
                "action_items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
]


class ToolRegistry:
    def __init__(self, db: SupabaseClient, slot_generator: SlotGenerator) -> None:
        self._handlers: Dict[str, ToolHandler] = {
            "identify_user": partial(identify_user.execute, db),
            "fetch_slots": partial(fetch_slots.execute, db, slot_generator),
            "book_appointment": partial(book_appointment.execute, db),
            "retrieve_appointments": partial(retrieve_appointments.execute, db),
            "cancel_appointment": partial(cancel_appointment.execute, db),
            "modify_appointment": partial(modify_appointment.execute, db),
            "end_conversation": lambda **kwargs: asyncio.sleep(0, result=end_conversation.execute(**kwargs)),
        }

    async def dispatch(self, name: str, **kwargs: Any) -> Any:
        handler = self._handlers.get(name)
        if not handler:
            raise KeyError(f"Unknown tool '{name}'")
        return await handler(**kwargs)
