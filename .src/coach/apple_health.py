"""Apple Health XML export parser.

Parses the export.xml file from an Apple Health data export to extract:
- Resting heart rate (daily average)
- Heart rate variability (SDNN, daily)
- Weight
- Blood pressure (systolic + diastolic)

Apple Health exports are large XML files (100MB+). We stream-parse with
iterparse to avoid loading the whole thing into memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from xml.etree.ElementTree import iterparse
from pathlib import Path
from collections import defaultdict


# Apple Health type identifiers we care about
TYPES = {
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv_sdnn",
    "HKQuantityTypeIdentifierBodyMass": "weight",
    "HKQuantityTypeIdentifierBloodPressureSystolic": "bp_systolic",
    "HKQuantityTypeIdentifierBloodPressureDiastolic": "bp_diastolic",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": "calories_consumed",
    "HKQuantityTypeIdentifierDietaryProtein": "protein",
    "HKQuantityTypeIdentifierDietaryFatTotal": "fat",
    "HKQuantityTypeIdentifierDietaryCarbohydrates": "carbs",
}

# Workout activity type classification
WORKOUT_CATEGORIES = {
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "strength",
    "HKWorkoutActivityTypeFunctionalStrengthTraining": "strength",
    "HKWorkoutActivityTypeCrossTraining": "strength",
    "HKWorkoutActivityTypeRunning": "cardio",
    "HKWorkoutActivityTypeCycling": "cardio",
    "HKWorkoutActivityTypeSwimming": "cardio",
    "HKWorkoutActivityTypeRowing": "cardio",
    "HKWorkoutActivityTypeElliptical": "cardio",
    "HKWorkoutActivityTypeStairClimbing": "cardio",
    "HKWorkoutActivityTypeHighIntensityIntervalTraining": "mixed",
    "HKWorkoutActivityTypeMixedCardio": "mixed",
    "HKWorkoutActivityTypeWalking": "low_intensity",
    "HKWorkoutActivityTypeYoga": "low_intensity",
    "HKWorkoutActivityTypePilates": "low_intensity",
    "HKWorkoutActivityTypeCoreTraining": "strength",
}


@dataclass
class HealthRecord:
    """A single health data point from Apple Health."""
    metric: str                # resting_hr, hrv_sdnn, weight, bp_systolic, bp_diastolic
    value: float
    unit: str
    timestamp: datetime
    source: str = ""           # device/app that recorded it


@dataclass
class DailyAggregate:
    """Daily roll-up of a metric."""
    metric: str
    date: date
    mean: float
    min: float
    max: float
    count: int
    unit: str


@dataclass
class WorkoutSummary:
    """Daily workout summary — one per day."""
    date: date
    training_type: str        # strength, cardio, mixed, low_intensity, rest
    duration_min: float
    calories: float
    hr_avg: float | None = None
    hr_max: float | None = None
    intensity: str = "moderate"  # low, moderate, high, very_high
    workout_count: int = 1


@dataclass
class AppleHealthExport:
    """Parsed Apple Health export data."""
    records: list[HealthRecord] = field(default_factory=list)
    daily: list[DailyAggregate] = field(default_factory=list)
    workouts: list[WorkoutSummary] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    record_count: int = 0
    skipped_count: int = 0


def parse_apple_health_xml(
    xml_path: str | Path,
    start_date: date | None = None,
    end_date: date | None = None,
) -> AppleHealthExport:
    """Parse an Apple Health export.xml file.

    Args:
        xml_path: Path to export.xml
        start_date: Only include records on or after this date (optional)
        end_date: Only include records on or before this date (optional)

    Returns:
        AppleHealthExport with records and daily aggregates.
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"Apple Health export not found: {xml_path}")

    result = AppleHealthExport()
    records_by_day: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    units_by_metric: dict[str, str] = {}

    workouts_by_day: dict[str, list[dict]] = defaultdict(list)

    for event, elem in iterparse(str(xml_path), events=("end",)):
        # Parse Workout elements
        if elem.tag == "Workout":
            try:
                activity = elem.get("workoutActivityType", "")
                duration = float(elem.get("duration", 0))
                calories = float(elem.get("totalEnergyBurned", 0))
                start_str = elem.get("startDate", "")
                ts = _parse_apple_timestamp(start_str)
                if ts:
                    workout_date = ts.date()
                    if start_date and workout_date < start_date:
                        elem.clear()
                        continue
                    if end_date and workout_date > end_date:
                        elem.clear()
                        continue
                    category = WORKOUT_CATEGORIES.get(activity, "mixed")
                    workouts_by_day[workout_date.isoformat()].append({
                        "type": category, "duration": duration, "calories": calories,
                    })
            except (ValueError, TypeError):
                pass
            elem.clear()
            continue

        if elem.tag != "Record":
            elem.clear()
            continue

        record_type = elem.get("type", "")
        metric = TYPES.get(record_type)

        if metric is None:
            result.skipped_count += 1
            elem.clear()
            continue

        try:
            value = float(elem.get("value", ""))
            unit = elem.get("unit", "")
            start_str = elem.get("startDate", "")
            source = elem.get("sourceName", "")

            # Parse timestamp: "2024-03-15 08:30:00 -0700"
            ts = _parse_apple_timestamp(start_str)
            if ts is None:
                result.parse_errors.append(f"Bad timestamp: {start_str}")
                elem.clear()
                continue

            record_date = ts.date()

            # Date filtering
            if start_date and record_date < start_date:
                elem.clear()
                continue
            if end_date and record_date > end_date:
                elem.clear()
                continue

            # Plausibility check
            if not _plausible(metric, value):
                result.parse_errors.append(
                    f"Implausible {metric}: {value} {unit} at {ts}"
                )
                elem.clear()
                continue

            # Unit normalization
            value, unit = _normalize_unit(metric, value, unit)

            record = HealthRecord(
                metric=metric,
                value=value,
                unit=unit,
                timestamp=ts,
                source=source,
            )
            result.records.append(record)
            result.record_count += 1

            # Accumulate for daily aggregates
            day_key = record_date.isoformat()
            records_by_day[day_key][metric].append(value)
            units_by_metric[metric] = unit

        except (ValueError, TypeError) as e:
            result.parse_errors.append(f"Parse error: {e}")

        elem.clear()

    # Build daily aggregates
    for day_str, metrics in sorted(records_by_day.items()):
        for metric, values in metrics.items():
            result.daily.append(DailyAggregate(
                metric=metric,
                date=date.fromisoformat(day_str),
                mean=round(sum(values) / len(values), 2),
                min=round(min(values), 2),
                max=round(max(values), 2),
                count=len(values),
                unit=units_by_metric.get(metric, ""),
            ))

    # Build workout summaries per day
    for day_str, day_workouts in sorted(workouts_by_day.items()):
        total_dur = sum(w["duration"] for w in day_workouts)
        total_cal = sum(w["calories"] for w in day_workouts)
        # Pick the dominant training type
        types = [w["type"] for w in day_workouts]
        if "strength" in types and "cardio" in types:
            training_type = "mixed"
        elif "strength" in types:
            training_type = "strength"
        elif "cardio" in types:
            training_type = "cardio"
        elif "low_intensity" in types:
            training_type = "low_intensity"
        else:
            training_type = "mixed"

        # Estimate intensity from duration + calories (rough proxy without HR data)
        cal_per_min = total_cal / total_dur if total_dur > 0 else 0
        if cal_per_min > 12:
            intensity = "very_high"
        elif cal_per_min > 8:
            intensity = "high"
        elif cal_per_min > 5:
            intensity = "moderate"
        else:
            intensity = "low"

        result.workouts.append(WorkoutSummary(
            date=date.fromisoformat(day_str),
            training_type=training_type,
            duration_min=round(total_dur, 1),
            calories=round(total_cal, 0),
            intensity=intensity,
            workout_count=len(day_workouts),
        ))

    return result


def _parse_apple_timestamp(s: str) -> datetime | None:
    """Parse Apple Health timestamp format: '2024-03-15 08:30:00 -0700'."""
    if not s:
        return None
    try:
        # Strip timezone offset for simplicity — Apple Health uses local time
        # Format: "2024-03-15 08:30:00 -0700"
        parts = s.rsplit(" ", 1)
        if len(parts) == 2:
            return datetime.fromisoformat(parts[0])
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _normalize_unit(metric: str, value: float, unit: str) -> tuple[float, str]:
    """Normalize units to canonical form."""
    # Weight: lbs → kg
    if metric == "weight" and unit == "lb":
        return round(value * 0.453592, 2), "kg"
    # HR units are always count/min (bpm)
    if metric in ("resting_hr", "heart_rate") and unit == "count/min":
        return value, "bpm"
    # HRV is always ms
    if metric == "hrv_sdnn" and unit == "ms":
        return value, "ms"
    # BP is always mmHg
    if metric in ("bp_systolic", "bp_diastolic") and unit == "mmHg":
        return value, "mmHg"
    return value, unit


PLAUSIBILITY = {
    "resting_hr": (25, 130),
    "heart_rate": (25, 250),
    "hrv_sdnn": (1, 300),
    "weight": (30, 250),        # kg after conversion
    "bp_systolic": (60, 250),
    "bp_diastolic": (30, 160),
}


def _plausible(metric: str, value: float) -> bool:
    """Check if a value is within plausible range."""
    bounds = PLAUSIBILITY.get(metric)
    if bounds is None:
        return True
    return bounds[0] <= value <= bounds[1]
