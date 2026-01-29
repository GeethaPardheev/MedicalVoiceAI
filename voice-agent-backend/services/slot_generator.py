from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

DEFAULT_SERVICE_LENGTHS = {
    "default": 30,
    "consult": 45,
    "follow_up": 30,
    "extended": 60,
}


@dataclass
class Slot:
    start_time: datetime
    end_time: datetime

    def to_dict(self) -> Dict[str, str]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
        }


class SlotGenerator:
    """Generates deterministic appointment slots."""

    def __init__(
        self,
        timezone_name: str = "America/Los_Angeles",
        workday_start: time = time(hour=9),
        workday_end: time = time(hour=17),
        interval_minutes: int = 30,
    ) -> None:
        self.zone = ZoneInfo(timezone_name)
        self.workday_start = workday_start
        self.workday_end = workday_end
        self.interval = timedelta(minutes=interval_minutes)

    def _service_length(self, service_type: Optional[str]) -> timedelta:
        minutes = DEFAULT_SERVICE_LENGTHS.get(service_type or "", DEFAULT_SERVICE_LENGTHS["default"])
        return timedelta(minutes=minutes)

    def generate_for_date(
        self,
        target_date: Optional[date] = None,
        service_type: Optional[str] = None,
    ) -> List[Slot]:
        target_date = target_date or datetime.now(tz=self.zone).date()
        start_dt = datetime.combine(target_date, self.workday_start, tzinfo=self.zone)
        end_dt = datetime.combine(target_date, self.workday_end, tzinfo=self.zone)
        slots: List[Slot] = []
        service_len = self._service_length(service_type)
        cursor = start_dt
        while cursor + service_len <= end_dt:
            slots.append(Slot(start_time=cursor, end_time=cursor + service_len))
            cursor += self.interval
        return slots

    def generate_next_days(
        self,
        days: int = 30,
        service_type: Optional[str] = None,
    ) -> List[Slot]:
        today = datetime.now(tz=self.zone).date()
        slots: List[Slot] = []
        for offset in range(days):
            target = today + timedelta(days=offset)
            slots.extend(self.generate_for_date(target, service_type))
        return slots
