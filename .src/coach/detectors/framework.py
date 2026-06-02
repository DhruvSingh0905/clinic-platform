"""Trend detector framework.

Detectors are organized as high-level THEMES, not single-metric tripwires.
Each theme aggregates multiple related signals across bloodwork, wearables,
and the drug timeline. The theme identifies statistical patterns and produces
structured findings that the LLM uses to reason and explain.

The detector does the math. The LLM does the language.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Severity(str, Enum):
    INFO = "info"                # pattern exists, worth noting
    NOTABLE = "notable"          # pattern is meaningful, user should be aware
    CONCERNING = "concerning"    # pattern warrants attention / clinician discussion


@dataclass
class Signal:
    """A single statistical observation within a theme."""
    metric: str                  # what was measured
    description: str             # plain English: "Hematocrit rose from 47% to 52%"
    value_current: float | None = None
    value_baseline: float | None = None
    value_change: float | None = None
    value_change_pct: float | None = None
    trend_direction: str = ""    # "rising", "falling", "stable", "volatile"
    time_window: str = ""        # "last 8 weeks", "since cycle start"
    supporting_dates: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class DrugContext:
    """What compounds are relevant to this finding."""
    compound_id: str
    compound_name: str
    compound_class: str
    days_on: int
    at_steady_state: bool
    current_level: float         # from drug_level table (0-1 scale)
    dose_info: str = ""          # "250mg E3.5D"


@dataclass
class Finding:
    """Output of a theme detector. Structured for LLM consumption."""
    theme: str                   # "cardiovascular", "hepatic", etc.
    detector_id: str             # "cv_stress", "hepatic_load", etc.
    severity: Severity
    headline: str                # one-line summary
    signals: list[Signal]        # all the statistical evidence
    drug_context: list[DrugContext]  # what's in the system
    time_window_start: str = ""
    time_window_end: str = ""
    confidence: float = 1.0
    recommendations: list[str] = field(default_factory=list)  # "discuss with clinician", "recheck in 4 weeks"


def get_metric_series(
    conn: sqlite3.Connection,
    metric_loinc: str,
    user_id: str = "default",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[tuple[str, float]]:
    """Get a timeseries of (date, value) for a bloodwork metric."""
    query = """SELECT observation_date, value_canonical
               FROM metric_observation
               WHERE user_id = ? AND metric_loinc = ? AND value_canonical IS NOT NULL"""
    params: list = [user_id, metric_loinc]

    if start_date:
        query += " AND observation_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND observation_date <= ?"
        params.append(end_date)

    query += " ORDER BY observation_date"
    return [(r[0], r[1]) for r in conn.execute(query, params).fetchall()]


def get_wearable_series(
    conn: sqlite3.Connection,
    metric: str,
    user_id: str = "default",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[tuple[str, float]]:
    """Get a timeseries of (date, value_mean) for a wearable metric."""
    query = """SELECT observation_date, value_mean
               FROM wearable_observation
               WHERE user_id = ? AND metric = ?"""
    params: list = [user_id, metric]

    if start_date:
        query += " AND observation_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND observation_date <= ?"
        params.append(end_date)

    query += " ORDER BY observation_date"
    return [(r[0], r[1]) for r in conn.execute(query, params).fetchall()]


def get_active_compounds(
    conn: sqlite3.Connection,
    on_date: str,
    user_id: str = "default",
) -> list[DrugContext]:
    """Get all active compounds with their drug levels on a given date."""
    rows = conn.execute("""
        SELECT dl.compound_id, cd.canonical_name, cd.compound_class,
               dl.estimated_level, dl.days_since_start, dl.at_steady_state,
               ce_latest.dose_mg, ce_latest.frequency
        FROM drug_level dl
        JOIN compound_definition cd ON dl.compound_id = cd.id
        LEFT JOIN (
            SELECT compound_id, dose_mg, frequency,
                   ROW_NUMBER() OVER (PARTITION BY compound_id ORDER BY timestamp DESC) as rn
            FROM compound_event
            WHERE user_id = ? AND event_type IN ('START', 'DOSE_CHANGE')
        ) ce_latest ON dl.compound_id = ce_latest.compound_id AND ce_latest.rn = 1
        WHERE dl.user_id = ? AND dl.observation_date = ? AND dl.estimated_level > 0.001
    """, (user_id, user_id, on_date)).fetchall()

    return [DrugContext(
        compound_id=r["compound_id"],
        compound_name=r["canonical_name"],
        compound_class=r["compound_class"],
        days_on=r["days_since_start"],
        at_steady_state=bool(r["at_steady_state"]),
        current_level=r["estimated_level"],
        dose_info=f"{r['dose_mg']}mg {r['frequency']}" if r["dose_mg"] else "",
    ) for r in rows]


def compute_trend(series: list[tuple[str, float]]) -> tuple[str, float | None]:
    """Compute simple trend direction and slope from a timeseries.

    Returns (direction, change_per_period) where direction is
    'rising', 'falling', 'stable', or 'insufficient_data'.
    """
    if len(series) < 2:
        return ("insufficient_data", None)

    values = [v for _, v in series]
    first_half = values[:len(values)//2]
    second_half = values[len(values)//2:]

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    change = avg_second - avg_first
    pct_change = (change / avg_first * 100) if avg_first != 0 else 0

    if abs(pct_change) < 3:
        return ("stable", change)
    elif change > 0:
        return ("rising", change)
    else:
        return ("falling", change)


def store_finding(conn: sqlite3.Connection, finding: Finding, user_id: str = "default") -> int:
    """Persist a finding to the database."""
    import json
    cursor = conn.execute(
        """INSERT INTO finding
           (user_id, detector_id, severity, summary, detail,
            supporting_observation_ids, time_window_start, time_window_end,
            confidence, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
        (user_id,
         finding.detector_id,
         finding.severity.value,
         finding.headline,
         json.dumps({
             "signals": [{"metric": s.metric, "description": s.description,
                          "current": s.value_current, "baseline": s.value_baseline,
                          "change": s.value_change, "trend": s.trend_direction}
                         for s in finding.signals],
             "drug_context": [{"name": d.compound_name, "class": d.compound_class,
                               "days_on": d.days_on, "level": d.current_level}
                              for d in finding.drug_context],
             "recommendations": finding.recommendations,
         }),
         None,  # supporting_observation_ids — could populate later
         finding.time_window_start,
         finding.time_window_end,
         finding.confidence),
    )
    conn.commit()
    return cursor.lastrowid
