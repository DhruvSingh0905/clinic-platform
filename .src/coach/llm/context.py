"""Tier 1 context builders — compact briefings injected per mode.

Three variants:
- build_briefing: Full briefing (findings + compounds + snapshot) — for diagnostics/testing
- build_finding_briefing: One specific finding + compounds + snapshot — for finding threads
- build_minimal_briefing: Compounds + snapshot only (no findings) — for free chat
"""

from __future__ import annotations

import json
import sqlite3


def _build_compound_section(conn: sqlite3.Connection, user_id: str) -> str:
    """Active compounds with drug levels."""
    compounds = conn.execute("""
        SELECT cd.canonical_name, cd.compound_class, dl.estimated_level,
               dl.days_since_start, dl.at_steady_state,
               ce.dose_mg, ce.frequency
        FROM drug_level dl
        JOIN compound_definition cd ON dl.compound_id = cd.id
        LEFT JOIN (
            SELECT compound_id, dose_mg, frequency,
                   ROW_NUMBER() OVER (PARTITION BY compound_id ORDER BY timestamp DESC) as rn
            FROM compound_event WHERE user_id = ? AND event_type IN ('START', 'DOSE_CHANGE')
        ) ce ON dl.compound_id = ce.compound_id AND ce.rn = 1
        WHERE dl.user_id = ?
          AND dl.observation_date = (SELECT MAX(observation_date) FROM drug_level WHERE user_id = ?)
          AND dl.estimated_level > 0.001
        ORDER BY dl.estimated_level DESC
    """, (user_id, user_id, user_id)).fetchall()

    if not compounds:
        return "ACTIVE COMPOUNDS: None logged"

    lines = ["ACTIVE COMPOUNDS:"]
    for c in compounds:
        ss = "steady state" if c["at_steady_state"] else "ramping"
        dose = f"{c['dose_mg']}mg {c['frequency']}" if c["dose_mg"] else "dose unknown"
        lines.append(f"  {c['canonical_name']} ({c['compound_class']}) — {dose}, day {c['days_since_start']}, {ss}, level {c['estimated_level']:.0%}")
    return "\n".join(lines)


def _build_snapshot_section(conn: sqlite3.Connection, user_id: str) -> str:
    """Data availability snapshot."""
    lab_count = conn.execute(
        "SELECT COUNT(DISTINCT observation_date) FROM metric_observation WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]

    lab_dates = conn.execute(
        "SELECT MIN(observation_date), MAX(observation_date) FROM metric_observation WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    wearable_days = conn.execute(
        "SELECT COUNT(DISTINCT observation_date) FROM wearable_observation WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]

    wearable_range = conn.execute(
        "SELECT MIN(observation_date), MAX(observation_date) FROM wearable_observation WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    event_count = conn.execute(
        "SELECT COUNT(*) FROM compound_event WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0]

    lines = ["DATA AVAILABLE:"]
    if lab_count:
        lines.append(f"  Lab panels: {lab_count} draws ({lab_dates[0]} to {lab_dates[1]})")
    else:
        lines.append("  Lab panels: none")
    if wearable_days:
        lines.append(f"  Wearable data: {wearable_days} days ({wearable_range[0]} to {wearable_range[1]})")
    else:
        lines.append("  Wearable data: none")
    lines.append(f"  Compound events: {event_count}")
    return "\n".join(lines)


def _build_phase_section(conn: sqlite3.Connection, user_id: str) -> str:
    """Current cycle phase."""
    from datetime import date
    row = conn.execute(
        "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()

    if row:
        days = (date.today() - date.fromisoformat(row["started_at"][:10])).days
        return f"CURRENT PHASE: {row['phase'].upper()} (since {row['started_at'][:10]}, day {days})"
    return "CURRENT PHASE: Unknown (not set — ask the user what phase they're in)"


def build_briefing(conn: sqlite3.Connection, user_id: str = "default") -> str:
    """Full briefing: all findings + compounds + snapshot. For testing/diagnostics."""
    sections = []

    # Findings
    findings = conn.execute("""
        SELECT id, severity, summary, detail
        FROM finding WHERE user_id = ? AND status IN ('active', 'viewed')
        ORDER BY CASE severity WHEN 'concerning' THEN 0 WHEN 'notable' THEN 1 ELSE 2 END
    """, (user_id,)).fetchall()

    if findings:
        lines = ["ACTIVE FINDINGS:"]
        for f in findings:
            lines.append(f"  [{f['severity'].upper()}] {f['summary']} (finding #{f['id']})")
            if f["detail"]:
                for s in json.loads(f["detail"]).get("signals", [])[:3]:
                    lines.append(f"    - {s['description']}")
        sections.append("\n".join(lines))
    else:
        sections.append("ACTIVE FINDINGS: None")

    # Include recently dismissed findings with reasons (last 30 days)
    dismissed = conn.execute("""
        SELECT summary, dismiss_reason, detected_at
        FROM finding WHERE user_id = ? AND status = 'dismissed' AND dismiss_reason IS NOT NULL
          AND detected_at >= datetime('now', '-30 days')
        ORDER BY detected_at DESC LIMIT 5
    """, (user_id,)).fetchall()
    if dismissed:
        reason_labels = {"alcohol": "alcohol", "recreational_drug": "recreational drug use",
                         "training": "heavy training", "other": "non-compound cause"}
        lines = ["RECENTLY DISMISSED (user-attributed):"]
        for d in dismissed:
            label = reason_labels.get(d["dismiss_reason"], d["dismiss_reason"])
            lines.append(f"  {d['summary']} — attributed to {label} ({d['detected_at'][:10]})")
        sections.append("\n".join(lines))

    sections.append(_build_phase_section(conn, user_id))
    sections.append(_build_compound_section(conn, user_id))
    sections.append(_build_snapshot_section(conn, user_id))
    return "\n\n".join(sections)


def build_finding_briefing(conn: sqlite3.Connection, finding_id: int, user_id: str = "default") -> str:
    """Finding thread briefing: one specific finding + compounds + snapshot."""
    sections = []

    finding = conn.execute("""
        SELECT id, detector_id, severity, summary, detail
        FROM finding WHERE id = ?
    """, (finding_id,)).fetchone()

    if finding:
        lines = [f"FINDING UNDER INVESTIGATION (#{finding['id']}):"]
        lines.append(f"  Severity: {finding['severity'].upper()}")
        lines.append(f"  Theme: {finding['detector_id']}")
        lines.append(f"  Summary: {finding['summary']}")

        if finding["detail"]:
            detail = json.loads(finding["detail"])
            if detail.get("signals"):
                lines.append("  Signals:")
                for s in detail["signals"]:
                    current = f" (current: {s.get('current')})" if s.get("current") is not None else ""
                    lines.append(f"    - {s['description']}{current}")
            if detail.get("drug_context"):
                lines.append("  Drug context at detection:")
                for d in detail["drug_context"]:
                    lines.append(f"    - {d['name']} ({d['class']}) — day {d['days_on']}, level {d['level']:.0%}")
            if detail.get("recommendations"):
                lines.append("  Recommendations:")
                for r in detail["recommendations"]:
                    lines.append(f"    - {r}")

        sections.append("\n".join(lines))
    else:
        sections.append(f"Finding #{finding_id} not found.")

    sections.append(_build_phase_section(conn, user_id))
    sections.append(_build_compound_section(conn, user_id))
    sections.append(_build_snapshot_section(conn, user_id))
    return "\n\n".join(sections)


def build_minimal_briefing(conn: sqlite3.Connection, user_id: str = "default") -> str:
    """Free chat briefing: phase + compounds + snapshot only. NO findings injected."""
    sections = [
        _build_phase_section(conn, user_id),
        _build_compound_section(conn, user_id),
        _build_snapshot_section(conn, user_id),
    ]
    return "\n\n".join(sections)
