"""Calendar system — temporal index over all data tables.

For any date, composites: compound events + drug levels + wearable observations +
lab results + findings + scheduled events. The calendar is a view layer, not a
separate data store.
"""
import sqlite3
import json
from datetime import date, timedelta


def get_calendar_day(conn: sqlite3.Connection, user_id: str, target_date: str) -> dict:
    """Everything that happened on a specific date for an athlete."""

    # Active compounds with levels
    compounds = []
    for c in conn.execute("""
        SELECT dl.compound_id, COALESCE(cd.canonical_name, dl.compound_id) as name,
               COALESCE(cd.compound_class, 'unknown') as compound_class,
               dl.estimated_level, dl.dose_active_mg, dl.at_steady_state, dl.days_since_start
        FROM drug_level dl
        LEFT JOIN compound_definition cd ON dl.compound_id = cd.id
        WHERE dl.user_id = ? AND dl.observation_date = ? AND dl.estimated_level > 0.01
    """, (user_id, target_date)).fetchall():
        # Get current dose info from latest compound_event
        dose_info = conn.execute("""
            SELECT dose_mg, frequency, route FROM compound_event
            WHERE user_id = ? AND compound_id = ? AND event_type IN ('START', 'DOSE_CHANGE') AND date(timestamp) <= ?
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id, c["compound_id"], target_date)).fetchone()
        compounds.append({
            "compound_id": c["compound_id"],
            "name": c["name"],
            "compound_class": c["compound_class"],
            "estimated_level": round(c["estimated_level"], 3),
            "dose_active_mg": c["dose_active_mg"],
            "at_steady_state": bool(c["at_steady_state"]),
            "days_since_start": c["days_since_start"],
            "dose_mg": dose_info["dose_mg"] if dose_info else None,
            "frequency": dose_info["frequency"] if dose_info else None,
            "route": dose_info["route"] if dose_info else None,
        })

    # Wearables
    wearables = [dict(w) for w in conn.execute(
        "SELECT metric, value_mean, unit, source, methodology FROM wearable_observation WHERE user_id = ? AND observation_date = ?",
        (user_id, target_date)
    ).fetchall()]

    # Labs
    labs = []
    for l in conn.execute("""
        SELECT mo.metric_loinc, COALESCE(md.canonical_name, mo.metric_loinc) as metric_name,
               mo.value_canonical, mo.unit_canonical, mo.flag,
               mo.reference_low, mo.reference_high, COALESCE(md.category, 'unknown') as category
        FROM metric_observation mo
        LEFT JOIN metric_definition md ON mo.metric_loinc = md.loinc_code
        WHERE mo.user_id = ? AND mo.observation_date = ?
    """, (user_id, target_date)).fetchall():
        labs.append(dict(l))

    # Findings active on this date
    findings = []
    for f in conn.execute("""
        SELECT id, detector_id, severity, summary, detail
        FROM finding WHERE user_id = ? AND status = 'active'
        AND (time_window_start IS NULL OR time_window_start <= ?)
        AND (time_window_end IS NULL OR time_window_end >= ?)
    """, (user_id, target_date, target_date)).fetchall():
        detail = {}
        try:
            detail = json.loads(f["detail"]) if f["detail"] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        findings.append({
            "id": f["id"],
            "severity": f["severity"],
            "headline": detail.get("headline", f["summary"][:80]),
            "theme": detail.get("theme", f["detector_id"]),
        })

    # Scheduled events
    scheduled = [dict(s) for s in conn.execute(
        "SELECT id, event_type, description, status, compound_id FROM scheduled_event WHERE user_id = ? AND scheduled_date = ?",
        (user_id, target_date)
    ).fetchall()]

    # Phase
    phase_row = conn.execute(
        "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND date(started_at) <= ? AND (ended_at IS NULL OR date(ended_at) >= ?) ORDER BY started_at DESC LIMIT 1",
        (user_id, target_date, target_date)
    ).fetchone()

    day_in_phase = 0
    if phase_row and phase_row["started_at"]:
        from datetime import datetime
        try:
            start = datetime.fromisoformat(phase_row["started_at"]).date()
            target = date.fromisoformat(target_date)
            day_in_phase = (target - start).days
        except (ValueError, TypeError):
            pass

    return {
        "date": target_date,
        "phase": phase_row["phase"] if phase_row else "unknown",
        "day_in_phase": day_in_phase,
        "compounds": compounds,
        "wearables": wearables,
        "labs": labs,
        "findings": findings,
        "scheduled": scheduled,
    }


def get_calendar_range(conn: sqlite3.Connection, user_id: str, start: str, end: str) -> dict:
    """Which days have data in a date range."""
    wearable_days = [r[0] for r in conn.execute(
        "SELECT DISTINCT observation_date FROM wearable_observation WHERE user_id = ? AND observation_date BETWEEN ? AND ?",
        (user_id, start, end)).fetchall()]
    lab_days = [r[0] for r in conn.execute(
        "SELECT DISTINCT observation_date FROM metric_observation WHERE user_id = ? AND observation_date BETWEEN ? AND ?",
        (user_id, start, end)).fetchall()]
    finding_days = [r[0] for r in conn.execute(
        "SELECT DISTINCT date(detected_at) FROM finding WHERE user_id = ? AND date(detected_at) BETWEEN ? AND ?",
        (user_id, start, end)).fetchall()]
    scheduled_days = [r[0] for r in conn.execute(
        "SELECT DISTINCT scheduled_date FROM scheduled_event WHERE user_id = ? AND scheduled_date BETWEEN ? AND ?",
        (user_id, start, end)).fetchall()]

    return {
        "start": start, "end": end,
        "wearable_days": wearable_days, "lab_days": lab_days,
        "finding_days": finding_days, "scheduled_days": scheduled_days,
    }


def get_upcoming_schedule(conn: sqlite3.Connection, user_id: str, days: int = 14) -> list[dict]:
    """Upcoming scheduled events."""
    end = (date.today() + timedelta(days=days)).isoformat()
    return [dict(e) for e in conn.execute(
        "SELECT id, event_type, scheduled_date, description, status, compound_id FROM scheduled_event WHERE user_id = ? AND scheduled_date BETWEEN ? AND ? AND status = 'upcoming' ORDER BY scheduled_date",
        (user_id, date.today().isoformat(), end)
    ).fetchall()]
