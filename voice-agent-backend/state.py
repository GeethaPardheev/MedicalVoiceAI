from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4


TranscriptSpeaker = Literal["user", "assistant", "system"]


@dataclass
class TranscriptSegment:
    speaker: TranscriptSpeaker
    text: str
    timestamp: float
    item_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "timestamp": self.timestamp,
            "iso_time": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "item_id": self.item_id,
        }


@dataclass
class ToolExecution:
    name: str
    arguments: Dict[str, Any]
    output: Any
    timestamp: float
    call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "output": self.output,
            "timestamp": self.timestamp,
            "iso_time": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "call_id": self.call_id,
        }


@dataclass
class CallState:
    room_name: str
    session_id: str = field(default_factory=lambda: uuid4().hex)
    user_identity: str | None = None
    user_phone: str | None = None
    user_name: str | None = None
    transcript: List[TranscriptSegment] = field(default_factory=list)
    tool_events: List[ToolExecution] = field(default_factory=list)
    appointments_in_call: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    final_notes: str | None = None
    action_items: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    summary_saved: bool = False
    summary_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def add_transcript(self, speaker: TranscriptSpeaker, text: str, item_id: str, created_at: float) -> None:
        self.transcript.append(
            TranscriptSegment(
                speaker=speaker,
                text=text.strip(),
                timestamp=created_at,
                item_id=item_id,
            )
        )

    def record_tool(self, name: str, arguments: Dict[str, Any], output: Any, *, call_id: str | None = None, created_at: float | None = None) -> None:
        self.tool_events.append(
            ToolExecution(
                name=name,
                arguments=arguments,
                output=output,
                timestamp=created_at or time.time(),
                call_id=call_id,
            )
        )

    def to_summary_transcript(self) -> List[Dict[str, Any]]:
        return [segment.to_dict() for segment in self.transcript]

    def timeline_payload(self) -> List[Dict[str, Any]]:
        return [event.to_dict() for event in self.tool_events]

    def preferences_payload(self) -> Dict[str, Any]:
        payload = dict(self.preferences)
        if self.final_notes:
            payload["call_notes"] = self.final_notes
        if self.action_items:
            payload["action_items"] = self.action_items
        return payload
