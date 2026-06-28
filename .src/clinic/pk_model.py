"""First-order single-compartment PK model for drug level timeline.

Generates day-by-day estimated relative concentration for every active
compound based on dose, frequency, half-life, and event history.

This is approximate — document in every output. For UGL compounds,
source_quality affects confidence, not the model itself.

Model: C(t) = sum of contributions from each dose
  Each dose contributes: dose_mg * (0.5 ^ (hours_since_dose / half_life_hours))
  Normalized to steady-state peak = 1.0 for interpretability.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from clinic.compound_db import COMPOUNDS


def generate_drug_levels(
    conn: sqlite3.Connection,
    user_id: str = "default",
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Generate drug level timeline for all compounds in the user's event history.

    Reads compound_event, writes to drug_level table.
    Returns total rows written.
    """
    if end_date is None:
        end_date = date.today()

    # Get all compound events for user
    rows = conn.execute(
        """SELECT compound_id, event_type, timestamp, dose_mg, frequency
           FROM compound_event
           WHERE user_id = ?
           ORDER BY timestamp""",
        (user_id,),
    ).fetchall()

    if not rows:
        return 0

    # Group events by compound
    events_by_compound: dict[str, list[dict]] = {}
    for r in rows:
        cid = r["compound_id"]
        events_by_compound.setdefault(cid, []).append({
            "event_type": r["event_type"],
            "timestamp": datetime.fromisoformat(r["timestamp"]),
            "dose_mg": r["dose_mg"],
            "frequency": r["frequency"],
        })

    # Find earliest event if no start_date given
    if start_date is None:
        earliest = min(e["timestamp"] for events in events_by_compound.values() for e in events)
        start_date = earliest.date()

    total = 0
    for compound_id, events in events_by_compound.items():
        compound = COMPOUNDS.get(compound_id)
        if not compound or not compound.half_life_hours:
            continue

        count = _generate_for_compound(
            conn, user_id, compound_id, events,
            compound.half_life_hours, start_date, end_date,
        )
        total += count

    conn.commit()
    return total


def _generate_for_compound(
    conn: sqlite3.Connection,
    user_id: str,
    compound_id: str,
    events: list[dict],
    half_life_hours: float,
    start_date: date,
    end_date: date,
) -> int:
    """Generate daily drug levels for a single compound."""
    # Build a list of all individual doses administered
    doses = _expand_doses(events, start_date, end_date)

    if not doses:
        return 0

    # Calculate steady-state peak for normalization
    # Steady state ≈ after 5 half-lives of consistent dosing
    steady_state_peak = _estimate_steady_state_peak(doses, half_life_hours, events)
    if steady_state_peak <= 0:
        steady_state_peak = 1.0  # avoid div by zero

    # Find the START date for days_since_start
    compound_start = None
    for e in events:
        if e["event_type"] == "START":
            compound_start = e["timestamp"]
            break

    # For each day in range, sum contributions from all prior doses
    count = 0
    current = start_date
    while current <= end_date:
        current_dt = datetime.combine(current, datetime.min.time().replace(hour=12))  # noon
        total_level = 0.0
        total_active_mg = 0.0

        for dose_time, dose_mg in doses:
            hours_since = (current_dt - dose_time).total_seconds() / 3600
            if hours_since < 0:
                continue
            # First-order decay
            remaining = dose_mg * (0.5 ** (hours_since / half_life_hours))
            # Ignore negligible contributions (< 0.1% of dose)
            if remaining > dose_mg * 0.001:
                total_level += remaining
                total_active_mg += remaining

        # Normalize to 0-1 scale (1 = steady-state peak at current dose)
        # After dose reduction, levels can exceed 1.0 as residual
        # higher-dose compound decays toward new steady state
        normalized = min(total_level / steady_state_peak, 5.0)  # cap at 5x for dose changes

        days_since = (current - compound_start.date()).days if compound_start else 0
        # Steady state reached after ~5 half-lives
        five_half_lives_days = (5 * half_life_hours) / 24
        at_steady = 1 if days_since >= five_half_lives_days else 0

        conn.execute(
            """INSERT OR REPLACE INTO drug_level
               (user_id, compound_id, observation_date, estimated_level,
                dose_active_mg, days_since_start, at_steady_state)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, compound_id, current.isoformat(),
             round(normalized, 4), round(total_active_mg, 2),
             days_since, at_steady),
        )
        count += 1
        current += timedelta(days=1)

    return count


def _expand_doses(
    events: list[dict],
    start_date: date,
    end_date: date,
) -> list[tuple[datetime, float]]:
    """Expand compound events into individual dose administrations.

    Given START/DOSE_CHANGE/STOP events with frequency, generate
    each individual dose (datetime, mg) within the date range.
    """
    doses: list[tuple[datetime, float]] = []
    active = False
    current_dose = 0.0
    current_freq_hours = 0.0
    last_dose_time: datetime | None = None

    for e in sorted(events, key=lambda x: x["timestamp"]):
        if e["event_type"] == "START":
            active = True
            current_dose = e["dose_mg"] or 0
            current_freq_hours = _freq_to_hours(e.get("frequency"))
            # First dose at start time
            if current_dose > 0:
                doses.append((e["timestamp"], current_dose))
                last_dose_time = e["timestamp"]

        elif e["event_type"] == "DOSE_CHANGE":
            # Fill doses from last event to this one at old dose
            if active and last_dose_time and current_freq_hours > 0:
                doses.extend(_fill_doses(
                    last_dose_time, e["timestamp"],
                    current_dose, current_freq_hours,
                ))
            current_dose = e["dose_mg"] or current_dose
            if e.get("frequency"):
                current_freq_hours = _freq_to_hours(e["frequency"])
            doses.append((e["timestamp"], current_dose))
            last_dose_time = e["timestamp"]

        elif e["event_type"] == "STOP":
            # Fill remaining doses up to stop
            if active and last_dose_time and current_freq_hours > 0:
                doses.extend(_fill_doses(
                    last_dose_time, e["timestamp"],
                    current_dose, current_freq_hours,
                ))
            active = False
            last_dose_time = None

    # If still active, fill doses up to end_date
    if active and last_dose_time and current_freq_hours > 0:
        end_dt = datetime.combine(end_date, datetime.min.time().replace(hour=23, minute=59))
        doses.extend(_fill_doses(
            last_dose_time, end_dt,
            current_dose, current_freq_hours,
        ))

    return doses


def _fill_doses(
    from_dt: datetime,
    to_dt: datetime,
    dose_mg: float,
    freq_hours: float,
) -> list[tuple[datetime, float]]:
    """Generate individual dose events between two timestamps."""
    doses = []
    if freq_hours <= 0 or dose_mg <= 0:
        return doses

    t = from_dt + timedelta(hours=freq_hours)
    while t < to_dt:
        doses.append((t, dose_mg))
        t += timedelta(hours=freq_hours)

    return doses


def _freq_to_hours(freq: str | None) -> float:
    """Convert frequency string to hours between doses."""
    if not freq:
        return 0
    mapping = {
        "daily": 24,
        "eod": 48,
        "e3d": 72,
        "e3.5d": 84,
        "weekly": 168,
        "biweekly": 336,
        "prn": 0,
    }
    return mapping.get(freq, 0)


def _estimate_steady_state_peak(
    doses: list[tuple[datetime, float]],
    half_life_hours: float,
    events: list[dict] | None = None,
) -> float:
    """Estimate the steady-state peak at the CURRENT dosing regimen.

    Calculates what the theoretical peak would be if the most recent
    dose and frequency were maintained to steady state (~10 half-lives).

    This means after a dose change, the new steady state becomes 100%
    and residual higher-dose levels show >100%, decaying naturally.
    """
    if not doses:
        return 1.0

    # Find the most recent dose amount and frequency from events
    current_dose = 0.0
    current_freq_hours = 0.0
    if events:
        for e in sorted(events, key=lambda x: x["timestamp"], reverse=True):
            if e["event_type"] in ("START", "DOSE_CHANGE"):
                current_dose = e["dose_mg"] or 0
                current_freq_hours = _freq_to_hours(e.get("frequency"))
                break
            elif e["event_type"] == "STOP":
                # Compound is stopped — use last active dose for reference
                break

    # Fallback: infer from the last actual dose
    if current_dose <= 0 and doses:
        current_dose = doses[-1][1]
    if current_freq_hours <= 0:
        # Try to infer frequency from spacing of last few doses
        if len(doses) >= 2:
            gaps = []
            for i in range(max(0, len(doses) - 5), len(doses) - 1):
                gap = (doses[i + 1][0] - doses[i][0]).total_seconds() / 3600
                if gap > 0:
                    gaps.append(gap)
            if gaps:
                current_freq_hours = sum(gaps) / len(gaps)

    if current_dose <= 0 or current_freq_hours <= 0:
        return 1.0

    # Simulate steady state: stack doses at current_dose/current_freq
    # for 10 half-lives, then measure peak at the last dose time
    n_doses = max(1, int((10 * half_life_hours) / current_freq_hours))
    peak = 0.0
    for i in range(n_doses):
        hours_ago = i * current_freq_hours
        remaining = current_dose * (0.5 ** (hours_ago / half_life_hours))
        if remaining > current_dose * 0.001:
            peak += remaining

    return peak if peak > 0 else 1.0
