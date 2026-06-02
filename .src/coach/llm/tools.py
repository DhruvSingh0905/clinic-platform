"""LLM tool functions — data retrieval layer.

Each tool returns pre-computed summaries, not raw database rows.
The LLM calls these to investigate findings or answer questions.
Tools accept human-readable names (not LOINC codes or compound IDs).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

import anthropic

from coach.config import ANTHROPIC_API_KEY, CDE_MODEL
from coach.extraction.loinc import map_test_name
from coach.compound_db import lookup_compound as _py_lookup_compound


# =============================================================================
# BLOODWORK TOOLS
# =============================================================================

def _resolve_metric_query(conn: sqlite3.Connection, metric_name: str, user_id: str) -> list:
    """Resolve a metric name to observations, trying canonical name then alias index."""
    # Try direct LIKE match on canonical name first
    rows = conn.execute("""
        SELECT mo.observation_date, mo.value_canonical, mo.unit_canonical,
               mo.flag, mo.reference_low, mo.reference_high, md.canonical_name
        FROM metric_observation mo
        JOIN metric_definition md ON mo.metric_loinc = md.loinc_code
        WHERE mo.user_id = ? AND md.canonical_name LIKE ? AND mo.value_canonical IS NOT NULL
        ORDER BY mo.observation_date
    """, (user_id, f"%{metric_name}%")).fetchall()

    if rows:
        return rows

    # Fall back to LOINC alias index lookup
    test_def = map_test_name(metric_name)
    if test_def:
        rows = conn.execute("""
            SELECT mo.observation_date, mo.value_canonical, mo.unit_canonical,
                   mo.flag, mo.reference_low, mo.reference_high, md.canonical_name
            FROM metric_observation mo
            JOIN metric_definition md ON mo.metric_loinc = md.loinc_code
            WHERE mo.user_id = ? AND md.loinc_code = ? AND mo.value_canonical IS NOT NULL
            ORDER BY mo.observation_date
        """, (user_id, test_def.loinc_code)).fetchall()

    return rows


def get_metric_summary(conn: sqlite3.Connection, metric_name: str, user_id: str = "default") -> str:
    """Get a summary of a bloodwork metric: latest, baseline, trend, change."""
    rows = _resolve_metric_query(conn, metric_name, user_id)

    if not rows:
        return f"No data found for '{metric_name}'."

    name = rows[0]["canonical_name"]
    unit = rows[0]["unit_canonical"]
    latest = rows[-1]
    baseline = rows[0]

    result = f"**{name}**\n"
    result += f"Latest: {latest['value_canonical']} {unit} ({latest['observation_date']})"
    if latest["flag"] and latest["flag"] != "normal":
        result += f" [{latest['flag'].upper()}]"
    if latest["reference_low"] is not None and latest["reference_high"] is not None:
        result += f" (ref: {latest['reference_low']}-{latest['reference_high']})"
    result += "\n"

    if len(rows) > 1:
        change = latest["value_canonical"] - baseline["value_canonical"]
        pct = (change / baseline["value_canonical"] * 100) if baseline["value_canonical"] else 0
        direction = "rising" if change > 0 else "falling" if change < 0 else "stable"
        result += f"Baseline: {baseline['value_canonical']} {unit} ({baseline['observation_date']})\n"
        result += f"Change: {change:+.1f} {unit} ({pct:+.1f}%), trend: {direction}\n"

    values = [r["value_canonical"] for r in rows]
    result += f"Range: {min(values)}-{max(values)} {unit} over {len(rows)} draws"
    return result


def get_metric_history(conn: sqlite3.Connection, metric_name: str, user_id: str = "default") -> str:
    """Get the full timeseries for a bloodwork metric."""
    rows = _resolve_metric_query(conn, metric_name, user_id)

    if not rows:
        return f"No data found for '{metric_name}'."

    name = rows[0]["canonical_name"]
    lines = [f"**{name} History** ({len(rows)} draws)"]
    for r in rows:
        flag = f" [{r['flag'].upper()}]" if r["flag"] and r["flag"] != "normal" else ""
        ref = f" (ref: {r['reference_low']}-{r['reference_high']})" if r["reference_low"] is not None else ""
        lines.append(f"  {r['observation_date']}: {r['value_canonical']} {r['unit_canonical']}{flag}{ref}")
    return "\n".join(lines)


def get_panel_snapshot(conn: sqlite3.Connection, draw_date: str, user_id: str = "default") -> str:
    """Get all metrics from a specific lab draw."""
    rows = conn.execute("""
        SELECT md.canonical_name, mo.value_canonical, mo.unit_canonical,
               mo.flag, mo.reference_low, mo.reference_high, md.category
        FROM metric_observation mo
        JOIN metric_definition md ON mo.metric_loinc = md.loinc_code
        WHERE mo.user_id = ? AND mo.observation_date = ? AND mo.value_canonical IS NOT NULL
        ORDER BY md.category, md.canonical_name
    """, (user_id, draw_date)).fetchall()

    if not rows:
        return f"No lab results found for {draw_date}."

    lines = [f"**Lab Panel — {draw_date}** ({len(rows)} tests)"]
    current_cat = ""
    for r in rows:
        if r["category"] != current_cat:
            current_cat = r["category"]
            lines.append(f"\n  [{current_cat.upper()}]")
        flag = f" [{r['flag'].upper()}]" if r["flag"] and r["flag"] != "normal" else ""
        ref = f" (ref: {r['reference_low']}-{r['reference_high']})" if r["reference_low"] is not None else ""
        lines.append(f"  {r['canonical_name']}: {r['value_canonical']} {r['unit_canonical']}{flag}{ref}")
    return "\n".join(lines)


def compare_panels(conn: sqlite3.Connection, date1: str, date2: str, user_id: str = "default") -> str:
    """Compare two lab draws side by side."""
    panel1 = {}
    for r in conn.execute("""
        SELECT md.canonical_name, mo.value_canonical, mo.unit_canonical, mo.flag
        FROM metric_observation mo JOIN metric_definition md ON mo.metric_loinc = md.loinc_code
        WHERE mo.user_id = ? AND mo.observation_date = ? AND mo.value_canonical IS NOT NULL
    """, (user_id, date1)).fetchall():
        panel1[r["canonical_name"]] = r

    panel2 = {}
    for r in conn.execute("""
        SELECT md.canonical_name, mo.value_canonical, mo.unit_canonical, mo.flag
        FROM metric_observation mo JOIN metric_definition md ON mo.metric_loinc = md.loinc_code
        WHERE mo.user_id = ? AND mo.observation_date = ? AND mo.value_canonical IS NOT NULL
    """, (user_id, date2)).fetchall():
        panel2[r["canonical_name"]] = r

    if not panel1 and not panel2:
        return f"No data found for either {date1} or {date2}."

    all_metrics = sorted(set(list(panel1.keys()) + list(panel2.keys())))
    lines = [f"**Panel Comparison: {date1} vs {date2}**"]

    for m in all_metrics:
        r1 = panel1.get(m)
        r2 = panel2.get(m)
        if r1 and r2:
            v1, v2 = r1["value_canonical"], r2["value_canonical"]
            change = v2 - v1
            unit = r1["unit_canonical"]
            direction = "↑" if change > 0 else "↓" if change < 0 else "→"
            lines.append(f"  {m}: {v1} → {v2} {unit} ({change:+.1f}) {direction}")
        elif r1:
            lines.append(f"  {m}: {r1['value_canonical']} → (not tested)")
        else:
            lines.append(f"  {m}: (not tested) → {r2['value_canonical']}")

    return "\n".join(lines)


# =============================================================================
# WEARABLE TOOLS
# =============================================================================

METRIC_ALIASES = {
    "weight": ["weight", "weight_kg"],
    "weight_kg": ["weight", "weight_kg"],
    "hrv_sdnn": ["hrv_sdnn", "hrv_rmssd", "hrv"],
    "hrv_rmssd": ["hrv_sdnn", "hrv_rmssd", "hrv"],
    "hrv": ["hrv_sdnn", "hrv_rmssd", "hrv"],
    "recovery_score": ["recovery_score", "recovery"],
    "recovery": ["recovery_score", "recovery"],
}

def get_wearable_trend(
    conn: sqlite3.Connection,
    metric: str,
    window_days: int = 90,
    user_id: str = "default",
) -> str:
    """Get wearable trend with rolling averages. Returns summary, not raw rows."""
    cutoff = (date.today() - timedelta(days=window_days)).isoformat()
    # Try exact match first, then aliases
    aliases = METRIC_ALIASES.get(metric, [metric])
    rows = []
    for alias in aliases:
        rows = conn.execute("""
            SELECT observation_date, value_mean, unit
            FROM wearable_observation
            WHERE user_id = ? AND metric = ? AND observation_date >= ?
            ORDER BY observation_date
        """, (user_id, alias, cutoff)).fetchall()
        if rows:
            break

    if not rows:
        return f"No wearable data for '{metric}' in last {window_days} days."

    values = [r["value_mean"] for r in rows]
    unit = rows[0]["unit"]
    n = len(values)

    # Baseline: first 7 days avg
    baseline_vals = values[:min(7, n)]
    baseline = sum(baseline_vals) / len(baseline_vals)

    # Current: last 7 days avg
    current_vals = values[-min(7, n):]
    current = sum(current_vals) / len(current_vals)

    # 3-day rolling (latest)
    rolling_3 = sum(values[-min(3, n):]) / min(3, n)

    change = current - baseline
    pct = (change / baseline * 100) if baseline else 0
    direction = "rising" if change > 2 else "falling" if change < -2 else "stable"

    metric_label = metric.replace("_", " ").title()
    result = f"**{metric_label} Trend** ({n} days of data)\n"
    result += f"Baseline (first 7d avg): {baseline:.1f} {unit}\n"
    result += f"Current (last 7d avg): {current:.1f} {unit}\n"
    result += f"3-day rolling avg: {rolling_3:.1f} {unit}\n"
    result += f"Change from baseline: {change:+.1f} {unit} ({pct:+.1f}%), trend: {direction}\n"
    result += f"Range: {min(values):.1f}-{max(values):.1f} {unit}"
    return result


def get_bp_summary(
    conn: sqlite3.Connection,
    window_days: int = 90,
    user_id: str = "default",
) -> str:
    """Get BP summary with morning/evening breakdown and classification."""
    cutoff = (date.today() - timedelta(days=window_days)).isoformat()

    # From wearable_observation (Apple Health BP)
    sys_rows = conn.execute("""
        SELECT observation_date, value_mean FROM wearable_observation
        WHERE user_id = ? AND metric = 'bp_systolic' AND observation_date >= ?
        ORDER BY observation_date
    """, (user_id, cutoff)).fetchall()

    dia_rows = conn.execute("""
        SELECT observation_date, value_mean FROM wearable_observation
        WHERE user_id = ? AND metric = 'bp_diastolic' AND observation_date >= ?
        ORDER BY observation_date
    """, (user_id, cutoff)).fetchall()

    # Also from manual bp_reading table
    manual = conn.execute("""
        SELECT timestamp, systolic, diastolic, time_of_day, classification
        FROM bp_reading WHERE user_id = ? AND timestamp >= ?
        ORDER BY timestamp
    """, (user_id, cutoff)).fetchall()

    if not sys_rows and not manual:
        return f"No BP data in last {window_days} days."

    lines = [f"**Blood Pressure Summary** (last {window_days} days)"]

    if sys_rows:
        sys_vals = [r["value_mean"] for r in sys_rows]
        dia_vals = [r["value_mean"] for r in dia_rows]
        lines.append(f"Wearable readings: {len(sys_rows)} days")
        lines.append(f"  Systolic: avg {sum(sys_vals)/len(sys_vals):.0f}, range {min(sys_vals):.0f}-{max(sys_vals):.0f} mmHg")
        if dia_vals:
            lines.append(f"  Diastolic: avg {sum(dia_vals)/len(dia_vals):.0f}, range {min(dia_vals):.0f}-{max(dia_vals):.0f} mmHg")

        # Trend
        if len(sys_vals) >= 4:
            first_half = sum(sys_vals[:len(sys_vals)//2]) / (len(sys_vals)//2)
            second_half = sum(sys_vals[len(sys_vals)//2:]) / (len(sys_vals) - len(sys_vals)//2)
            bp_change = second_half - first_half
            direction = "rising" if bp_change > 3 else "falling" if bp_change < -3 else "stable"
            lines.append(f"  Systolic trend: {direction} ({bp_change:+.0f} mmHg)")

    if manual:
        lines.append(f"Manual readings: {len(manual)}")
        for r in manual:
            tod = f" ({r['time_of_day']})" if r["time_of_day"] else ""
            lines.append(f"  {r['timestamp'][:10]}: {r['systolic']}/{r['diastolic']} mmHg{tod} — {r['classification']}")

    return "\n".join(lines)


# =============================================================================
# DRUG TIMELINE TOOLS
# =============================================================================

def _resolve_compound(conn: sqlite3.Connection, compound_name: str):
    """Resolve compound name/alias to DB row. Python alias lookup first (precise), then SQL LIKE (fuzzy)."""
    # Try Python alias lookup first — this handles brand names, abbreviations, and common shorthand
    py_match = _py_lookup_compound(compound_name)
    if py_match:
        row = conn.execute(
            "SELECT id, canonical_name, compound_class, mechanism_summary, notes FROM compound_definition WHERE id = ?",
            (py_match.id,),
        ).fetchone()
        if row:
            return row

    # Fall back to SQL LIKE on canonical_name and id
    row = conn.execute("""
        SELECT id, canonical_name, compound_class, mechanism_summary, notes
        FROM compound_definition
        WHERE canonical_name LIKE ? OR id LIKE ?
        LIMIT 1
    """, (f"%{compound_name}%", f"%{compound_name.lower().replace(' ', '_')}%")).fetchone()

    return row


def get_compound_status(conn: sqlite3.Connection, compound_name: str, user_id: str = "default") -> str:
    """Get current status of a compound. Accepts name or alias."""
    row = _resolve_compound(conn, compound_name)

    if not row:
        return f"Compound '{compound_name}' not found in database."

    cid = row["id"]
    name = row["canonical_name"]
    cls = row["compound_class"]

    # Get latest drug level
    dl = conn.execute("""
        SELECT estimated_level, days_since_start, at_steady_state, observation_date
        FROM drug_level
        WHERE user_id = ? AND compound_id = ?
        ORDER BY observation_date DESC LIMIT 1
    """, (user_id, cid)).fetchone()

    # Get latest event
    ev = conn.execute("""
        SELECT event_type, timestamp, dose_mg, frequency, route, source_quality
        FROM compound_event
        WHERE user_id = ? AND compound_id = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (user_id, cid)).fetchone()

    result = f"**{name}** ({cls})\n"

    if ev:
        result += f"Last event: {ev['event_type']} on {ev['timestamp'][:10]}"
        if ev["dose_mg"]:
            result += f" — {ev['dose_mg']}mg {ev['frequency'] or ''} {ev['route'] or ''}"
        if ev["source_quality"] and ev["source_quality"] != "unknown":
            result += f" (source: {ev['source_quality']})"
        result += "\n"

    if dl:
        ss = "at steady state" if dl["at_steady_state"] else "still ramping"
        result += f"Day {dl['days_since_start']}, {ss}\n"
        result += f"Estimated system level: {dl['estimated_level']:.0%} of steady-state peak\n"
    else:
        result += "No drug level data (compound may not be active or no events logged)\n"

    return result


def get_compounds_on_date(conn: sqlite3.Connection, target_date: str, user_id: str = "default") -> str:
    """Get all active compounds with levels on a specific date."""
    rows = conn.execute("""
        SELECT cd.canonical_name, cd.compound_class, dl.estimated_level,
               dl.days_since_start, dl.at_steady_state
        FROM drug_level dl
        JOIN compound_definition cd ON dl.compound_id = cd.id
        WHERE dl.user_id = ? AND dl.observation_date = ? AND dl.estimated_level > 0.001
        ORDER BY dl.estimated_level DESC
    """, (user_id, target_date)).fetchall()

    if not rows:
        return f"No active compounds found on {target_date}."

    lines = [f"**Active Compounds on {target_date}**"]
    for r in rows:
        ss = "steady" if r["at_steady_state"] else "ramping"
        lines.append(f"  {r['canonical_name']} ({r['compound_class']}) — {r['estimated_level']:.0%} level, day {r['days_since_start']}, {ss}")
    return "\n".join(lines)


def get_compound_mechanism(conn: sqlite3.Connection, compound_name: str) -> str:
    """Get mechanism summary and monitoring markers for a compound."""
    # Need full row including monitoring_markers_json
    base = _resolve_compound(conn, compound_name)
    if not base:
        return f"Compound '{compound_name}' not found."

    # Re-fetch with all columns
    row = conn.execute(
        "SELECT * FROM compound_definition WHERE id = ?",
        (base["id"],),
    ).fetchone()

    if not row:
        return f"Compound '{compound_name}' not found."

    result = f"**{row['canonical_name']}** ({row['compound_class']})\n"
    if row["mechanism_summary"]:
        result += f"Mechanism: {row['mechanism_summary']}\n"

    if row["monitoring_markers_json"]:
        markers = json.loads(row["monitoring_markers_json"])
        if markers:
            # Resolve LOINC codes to names
            names = []
            for loinc in markers:
                md = conn.execute(
                    "SELECT canonical_name FROM metric_definition WHERE loinc_code = ?",
                    (loinc,),
                ).fetchone()
                names.append(md["canonical_name"] if md else loinc)
            result += f"Monitor: {', '.join(names)}\n"

    if row["notes"]:
        result += f"Notes: {row['notes']}\n"

    return result


# =============================================================================
# FINDINGS TOOLS
# =============================================================================

def get_finding_detail(conn: sqlite3.Connection, finding_id: int) -> str:
    """Get full detail of a specific finding."""
    row = conn.execute("""
        SELECT detector_id, severity, summary, detail, detected_at,
               time_window_start, time_window_end, confidence
        FROM finding WHERE id = ?
    """, (finding_id,)).fetchone()

    if not row:
        return f"Finding #{finding_id} not found."

    result = f"**Finding #{finding_id}** [{row['severity'].upper()}]\n"
    result += f"{row['summary']}\n"
    result += f"Detected: {row['detected_at']}\n"

    if row["detail"]:
        detail = json.loads(row["detail"])
        if detail.get("signals"):
            result += "\nSignals:\n"
            for s in detail["signals"]:
                result += f"  - {s['metric']}: {s['description']}\n"
        if detail.get("drug_context"):
            result += "\nDrug context:\n"
            for d in detail["drug_context"]:
                result += f"  - {d['name']} ({d['class']}) — day {d['days_on']}, level {d['level']:.0%}\n"
        if detail.get("recommendations"):
            result += "\nRecommendations:\n"
            for r in detail["recommendations"]:
                result += f"  - {r}\n"

    return result


def get_finding_history(conn: sqlite3.Connection, theme: str, days: int = 90, user_id: str = "default") -> str:
    """Get finding history for a theme."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT id, severity, summary, detected_at, status
        FROM finding
        WHERE user_id = ? AND detector_id LIKE ? AND detected_at >= ?
        ORDER BY detected_at DESC
    """, (user_id, f"%{theme}%", cutoff)).fetchall()

    if not rows:
        return f"No findings for theme '{theme}' in last {days} days."

    lines = [f"**Finding History: {theme}** ({len(rows)} findings)"]
    for r in rows:
        lines.append(f"  [{r['severity'].upper()}] {r['detected_at'][:10]}: {r['summary']} ({r['status']})")
    return "\n".join(lines)


# =============================================================================
# TOOL DEFINITIONS for Claude API
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "get_metric_summary",
        "description": "Get a summary of a bloodwork metric including latest value, baseline, trend direction, and change. Use for quick overview of any lab test.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string", "description": "Name of the metric (e.g., 'Hematocrit', 'ALT', 'Estradiol', 'HDL Cholesterol')"}
            },
            "required": ["metric_name"]
        }
    },
    {
        "name": "get_metric_history",
        "description": "Get the full timeseries of a bloodwork metric across all lab draws. Use when you need to see all values over time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string", "description": "Name of the metric"}
            },
            "required": ["metric_name"]
        }
    },
    {
        "name": "get_panel_snapshot",
        "description": "Get all lab results from a specific blood draw date. Use to see the full picture from one lab visit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "draw_date": {"type": "string", "description": "Date of the lab draw (YYYY-MM-DD)"}
            },
            "required": ["draw_date"]
        }
    },
    {
        "name": "compare_panels",
        "description": "Compare lab results between two draw dates side by side. Shows what changed, what's new, what normalized.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date1": {"type": "string", "description": "First draw date (YYYY-MM-DD)"},
                "date2": {"type": "string", "description": "Second draw date (YYYY-MM-DD)"}
            },
            "required": ["date1", "date2"]
        }
    },
    {
        "name": "get_wearable_trend",
        "description": "Get wearable data trend with rolling averages (3-day, 7-day), baseline comparison, and direction. Use for heart rate, HRV, weight, or BP trends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "enum": ["resting_hr", "hrv_sdnn", "hrv_rmssd", "weight", "weight_kg", "bp_systolic", "bp_diastolic", "heart_rate", "recovery_score"],
                           "description": "Wearable metric to query"},
                "window_days": {"type": "integer", "description": "Number of days to look back (default 90)", "default": 90}
            },
            "required": ["metric"]
        }
    },
    {
        "name": "get_bp_summary",
        "description": "Get blood pressure summary with morning/evening breakdown, trends, and AHA classification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "window_days": {"type": "integer", "description": "Days to look back (default 90)", "default": 90}
            }
        }
    },
    {
        "name": "get_compound_status",
        "description": "Get current status of a compound: active/stopped, days on, dose, current system level, steady state. Accepts common names (e.g., 'Test Cyp', 'Anavar', 'Telmisartan').",
        "input_schema": {
            "type": "object",
            "properties": {
                "compound_name": {"type": "string", "description": "Compound name or alias"}
            },
            "required": ["compound_name"]
        }
    },
    {
        "name": "get_compounds_on_date",
        "description": "Get all active compounds with estimated system levels on a specific date. Use to see what was in the system when a blood draw happened.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date to query (YYYY-MM-DD)"}
            },
            "required": ["date"]
        }
    },
    {
        "name": "get_compound_mechanism",
        "description": "Get mechanism of action, monitoring markers, and clinical notes for a compound. Use when explaining WHY a compound affects a specific metric.",
        "input_schema": {
            "type": "object",
            "properties": {
                "compound_name": {"type": "string", "description": "Compound name or alias"}
            },
            "required": ["compound_name"]
        }
    },
    {
        "name": "get_finding_detail",
        "description": "Get full detail of a specific detector finding including all signals, drug context, and recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "finding_id": {"type": "integer", "description": "Finding ID number"}
            },
            "required": ["finding_id"]
        }
    },
    {
        "name": "get_finding_history",
        "description": "Get historical findings for a health theme to see progression over time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "theme": {"type": "string", "description": "Theme name (e.g., 'cardiovascular', 'hepatic', 'hormonal', 'metabolic', 'renal')"},
                "days": {"type": "integer", "description": "Days to look back (default 90)", "default": 90}
            },
            "required": ["theme"]
        }
    },
    {
        "name": "search_drug_interaction",
        "description": "Search the web for drug interaction information, mechanism of action details, or pharmacological research. Use when you need to verify or look up specific compound interactions, side effects, or mechanisms that you're not confident about. Do NOT use search results to make clinical recommendations — only to explain mechanisms and flag potential interactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query about drug interactions, mechanisms, or pharmacology (e.g., 'telmisartan oxandrolone interaction', 'trenbolone prolactin mechanism')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_hr_daily_stats",
        "description": "Get detailed heart rate statistics for a specific day — resting HR, active HR (min/mean/max), HRV with methodology, recovery score. More detailed than the wearable trend view.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date (YYYY-MM-DD)"}
            },
            "required": ["date"]
        }
    },
    {
        "name": "get_nutrition_summary",
        "description": "Get calorie and macro data from food logging apps (MyFitnessPal, MacroFactor, etc via Apple Health). Self-reported — treat as approximate context for weight changes, not precise measurement. Useful for: 'is weight gain from food surplus or water retention?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                "window_days": {"type": "integer", "description": "Days of context (default 7)", "default": 7}
            },
            "required": ["date"]
        }
    },
    {
        "name": "get_training_context",
        "description": "Get exercise/training context for a date or recent window. IMPORTANT: Use this before attributing HR/HRV changes to compounds — training load is a major confound. Exercise data is approximate and varies by device.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date to check (YYYY-MM-DD)"},
                "window_days": {"type": "integer", "description": "Days of context (default 7)", "default": 7}
            },
            "required": ["date"]
        }
    },
]


def get_hr_daily_stats(conn: sqlite3.Connection, target_date: str, user_id: str = "default") -> str:
    """Get detailed cardiac stats for a specific day — resting HR, active HR, HRV with methodology, recovery score, respiratory rate."""
    metrics = {}
    for metric in ["resting_hr", "heart_rate", "hrv_sdnn", "hrv_value", "recovery_score", "respiratory_rate"]:
        row = conn.execute("""
            SELECT value_mean, value_min, value_max, reading_count, unit, source, methodology
            FROM wearable_observation
            WHERE user_id = ? AND metric = ? AND observation_date = ?
        """, (user_id, metric, target_date)).fetchone()
        if row:
            metrics[metric] = {
                "mean": row["value_mean"], "min": row["value_min"],
                "max": row["value_max"], "count": row["reading_count"],
                "unit": row["unit"], "source": row["source"],
                "methodology": row["methodology"],
            }

    if not metrics:
        return f"No cardiac data for {target_date}."

    # Also get user's baseline (first 7 days of data)
    baseline = {}
    for metric in ["resting_hr", "hrv_sdnn", "hrv_value"]:
        row = conn.execute("""
            SELECT AVG(value_mean) as avg FROM (
                SELECT value_mean FROM wearable_observation
                WHERE user_id = ? AND metric = ?
                ORDER BY observation_date LIMIT 7
            )
        """, (user_id, metric)).fetchone()
        if row and row["avg"]:
            baseline[metric] = round(row["avg"], 1)

    lines = [f"**Cardiac Summary — {target_date}**"]

    if "resting_hr" in metrics:
        m = metrics["resting_hr"]
        bl = baseline.get("resting_hr")
        bl_str = f" (baseline: {bl:.0f}, {'+' if m['mean'] > bl else ''}{((m['mean'] - bl) / bl * 100):.0f}% from baseline)" if bl else ""
        lines.append(f"Resting HR: {m['mean']:.0f} {m['unit']}{bl_str}")

    # HRV — check both old (hrv_sdnn) and new (hrv_value) metric names
    hrv = metrics.get("hrv_value") or metrics.get("hrv_sdnn")
    if hrv:
        method = hrv.get("methodology") or "sdnn"  # default to sdnn for legacy data
        source = hrv.get("source") or "unknown"
        bl_key = "hrv_value" if "hrv_value" in baseline else "hrv_sdnn"
        bl = baseline.get(bl_key)
        bl_str = f" (baseline: {bl:.0f}, {((hrv['mean'] - bl) / bl * 100):+.0f}% from baseline)" if bl else ""
        lines.append(f"HRV: {hrv['mean']:.0f} ms ({method.upper()} via {source}){bl_str}")
        lines.append(f"  ⚠ Methodology note: {method.upper()} — {'measures overall autonomic variability (sympathetic + parasympathetic)' if method == 'sdnn' else 'measures parasympathetic (vagal) activity specifically'}. Do NOT compare with values from a different methodology.")

    if "heart_rate" in metrics:
        m = metrics["heart_rate"]
        lines.append(f"Active HR: avg {m['mean']:.0f}, min {m['min']:.0f}, max {m['max']:.0f} {m['unit']} ({m['count']} readings)")

    if "recovery_score" in metrics:
        m = metrics["recovery_score"]
        method = m.get("methodology") or "unknown"
        method_labels = {
            "whoop_recovery": "WHOOP Recovery (HRV-weighted composite: HRV, RHR, sleep, respiratory rate)",
            "oura_readiness": "Oura Readiness (composite: HRV, RHR, temperature, activity, sleep)",
            "garmin_body_battery": "Garmin Body Battery (HRV stress + activity + sleep charge/drain)",
        }
        desc = method_labels.get(method, method)
        lines.append(f"Recovery Score: {m['mean']:.0f}/100 — {desc}")

    if "respiratory_rate" in metrics:
        m = metrics["respiratory_rate"]
        lines.append(f"Respiratory Rate: {m['mean']:.1f} breaths/min (sleep)")

    return "\n".join(lines)


def get_training_context(conn: sqlite3.Connection, target_date: str, window_days: int = 7, user_id: str = "default") -> str:
    """Get training/exercise context for a date or recent window. Used to distinguish training-induced vs compound-induced changes."""
    from datetime import timedelta

    end = target_date
    start = (date.fromisoformat(target_date) - timedelta(days=window_days)).isoformat()

    rows = conn.execute("""
        SELECT observation_date, value_mean, value_min, value_max, unit, methodology
        FROM wearable_observation
        WHERE user_id = ? AND metric = 'training_load' AND observation_date BETWEEN ? AND ?
        ORDER BY observation_date
    """, (user_id, start, end)).fetchall()

    # Also check for individual training metrics
    training_rows = conn.execute("""
        SELECT observation_date, value_mean, unit, methodology
        FROM wearable_observation
        WHERE user_id = ? AND metric IN ('training_type', 'training_duration', 'training_calories', 'training_intensity')
              AND observation_date BETWEEN ? AND ?
        ORDER BY observation_date, metric
    """, (user_id, start, end)).fetchall()

    if not rows and not training_rows:
        return f"No exercise/training data available for {start} to {end}. Cannot determine whether cardiac changes are training-induced or compound-induced. Interpret HR/HRV trends with caution — they may reflect training load rather than drug effects."

    lines = [f"**Training Context — {window_days} day window ending {target_date}**"]
    lines.append("⚠ Exercise data is approximate — wearable estimates vary by device, form factor, and algorithm. Use as directional context, not precise measurement.")

    if rows:
        values = [r["value_mean"] for r in rows]
        training_days = len([v for v in values if v > 0])
        rest_days = window_days - training_days
        avg_load = sum(values) / len(values) if values else 0
        peak = max(values) if values else 0

        lines.append(f"Training days: {training_days}/{window_days} (rest: {rest_days})")
        lines.append(f"Avg load: {avg_load:.0f}, Peak: {peak:.0f}")

        # Check if today specifically had training
        today_rows = [r for r in rows if r["observation_date"] == target_date]
        if today_rows:
            today_load = today_rows[0]["value_mean"]
            lines.append(f"Today ({target_date}): load {today_load:.0f}")
        else:
            lines.append(f"Today ({target_date}): rest day or no data")

    if training_rows:
        # Group by date
        by_date: dict[str, dict] = {}
        for r in training_rows:
            d = r["observation_date"]
            by_date.setdefault(d, {})
            # Metric name is in the value for training_type, otherwise it's the metric
            by_date[d][r["unit"]] = r["value_mean"]

        recent = list(by_date.items())[-3:]
        for dt, metrics in recent:
            parts = []
            for k, v in metrics.items():
                parts.append(f"{k}: {v}")
            if parts:
                lines.append(f"  {dt}: {', '.join(parts)}")

    lines.append("")
    lines.append("Interpretation: if training load was high in the last 48h, elevated resting HR and suppressed HRV are expected recovery responses — not necessarily compound-induced. Weight fluctuations after training days reflect glycogen, not water retention.")

    return "\n".join(lines)


def get_nutrition_summary(conn: sqlite3.Connection, target_date: str, window_days: int = 7, user_id: str = "default") -> str:
    """Get nutrition/calorie data for a date or window. Self-reported from MFP/MacroFactor/Apple Health — treat as approximate."""
    from datetime import timedelta

    end = target_date
    start = (date.fromisoformat(target_date) - timedelta(days=window_days)).isoformat()

    lines = [f"**Nutrition Summary — {window_days} days ending {target_date}**"]
    lines.append("⚠ Nutrition data is self-reported from food logging apps. Accuracy depends on user logging consistency. Treat as approximate context, not precise measurement.")

    has_data = False
    for metric, label, unit in [
        ("calories_consumed", "Calories", "kcal"),
        ("protein", "Protein", "g"),
        ("fat", "Fat", "g"),
        ("carbs", "Carbs", "g"),
    ]:
        rows = conn.execute("""
            SELECT observation_date, value_mean FROM wearable_observation
            WHERE user_id = ? AND metric = ? AND observation_date BETWEEN ? AND ?
            ORDER BY observation_date
        """, (user_id, metric, start, end)).fetchall()

        if rows:
            has_data = True
            values = [r["value_mean"] for r in rows]
            avg = sum(values) / len(values)
            lines.append(f"{label}: avg {avg:.0f} {unit}/day ({len(rows)} days logged)")

    if not has_data:
        return f"No nutrition data available for {start} to {end}. User may not be logging food, or food logging app is not connected to Apple Health."

    return "\n".join(lines)


def search_drug_interaction(query: str) -> str:
    """Search the web for drug interaction or pharmacology info using Claude with web search."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=CDE_MODEL,
        max_tokens=1024,
        system="You are a pharmacology research assistant. Search for the requested drug interaction or mechanism information. Return a concise factual summary with key points. Do NOT provide clinical recommendations — only factual pharmacological information. Cite sources where possible.",
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"Search for: {query}"}],
    )

    # Extract text from the response (may include tool results)
    parts = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)

    if not parts:
        # If the model used web search but hasn't produced text yet, do a follow-up
        messages = [
            {"role": "user", "content": f"Search for: {query}"},
            {"role": "assistant", "content": response.content},
        ]
        # Add any web search results
        for block in response.content:
            if block.type == "tool_use":
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": block.id, "content": "Please summarize what you found."}
                ]})

        follow_up = client.messages.create(
            model=CDE_MODEL,
            max_tokens=1024,
            system="Summarize the pharmacological information you found. Be concise and factual.",
            messages=messages,
        )
        for block in follow_up.content:
            if block.type == "text":
                parts.append(block.text)

    return "\n".join(parts) if parts else "No results found for this search."


# =============================================================================
# PHASE TRACKING TOOLS
# =============================================================================

def get_all_active_compounds(conn: sqlite3.Connection, user_id: str = "default") -> str:
    """Get ALL compounds with any system level > 0, including ancillaries/supplements.

    Returns current dose, frequency, route, and level for each. Used during
    phase transitions to enumerate every compound the user needs to decide about.
    """
    from datetime import date as date_type

    today = date_type.today().isoformat()
    rows = conn.execute("""
        SELECT cd.id, cd.canonical_name, cd.compound_class, dl.estimated_level,
               dl.days_since_start, dl.at_steady_state
        FROM drug_level dl
        JOIN compound_definition cd ON dl.compound_id = cd.id
        WHERE dl.user_id = ? AND dl.observation_date = ? AND dl.estimated_level > 0.001
        ORDER BY cd.compound_class, dl.estimated_level DESC
    """, (user_id, today)).fetchall()

    if not rows:
        return "No active compounds found."

    lines = ["**All Active Compounds (including ancillaries)**\n"]
    for r in rows:
        # Get current dose/freq/route from latest event
        ev = conn.execute("""
            SELECT dose_mg, frequency, route, event_type
            FROM compound_event
            WHERE user_id = ? AND compound_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id, r["id"])).fetchone()

        dose_info = ""
        if ev and ev["event_type"] != "STOP":
            dose_info = f" — {ev['dose_mg']}mg {ev['frequency']} via {ev['route'] or '?'}"
        elif ev and ev["event_type"] == "STOP":
            dose_info = " — STOPPED (washout)"

        ss = "steady" if r["at_steady_state"] else "ramping"
        lines.append(
            f"  {r['canonical_name']} ({r['compound_class']}){dose_info}, "
            f"level {r['estimated_level']:.0%}, day {r['days_since_start']}, {ss}"
        )

    return "\n".join(lines)


def record_phase_change(
    conn: sqlite3.Connection,
    new_phase: str,
    started_at: str | None = None,
    notes: str | None = None,
    user_id: str = "default",
) -> str:
    """Record a phase transition. Closes the prior phase and opens the new one.

    Call this AFTER all compound events (STOP, DOSE_CHANGE) have been logged
    for the transition. This also regenerates drug levels.
    """
    from datetime import date as date_type, timedelta

    valid_phases = ("blast", "cruise", "pct", "off")
    new_phase = new_phase.lower().strip()
    if new_phase not in valid_phases:
        return f"ERROR: Invalid phase '{new_phase}'. Must be one of: {', '.join(valid_phases)}"

    if not started_at:
        started_at = date_type.today().isoformat()

    # Close current phase
    current = conn.execute(
        "SELECT id, phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (user_id,),
    ).fetchone()

    if current:
        if current["phase"] == new_phase:
            return f"Already in {new_phase} phase (since {current['started_at'][:10]}). No change needed."
        conn.execute(
            "UPDATE cycle_phase SET ended_at = ? WHERE id = ?",
            (started_at, current["id"]),
        )

    # Insert new phase
    conn.execute(
        "INSERT INTO cycle_phase (user_id, phase, started_at, notes) VALUES (?, ?, ?, ?)",
        (user_id, new_phase, started_at, notes),
    )
    conn.commit()

    # Regenerate drug levels to reflect compound changes
    from coach.pk_model import generate_drug_levels
    generate_drug_levels(
        conn, user_id=user_id,
        start_date=date_type.fromisoformat(started_at) - timedelta(days=7),
        end_date=date_type.today() + timedelta(days=30),
    )

    # Build confirmation
    result = f"✓ Phase changed to {new_phase.upper()}"
    if current:
        days_in_prev = (date_type.fromisoformat(started_at) - date_type.fromisoformat(current["started_at"][:10])).days
        result += f" (was {current['phase']} for {days_in_prev} days)"
    result += f"\nStarted: {started_at}"
    if notes:
        result += f"\nNotes: {notes}"
    result += "\nDrug levels regenerated with updated compound events."
    return result


def get_phase_timeline(conn: sqlite3.Connection, user_id: str = "default") -> str:
    """Get the full phase history with dates and durations."""
    from datetime import date as date_type

    rows = conn.execute(
        "SELECT phase, started_at, ended_at, notes FROM cycle_phase WHERE user_id = ? ORDER BY started_at",
        (user_id,),
    ).fetchall()

    if not rows:
        return "No phase history recorded. Phase tracking has not been set up yet."

    lines = ["**Phase Timeline**\n"]
    today = date_type.today()
    for r in rows:
        start = r["started_at"][:10]
        if r["ended_at"]:
            end = r["ended_at"][:10]
            days = (date_type.fromisoformat(end) - date_type.fromisoformat(start)).days
            lines.append(f"  {r['phase'].upper()}: {start} → {end} ({days} days)")
        else:
            days = (today - date_type.fromisoformat(start)).days
            lines.append(f"  {r['phase'].upper()}: {start} → present ({days} days) ← CURRENT")
        if r["notes"]:
            lines.append(f"    Notes: {r['notes']}")

    return "\n".join(lines)


# =============================================================================
# COMPOUND MANAGEMENT TOOLS (write operations)
# =============================================================================

def check_compound_active(conn: sqlite3.Connection, compound_name: str, user_id: str = "default") -> str:
    """Check if a compound is currently active in the user's stack."""
    row = _resolve_compound(conn, compound_name)
    if not row:
        return f"Compound '{compound_name}' not found in the database. Cannot check status."

    cid = row["id"]
    name = row["canonical_name"]

    # Get the most recent event for this compound
    event = conn.execute("""
        SELECT event_type, timestamp, dose_mg, frequency, route
        FROM compound_event
        WHERE user_id = ? AND compound_id = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (user_id, cid)).fetchone()

    if not event:
        return f"**{name}** — NOT in compound log. No events recorded. Safe to add."

    if event["event_type"] == "STOP":
        return f"**{name}** — STOPPED (last event: STOP on {event['timestamp'][:10]}). Can be restarted."

    # Active
    dose_info = f"{event['dose_mg']}mg {event['frequency']}" if event["dose_mg"] else "dose unknown"
    return f"**{name}** — ALREADY ACTIVE. Current: {dose_info} via {event['route'] or 'unknown route'}, started {event['timestamp'][:10]}. Do NOT add a duplicate START event. If dose changed, use update_compound instead."


def add_compound_event(
    conn: sqlite3.Connection,
    compound_name: str,
    event_type: str,
    dose_mg: float | None = None,
    frequency: str | None = None,
    route: str | None = None,
    source_quality: str = "unknown",
    user_id: str = "default",
) -> str:
    """Add a compound event (START, DOSE_CHANGE, STOP) to the cycle log."""
    row = _resolve_compound(conn, compound_name)
    if not row:
        return f"ERROR: Compound '{compound_name}' not found in database. Cannot log event."

    cid = row["id"]
    name = row["canonical_name"]

    # Validate event type
    valid_types = ("START", "DOSE_CHANGE", "STOP", "MISSED_DOSE")
    event_type = event_type.upper()
    if event_type not in valid_types:
        return f"ERROR: Invalid event type '{event_type}'. Must be one of: {', '.join(valid_types)}"

    # Validate required fields for START and DOSE_CHANGE
    if event_type in ("START", "DOSE_CHANGE"):
        if dose_mg is None or dose_mg <= 0:
            return f"ERROR: {event_type} requires a positive dose_mg. Got: {dose_mg}"
        if not frequency:
            return f"ERROR: {event_type} requires frequency (daily, eod, e3d, e3.5d, weekly, biweekly)."
        if not route:
            return f"ERROR: {event_type} requires route (IM, subQ, oral, transdermal)."

    # Safety check: don't duplicate START if already active
    if event_type == "START":
        last_event = conn.execute("""
            SELECT event_type FROM compound_event
            WHERE user_id = ? AND compound_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id, cid)).fetchone()

        if last_event and last_event["event_type"] != "STOP":
            return f"ERROR: {name} is already active (last event: {last_event['event_type']}). Use DOSE_CHANGE to update dose, or STOP first then START to restart."

    # Insert event
    from datetime import datetime
    now = datetime.now().isoformat()

    conn.execute(
        """INSERT INTO compound_event
           (user_id, compound_id, event_type, timestamp, dose_mg,
            frequency, route, source_quality, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1.0)""",
        (user_id, cid, event_type, now, dose_mg, frequency, route, source_quality),
    )
    conn.commit()

    # Regenerate drug levels to reflect this change
    from coach.pk_model import generate_drug_levels
    from datetime import date as date_type, timedelta as td
    generate_drug_levels(
        conn, user_id=user_id,
        start_date=date_type.today() - td(days=7),
        end_date=date_type.today() + td(days=30),
    )

    if event_type == "START":
        return f"✓ Logged: {name} START — {dose_mg}mg {frequency} via {route}. Drug level tracking will begin. The system will now correlate this compound with future metric changes."
    elif event_type == "DOSE_CHANGE":
        return f"✓ Logged: {name} DOSE_CHANGE — new dose {dose_mg}mg {frequency}. Drug level timeline will adjust."
    elif event_type == "STOP":
        return f"✓ Logged: {name} STOP. The drug level timeline will show the washout curve based on half-life. Detectors will know this compound is no longer active."
    else:
        return f"✓ Logged: {name} {event_type}."


# Add to TOOL_DEFINITIONS — compound management
COMPOUND_MGMT_TOOLS = [
    {
        "name": "check_compound_active",
        "description": "Check if a compound is currently active in the user's stack before adding or modifying it. ALWAYS call this before add_compound_event to avoid duplicates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "compound_name": {"type": "string", "description": "Compound name or alias (e.g., 'Deca', 'Nandrolone Decanoate', 'NPP')"}
            },
            "required": ["compound_name"]
        }
    },
    {
        "name": "add_compound_event",
        "description": "Log a compound event (START, DOSE_CHANGE, STOP) to the user's cycle log. ALWAYS call check_compound_active first. For START: requires dose_mg, frequency, route. For STOP: only compound_name and event_type needed. Do NOT ask the user about source quality.",
        "input_schema": {
            "type": "object",
            "properties": {
                "compound_name": {"type": "string", "description": "Compound name or alias"},
                "event_type": {"type": "string", "enum": ["START", "DOSE_CHANGE", "STOP", "MISSED_DOSE"], "description": "Type of event"},
                "dose_mg": {"type": "number", "description": "Dose in mg (required for START and DOSE_CHANGE)"},
                "frequency": {"type": "string", "enum": ["daily", "eod", "e3d", "e3.5d", "weekly", "biweekly", "prn"], "description": "Dosing frequency (required for START and DOSE_CHANGE)"},
                "route": {"type": "string", "enum": ["IM", "subQ", "oral", "transdermal", "sublingual"], "description": "Administration route (required for START and DOSE_CHANGE)"}
            },
            "required": ["compound_name", "event_type"]
        }
    },
]

# Phase tracking tools
PHASE_TOOLS = [
    {
        "name": "get_all_active_compounds",
        "description": "Get ALL active compounds including ancillaries, supplements, and support drugs with current dose/frequency/route. Use during phase transitions to enumerate every compound the user needs to decide about.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "record_phase_change",
        "description": "Record a phase transition (blast/cruise/PCT/off). Call this AFTER all compound events (STOP, DOSE_CHANGE) have been logged for the transition. Regenerates drug levels automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "new_phase": {"type": "string", "enum": ["blast", "cruise", "pct", "off"], "description": "The new phase"},
                "started_at": {"type": "string", "description": "ISO date when the phase started (default: today)"},
                "notes": {"type": "string", "description": "Optional context about this phase"}
            },
            "required": ["new_phase"]
        }
    },
    {
        "name": "get_phase_timeline",
        "description": "Get the user's phase history (blast/cruise/PCT/off) with dates and durations. Use when user asks 'when did I start cruising?', 'how long was my blast?', or 'what phase am I in?'",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
]

# Append to main tool list
TOOL_DEFINITIONS.extend(PHASE_TOOLS)
TOOL_DEFINITIONS.extend(COMPOUND_MGMT_TOOLS)


def execute_tool(conn: sqlite3.Connection, tool_name: str, tool_input: dict, user_id: str = "default") -> str:
    """Execute a tool by name and return the result string."""
    dispatch = {
        "get_metric_summary": lambda: get_metric_summary(conn, tool_input["metric_name"], user_id),
        "get_metric_history": lambda: get_metric_history(conn, tool_input["metric_name"], user_id),
        "get_panel_snapshot": lambda: get_panel_snapshot(conn, tool_input["draw_date"], user_id),
        "compare_panels": lambda: compare_panels(conn, tool_input["date1"], tool_input["date2"], user_id),
        "get_wearable_trend": lambda: get_wearable_trend(conn, tool_input["metric"], tool_input.get("window_days", 90), user_id),
        "get_bp_summary": lambda: get_bp_summary(conn, tool_input.get("window_days", 90), user_id),
        "get_compound_status": lambda: get_compound_status(conn, tool_input["compound_name"], user_id),
        "get_compounds_on_date": lambda: get_compounds_on_date(conn, tool_input["date"], user_id),
        "get_compound_mechanism": lambda: get_compound_mechanism(conn, tool_input["compound_name"]),
        "get_finding_detail": lambda: get_finding_detail(conn, tool_input["finding_id"]),
        "get_finding_history": lambda: get_finding_history(conn, tool_input["theme"], tool_input.get("days", 90), user_id),
        "search_drug_interaction": lambda: search_drug_interaction(tool_input["query"]),
        "get_hr_daily_stats": lambda: get_hr_daily_stats(conn, tool_input["date"], user_id),
        "get_training_context": lambda: get_training_context(conn, tool_input["date"], tool_input.get("window_days", 7), user_id),
        "get_nutrition_summary": lambda: get_nutrition_summary(conn, tool_input["date"], tool_input.get("window_days", 7), user_id),
        "check_compound_active": lambda: check_compound_active(conn, tool_input["compound_name"], user_id),
        "add_compound_event": lambda: add_compound_event(
            conn, tool_input["compound_name"], tool_input["event_type"],
            tool_input.get("dose_mg"), tool_input.get("frequency"),
            tool_input.get("route"), tool_input.get("source_quality", "unknown"), user_id,
        ),
        "get_all_active_compounds": lambda: get_all_active_compounds(conn, user_id),
        "record_phase_change": lambda: record_phase_change(
            conn, tool_input["new_phase"],
            tool_input.get("started_at"), tool_input.get("notes"), user_id,
        ),
        "get_phase_timeline": lambda: get_phase_timeline(conn, user_id),
    }

    handler = dispatch.get(tool_name)
    if not handler:
        return f"Unknown tool: {tool_name}"

    try:
        return handler()
    except Exception as e:
        return f"Tool error: {e}"
