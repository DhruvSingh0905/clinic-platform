"""Structured cycle log — compound event model.

Events, not states. A cycle is reconstructed from a sequence of
START/DOSE_CHANGE/STOP/MISSED_DOSE events per compound.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    START = "START"
    DOSE_CHANGE = "DOSE_CHANGE"
    STOP = "STOP"
    MISSED_DOSE = "MISSED_DOSE"


class Frequency(str, Enum):
    DAILY = "daily"
    EOD = "eod"             # every other day
    E3D = "e3d"             # every 3 days
    E3_5D = "e3.5d"         # twice a week
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"   # every 2 weeks
    PRN = "prn"             # as needed


class Route(str, Enum):
    IM = "IM"
    SUBQ = "subQ"
    ORAL = "oral"
    TRANSDERMAL = "transdermal"
    SUBLINGUAL = "sublingual"


class SourceQuality(str, Enum):
    PHARMACY = "pharmacy"
    DOMESTIC_UGL = "domestic_ugl"
    INTL_UGL = "intl_ugl"
    UNKNOWN = "unknown"


@dataclass
class CompoundEvent:
    """A single cycle log event."""
    compound_id: str            # FK into compound DB
    event_type: EventType
    timestamp: datetime
    dose_mg: float | None = None      # required for START, DOSE_CHANGE
    frequency: Frequency | None = None
    route: Route | None = None
    source_quality: SourceQuality = SourceQuality.UNKNOWN
    user_notes: str | None = None
    confidence: float = 1.0     # user certainty about UGL contents


@dataclass
class CompoundState:
    """Derived state of a compound at a point in time."""
    compound_id: str
    active: bool
    current_dose_mg: float | None
    frequency: Frequency | None
    route: Route | None
    days_on: int
    start_date: datetime
    last_event: CompoundEvent


def validate_event(event: CompoundEvent) -> list[str]:
    """Validate a compound event. Returns list of issues (empty = valid)."""
    issues = []

    if event.event_type in (EventType.START, EventType.DOSE_CHANGE):
        if event.dose_mg is None or event.dose_mg <= 0:
            issues.append(f"{event.event_type.value} requires positive dose_mg")
        if event.frequency is None:
            issues.append(f"{event.event_type.value} requires frequency")
        if event.route is None:
            issues.append(f"{event.event_type.value} requires route")

    if event.dose_mg is not None and event.dose_mg > 5000:
        issues.append(f"Implausible dose: {event.dose_mg}mg")

    return issues


def derive_state(
    events: list[CompoundEvent],
    at_time: datetime | None = None,
) -> dict[str, CompoundState]:
    """Derive active compound states from event history.

    Args:
        events: All compound events, any order.
        at_time: Point in time to derive state at. Defaults to now.

    Returns:
        Dict of compound_id → CompoundState for compounds with any history.
    """
    if at_time is None:
        at_time = datetime.now()

    # Group events by compound, sort by timestamp
    by_compound: dict[str, list[CompoundEvent]] = {}
    for e in events:
        by_compound.setdefault(e.compound_id, []).append(e)

    states: dict[str, CompoundState] = {}

    for compound_id, compound_events in by_compound.items():
        compound_events.sort(key=lambda e: e.timestamp)

        # Walk events up to at_time
        active = False
        dose = None
        freq = None
        route = None
        start_date = None
        last_event = None

        for e in compound_events:
            if e.timestamp > at_time:
                break
            last_event = e

            if e.event_type == EventType.START:
                active = True
                dose = e.dose_mg
                freq = e.frequency
                route = e.route
                start_date = e.timestamp
            elif e.event_type == EventType.DOSE_CHANGE:
                dose = e.dose_mg
                if e.frequency:
                    freq = e.frequency
                if e.route:
                    route = e.route
            elif e.event_type == EventType.STOP:
                active = False

        if last_event is not None:
            days_on = 0
            if active and start_date:
                days_on = (at_time - start_date).days

            states[compound_id] = CompoundState(
                compound_id=compound_id,
                active=active,
                current_dose_mg=dose if active else None,
                frequency=freq if active else None,
                route=route if active else None,
                days_on=days_on,
                start_date=start_date or last_event.timestamp,
                last_event=last_event,
            )

    return states


def weekly_dose_mg(dose_mg: float, frequency: Frequency) -> float:
    """Calculate weekly equivalent dose from per-administration dose + frequency."""
    multipliers = {
        Frequency.DAILY: 7.0,
        Frequency.EOD: 3.5,
        Frequency.E3D: 7 / 3,
        Frequency.E3_5D: 2.0,
        Frequency.WEEKLY: 1.0,
        Frequency.BIWEEKLY: 0.5,
        Frequency.PRN: 0.0,  # can't calculate
    }
    return round(dose_mg * multipliers.get(frequency, 0), 1)
