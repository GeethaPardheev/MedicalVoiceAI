from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from dateutil import parser

LOG = logging.getLogger(__name__)


class SupabaseClient:
    """Lightweight Supabase PostgREST helper with async httpx under the hood."""

    def __init__(self) -> None:
        self._base_url = os.getenv("SUPABASE_URL")
        self._api_key = os.getenv("SUPABASE_KEY")
        if not self._base_url or not self._api_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured")
        self._rest_url = f"{self._base_url.rstrip('/')}/rest/v1"
        self._client = httpx.AsyncClient(
            base_url=self._rest_url,
            headers={
                "apikey": self._api_key,
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Prefer": "return=representation",
            },
            timeout=20.0,
        )
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            response = await self._client.get("/users", params={"select": "phone", "limit": 1})
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            LOG.error("Supabase health check failed: %s", exc)
            return False

    @staticmethod
    def normalize_phone(phone: str) -> str:
        digits = "".join(filter(str.isdigit, phone or ""))
        if not digits:
            raise ValueError("phone number required")
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]
        return f"+1{digits}" if len(digits) == 10 else f"+{digits}"

    @staticmethod
    def _iso(dt: datetime) -> str:
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        LOG.debug("supabase request", extra={"method": method, "path": path, "kwargs": kwargs})
        async with self._lock:
            response = await self._client.request(method, path, **kwargs)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                LOG.warning("Supabase endpoint missing: %s %s", method, path)
                # treat missing table/view as empty result so UI can keep working
                return []
            raise
        LOG.debug(
            "supabase response",
            extra={"method": method, "path": path, "status": response.status_code},
        )
        if response.status_code == 204:
            return []
        return response.json()

    async def get_user(self, phone: str) -> Optional[Dict[str, Any]]:
        normalized = self.normalize_phone(phone)
        data = await self._request(
            "GET",
            "/users",
            params={"phone": f"eq.{normalized}", "select": "*"},
        )
        return data[0] if data else None

    async def upsert_user(self, phone: str, name: Optional[str] = None) -> Dict[str, Any]:
        normalized = self.normalize_phone(phone)
        payload = {"phone": normalized}
        if name:
            payload["name"] = name
        data = await self._request("POST", "/users", json=payload)
        return data[0]

    async def update_user_preferences(self, phone: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self.normalize_phone(phone)
        payload = {"preferences": preferences}
        data = await self._request(
            "PATCH",
            "/users",
            params={"phone": f"eq.{normalized}"},
            json=payload,
        )
        return data[0]

    async def list_appointments(
        self,
        user_phone: Optional[str] = None,
        status: Optional[str] = None,
        start_from: Optional[datetime] = None,
        start_to: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"select": "*", "order": "start_time"}
        if user_phone:
            params["user_phone"] = f"eq.{self.normalize_phone(user_phone)}"
        if status:
            params["status"] = f"eq.{status}"
        if start_from:
            params["start_time"] = f"gte.{self._iso(start_from)}"
        if start_to:
            params["start_time"] = f"lt.{self._iso(start_to)}"
        return await self._request("GET", "/appointments", params=params)

    async def create_appointment(
        self,
        user_phone: str,
        start_time: datetime,
        end_time: datetime,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "user_phone": self.normalize_phone(user_phone),
            "start_time": self._iso(start_time),
            "end_time": self._iso(end_time),
            "meta": {"reason": reason, "notes": notes},
        }
        data = await self._request("POST", "/appointments", json=payload)
        return data[0]

    async def update_appointment(
        self,
        appointment_id: str,
        **patch: Any,
    ) -> Dict[str, Any]:
        data = await self._request(
            "PATCH",
            "/appointments",
            params={"id": f"eq.{appointment_id}"},
            json=patch,
        )
        return data[0]

    async def cancel_appointment(self, appointment_id: str) -> Dict[str, Any]:
        payload = {"status": "cancelled"}
        return await self.update_appointment(appointment_id, **payload)

    async def save_call_summary(
        self,
        user_phone: str,
        summary_text: str,
        preferences: Dict[str, Any],
        appointments_in_call: List[Dict[str, Any]],
        cost_breakdown: Optional[Dict[str, Any]] = None,
        timeline: Optional[List[Dict[str, Any]]] = None,
        transcript: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "user_phone": self.normalize_phone(user_phone),
            "summary_text": summary_text,
            "preferences": preferences,
            "appointments_in_call": appointments_in_call,
            "cost_breakdown": cost_breakdown,
        }
        if timeline is not None:
            payload["timeline"] = timeline
        if transcript is not None:
            payload["transcript"] = transcript
        data = await self._request("POST", "/call_summaries", json=payload)
        return data[0]

    async def list_call_summaries(
        self,
        user_phone: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "select": "*",
            "order": "created_at.desc",
            "limit": limit,
        }
        if user_phone:
            params["user_phone"] = f"eq.{self.normalize_phone(user_phone)}"
        return await self._request("GET", "/call_summaries", params=params)

    async def get_appointment(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        data = await self._request(
            "GET",
            "/appointments",
            params={"id": f"eq.{appointment_id}", "select": "*"},
        )
        return data[0] if data else None

    async def list_booked_slots_for_day(self, date_value: datetime) -> List[Dict[str, Any]]:
        start = datetime(date_value.year, date_value.month, date_value.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        params = {
            "select": "id,start_time,end_time,status,user_phone",
            "status": "eq.booked",
            "start_time": f"gte.{self._iso(start)}",
            "end_time": f"lt.{self._iso(end)}",
        }
        return await self._request("GET", "/appointments", params=params)

    async def enforce_no_overlap(
        self, user_phone: str, start_time: datetime, end_time: datetime
    ) -> None:
        params = {
            "select": "id,start_time,end_time,status",
            "user_phone": f"eq.{self.normalize_phone(user_phone)}",
            "status": "eq.booked",
            "start_time": f"lt.{self._iso(end_time)}",
            "end_time": f"gt.{self._iso(start_time)}",
        }
        conflicts = await self._request("GET", "/appointments", params=params)
        if conflicts:
            raise ValueError("User already has a booking during that time window")

    async def ensure_slot_free(self, start_time: datetime) -> None:
        params = {
            "select": "id,user_phone",
            "status": "eq.booked",
            "start_time": f"eq.{self._iso(start_time)}",
        }
        conflicts = await self._request("GET", "/appointments", params=params)
        if conflicts:
            raise ValueError("Slot already booked")

    @staticmethod
    def parse_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        dt = parser.isoparse(value)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
