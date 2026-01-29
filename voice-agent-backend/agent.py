from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, Any, Dict, Optional

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AutoSubscribe,
    CloseEvent,
    ConversationItemAddedEvent,
    FunctionToolsExecutedEvent,
    JobContext,
    RunContext,
    cli,
    inference,
    room_io,
)
from livekit.agents.llm import ToolError, function_tool
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from pydantic import Field

from services import LLMService, SlotGenerator, SupabaseClient
from settings import get_settings
from state import CallState
from tools import TOOL_SCHEMAS, ToolRegistry

logger = logging.getLogger("voice-agent")
settings = get_settings()

_supabase = SupabaseClient()
_slot_generator = SlotGenerator(settings.default_timezone)
_toolkit = ToolRegistry(_supabase, _slot_generator)
_llm_service = LLMService(TOOL_SCHEMAS)
_vad_model = silero.VAD.load()

AGENT_INSTRUCTIONS = """
You are Aida, a medical front-desk assistant who books, modifies, and cancels appointments.
Follow this playbook:
1. Warmly greet the caller and explain that the line is recorded.
2. Use identify_user to capture and normalize the caller's phone number before touching the calendar.
3. Collect intent (new booking, modify, cancel, info) and confirm service type + preferred day window.
4. Use fetch_slots to reason about availability, then book_appointment or modify_appointment as needed.
5. Always confirm start/end time, timezone, and purpose back to the caller before finalizing.
6. If user is unsure, propose two concrete options and highlight follow-up steps.
7. End every successful call with end_conversation and capture any action items.
Tone guidelines: efficient, empathetic, concise, no emojis, no markdown lists unless summarizing.
""".strip()


def _build_tts() -> inference.TTS:
    kwargs: Dict[str, Any] = {}
    if settings.tts_voice_id:
        kwargs["voice"] = settings.tts_voice_id
    return inference.TTS(settings.tts_model, **kwargs)


class SchedulerAgent(Agent):
    def __init__(self, toolkit: ToolRegistry) -> None:
        super().__init__(instructions=AGENT_INSTRUCTIONS)
        self._toolkit = toolkit

    def _guard_phone(self, context: RunContext[CallState], supplied: Optional[str]) -> str:
        phone = supplied or context.userdata.user_phone
        if not phone:
            raise ToolError("Caller phone number is unknown. Run identify_user first.")
        return phone

    def _log_tool(self, name: str, stage: str, **payload: Any) -> None:
        logger.info(
            "tool %s %s",
            name,
            stage,
            extra={"tool": name, "stage": stage, **payload},
        )

    @function_tool
    async def identify_user(
        self,
        context: RunContext[CallState],
        phone_number: Annotated[str, Field(description="Caller phone number (any format)")],
        name: Annotated[str | None, Field(description="Caller preferred name")] = None,
    ) -> Dict[str, Any]:
        self._log_tool("identify_user", "start", phone=phone_number, provided_name=name)
        try:
            record = await self._toolkit.dispatch("identify_user", phone_number=phone_number, name=name)
        except ValueError as exc:  # pragma: no cover - defensive guard for LLM misuse
            raise ToolError(str(exc)) from exc
        context.userdata.user_phone = record.get("phone") or phone_number
        context.userdata.user_name = record.get("name") or name
        prefs = record.get("preferences")
        if isinstance(prefs, dict):
            context.userdata.preferences = prefs
        context.userdata.record_tool(
            name="identify_user",
            arguments={"phone_number": phone_number, "name": name},
            output=record,
        )
        self._log_tool("identify_user", "complete", normalized_phone=context.userdata.user_phone)
        return record

    @function_tool
    async def fetch_slots(
        self,
        context: RunContext[CallState],
        date: Annotated[str | None, Field(description="ISO date to anchor availability")] = None,
        service_type: Annotated[str | None, Field(description="Consult, follow_up, extended, etc.")] = None,
    ) -> Any:
        payload = {"date": date, "service_type": service_type}
        self._log_tool("fetch_slots", "start", **{k: v for k, v in payload.items() if v})
        slots = await self._toolkit.dispatch("fetch_slots", **payload)
        context.userdata.record_tool("fetch_slots", arguments=payload, output=slots)
        self._log_tool("fetch_slots", "complete", slot_count=len(slots) if isinstance(slots, list) else None)
        return slots

    @function_tool
    async def book_appointment(
        self,
        context: RunContext[CallState],
        slot_start: Annotated[str, Field(description="ISO start datetime")],
        slot_end: Annotated[str | None, Field(description="ISO end datetime")] = None,
        reason: Annotated[str | None, Field(description="Visit reason")] = None,
        notes: Annotated[str | None, Field(description="Internal notes")] = None,
        user_phone: Annotated[str | None, Field(description="Override phone number")] = None,
    ) -> Dict[str, Any]:
        phone = self._guard_phone(context, user_phone)
        payload = {
            "user_phone": phone,
            "slot_start": slot_start,
            "slot_end": slot_end,
            "reason": reason,
            "notes": notes,
        }
        self._log_tool("book_appointment", "start", **payload)
        record = await self._toolkit.dispatch("book_appointment", **payload)
        context.userdata.appointments_in_call.append(record)
        context.userdata.record_tool("book_appointment", arguments=payload, output=record)
        self._log_tool("book_appointment", "complete", appointment_id=record.get("id"))
        return record

    @function_tool
    async def retrieve_appointments(
        self,
        context: RunContext[CallState],
        since: Annotated[str | None, Field(description="Optional ISO datetime filter")] = None,
        user_phone: Annotated[str | None, Field(description="Override phone number")] = None,
    ) -> Any:
        phone = self._guard_phone(context, user_phone)
        payload = {"user_phone": phone, "since": since}
        self._log_tool("retrieve_appointments", "start", **payload)
        records = await self._toolkit.dispatch("retrieve_appointments", **payload)
        context.userdata.record_tool("retrieve_appointments", arguments=payload, output=records)
        self._log_tool("retrieve_appointments", "complete", count=len(records) if isinstance(records, list) else None)
        return records

    @function_tool
    async def cancel_appointment(
        self,
        context: RunContext[CallState],
        appointment_id: Annotated[str, Field(description="Appointment identifier")],
    ) -> Dict[str, Any]:
        payload = {"appointment_id": appointment_id}
        self._log_tool("cancel_appointment", "start", **payload)
        record = await self._toolkit.dispatch("cancel_appointment", **payload)
        context.userdata.appointments_in_call.append(record)
        context.userdata.record_tool("cancel_appointment", arguments=payload, output=record)
        self._log_tool("cancel_appointment", "complete", result_status=record.get("status"))
        return record

    @function_tool
    async def modify_appointment(
        self,
        context: RunContext[CallState],
        appointment_id: Annotated[str, Field(description="Appointment identifier")],
        new_slot_start: Annotated[str, Field(description="New slot start")],
        new_slot_end: Annotated[str | None, Field(description="New slot end")] = None,
    ) -> Dict[str, Any]:
        payload = {
            "appointment_id": appointment_id,
            "new_slot_start": new_slot_start,
            "new_slot_end": new_slot_end,
        }
        self._log_tool("modify_appointment", "start", **payload)
        record = await self._toolkit.dispatch("modify_appointment", **payload)
        context.userdata.appointments_in_call.append(record)
        context.userdata.record_tool("modify_appointment", arguments=payload, output=record)
        self._log_tool("modify_appointment", "complete", appointment_id=appointment_id)
        return record

    @function_tool
    async def end_conversation(
        self,
        context: RunContext[CallState],
        notes: Annotated[str | None, Field(description="Wrap-up notes")] = None,
        action_items: Annotated[list[str] | None, Field(description="Call follow-ups")] = None,
    ) -> Dict[str, Any]:
        payload = {"notes": notes, "action_items": action_items}
        self._log_tool("end_conversation", "start", has_notes=bool(notes), action_items=len(action_items or []))
        result = await self._toolkit.dispatch("end_conversation", **payload)
        context.userdata.final_notes = result.get("notes")
        context.userdata.action_items = result.get("action_items", [])
        context.userdata.record_tool("end_conversation", arguments=payload, output=result)
        asyncio.create_task(finalize_call(context.userdata, trigger="end_conversation"))
        self._log_tool("end_conversation", "complete", status=result.get("status"))
        return {
            "status": "closing",
            "message": "Happy to help. Expect a confirmation text shortly.",
        }


class SessionEventBridge:
    def __init__(self, state: CallState, room: rtc.Room | None) -> None:
        self._state = state
        self._room = room

    def bind(self, session: AgentSession[CallState]) -> None:
        logger.info("binding session event bridge", extra={"room": self._room.name if self._room else None})
        session.on("conversation_item_added", self._on_conversation_item)
        session.on("function_tools_executed", self._on_tool_event)
        session.on("close", self._on_close)

    def _text_from_item(self, item: Any) -> str:
        if not getattr(item, "content", None):
            return ""
        parts = [chunk for chunk in item.content if isinstance(chunk, str)]
        return "\n".join(parts)

    def _speaker_from_role(self, role: str) -> str:
        if role == "assistant":
            return "assistant"
        if role == "system":
            return "system"
        return "user"

    def _publish_data(self, topic: str, payload: Dict[str, Any]) -> None:
        if not self._room:
            return
        logger.debug("publishing data", extra={"topic": topic, "payload": payload})

        async def _task() -> None:
            try:
                data = json.dumps(payload).encode("utf-8")
                result = self._room.local_participant.publish_data(data, topic=topic)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:  # pragma: no cover - defensive network guard
                logger.debug("failed to publish data", exc_info=exc)
        asyncio.create_task(_task())

    def _on_conversation_item(self, event: ConversationItemAddedEvent) -> None:
        text = self._text_from_item(event.item)
        if not text:
            return
        speaker = self._speaker_from_role(event.item.role)
        logger.debug(
            "conversation item",
            extra={"speaker": speaker, "item_id": event.item.id, "chars": len(text)},
        )
        self._state.add_transcript(speaker, text, event.item.id, event.item.created_at)
        self._publish_data(
            "app.transcript",
            {
                "type": "transcript",
                "speaker": speaker,
                "text": text,
                "timestamp": event.item.created_at,
                "item_id": event.item.id,
            },
        )

    def _on_tool_event(self, event: FunctionToolsExecutedEvent) -> None:
        for call, output in event.zipped():
            try:
                args = json.loads(call.arguments or "{}")
            except json.JSONDecodeError:
                args = {"raw": call.arguments}
            parsed_output: Any = None
            if output and output.output:
                try:
                    parsed_output = json.loads(output.output)
                except json.JSONDecodeError:
                    parsed_output = output.output
            logger.info(
                "tool event",
                extra={
                    "name": call.name,
                    "call_id": call.call_id,
                    "has_output": parsed_output is not None,
                },
            )
            self._state.record_tool(
                name=call.name,
                arguments=args,
                output=parsed_output,
                call_id=call.call_id,
                created_at=call.created_at,
            )
            self._publish_data(
                "app.timeline",
                {
                    "type": "tool",
                    "name": call.name,
                    "arguments": args,
                    "output": parsed_output,
                    "timestamp": call.created_at,
                    "call_id": call.call_id,
                },
            )

    def _on_close(self, _: CloseEvent) -> None:
        logger.info("session close received", extra={"room": self._room.name if self._room else None})
        asyncio.create_task(finalize_call(self._state, trigger="session_close"))


async def finalize_call(state: CallState, *, trigger: str) -> None:
    if not state.user_phone:
        logger.debug("finalize skipped (missing phone)", extra={"session_id": state.session_id})
        return
    async with state.summary_lock:
        if state.summary_saved:
            logger.debug("finalize skipped (already saved)", extra={"session_id": state.session_id})
            return
        logger.info("summarizing call", extra={"session_id": state.session_id, "trigger": trigger})
        summary = await _llm_service.summarize_call(
            transcript=state.to_summary_transcript(),
            appointments=state.appointments_in_call,
            preferences=state.preferences_payload(),
        )
        await _supabase.save_call_summary(
            user_phone=state.user_phone,
            summary_text=summary["summary_text"],
            preferences=state.preferences_payload(),
            appointments_in_call=state.appointments_in_call,
            cost_breakdown=summary.get("usage"),
            timeline=state.timeline_payload(),
            transcript=state.to_summary_transcript(),
        )
        state.summary_saved = True
        logger.info("call summary persisted", extra={"trigger": trigger, "session_id": state.session_id})


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("agent session started", extra={"room": ctx.room.name, "job_id": ctx.job.job_id})
    state = CallState(room_name=ctx.room.name, user_identity=ctx.room.local_participant.identity)
    session = AgentSession[CallState](
        userdata=state,
        stt=inference.STT(settings.stt_model),
        llm=inference.LLM(settings.llm_model),
        tts=_build_tts(),
        vad=_vad_model,
        turn_detection=MultilingualModel(),
        max_tool_steps=6,
        preemptive_generation=True,
    )
    bridge = SessionEventBridge(state, ctx.room)
    bridge.bind(session)
    agent = SchedulerAgent(_toolkit)
    ctx.add_shutdown_callback(lambda: finalize_call(state, trigger="shutdown"))
    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=True,
            audio_output=True,
            transcription_output=True,
            text_output=room_io.TextOutputOptions(transcription_speed_factor=1.2),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
