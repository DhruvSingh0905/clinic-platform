"""Blood pressure manual entry with validation.

MVP: manual entry only. v2: Withings BPM API integration.
Time-of-day matters for BP (morning readings are clinical standard).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BPReading:
    systolic: int
    diastolic: int
    heart_rate: int | None = None   # some cuffs report this
    timestamp: datetime = None
    time_of_day: str = ""           # "morning", "evening", "post_workout", "random"
    position: str = "seated"        # "seated", "standing", "supine"
    notes: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


def validate_bp(reading: BPReading) -> list[str]:
    """Validate a BP reading. Returns list of issues (empty = valid)."""
    issues = []

    if not 60 <= reading.systolic <= 250:
        issues.append(f"Implausible systolic: {reading.systolic}")
    if not 30 <= reading.diastolic <= 160:
        issues.append(f"Implausible diastolic: {reading.diastolic}")
    if reading.systolic <= reading.diastolic:
        issues.append("Systolic must be greater than diastolic")
    if reading.heart_rate is not None and not 30 <= reading.heart_rate <= 200:
        issues.append(f"Implausible heart rate: {reading.heart_rate}")

    return issues


def classify_bp(systolic: int, diastolic: int) -> str:
    """Classify BP per AHA guidelines. Informational only."""
    if systolic < 120 and diastolic < 80:
        return "normal"
    elif systolic < 130 and diastolic < 80:
        return "elevated"
    elif systolic < 140 or diastolic < 90:
        return "stage_1_hypertension"
    else:
        return "stage_2_hypertension"
