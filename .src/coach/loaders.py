"""Data loaders: wire extraction/ingestion modules into the canonical store.

Each loader:
1. Creates a source_document record (provenance)
2. Inserts observations with FK back to source
3. Returns counts for verification
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from coach.extraction.schema import ValidatedExtraction
from coach.extraction.reference_data import TEST_DEFINITIONS
from coach.apple_health import AppleHealthExport
from coach.cycle_log import CompoundEvent
from coach.compound_db import COMPOUNDS
from coach.bp_entry import BPReading, classify_bp


def seed_metric_definitions(conn: sqlite3.Connection) -> int:
    """Seed the metric_definition table from reference_data.py."""
    count = 0
    for td in TEST_DEFINITIONS:
        conn.execute(
            """INSERT OR IGNORE INTO metric_definition
               (loinc_code, canonical_name, canonical_unit, category,
                plausibility_min, plausibility_max,
                default_ref_low_male, default_ref_high_male)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (td.loinc_code, td.canonical_name, td.canonical_unit, td.category,
             td.plausibility_min, td.plausibility_max,
             td.default_ref_low_male, td.default_ref_high_male),
        )
        count += 1
    conn.commit()
    return count


def seed_compound_definitions(conn: sqlite3.Connection) -> int:
    """Seed the compound_definition table from compound_db.py."""
    count = 0
    for c in COMPOUNDS.values():
        conn.execute(
            """INSERT OR REPLACE INTO compound_definition
               (id, canonical_name, compound_class, ester, parent,
                half_life_hours, half_life_source, route, is_17aa,
                monitoring_markers_json, mechanism_summary, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c.id, c.canonical_name, c.compound_class, c.ester, c.parent,
             c.half_life_hours, c.half_life_source, c.route, int(c.is_17aa),
             json.dumps(c.monitoring_markers), c.mechanism_summary, c.notes),
        )
        count += 1
    conn.commit()
    return count


def load_bloodwork(
    conn: sqlite3.Connection,
    extraction: ValidatedExtraction,
    user_id: str = "default",
) -> int:
    """Load validated bloodwork extraction into the canonical store."""
    if extraction.document_rejected:
        return 0

    # Use draw date or fall back to today
    obs_date = extraction.draw_date or date.today().isoformat()

    # Create source document
    cursor = conn.execute(
        """INSERT INTO source_document (user_id, source_type, original_filename, extractor_version)
           VALUES (?, 'LAB_PDF', ?, 'v0.1.0')""",
        (user_id, extraction.source_file),
    )
    source_id = cursor.lastrowid

    count = 0
    for r in extraction.results:
        loinc = r.loinc_code or "UNMAPPED"

        # Ensure unmapped tests have a metric_definition row so FK holds
        if loinc == "UNMAPPED":
            conn.execute(
                """INSERT OR IGNORE INTO metric_definition
                   (loinc_code, canonical_name, canonical_unit, category)
                   VALUES ('UNMAPPED', 'Unmapped Test', '', 'unmapped')""",
            )

        conn.execute(
            """INSERT INTO metric_observation
               (user_id, metric_loinc, value_canonical, value_string,
                unit_canonical, observation_date, source_document_id,
                extraction_confidence, reference_low, reference_high,
                reference_source, flag, validation_issues, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id,
             loinc,
             r.value,
             r.value_string,
             r.unit_canonical or r.unit_raw,
             obs_date,
             source_id,
             r.confidence,
             r.reference_range_low,
             r.reference_range_high,
             "pdf_extracted",
             r.flag.value if r.flag else None,
             json.dumps([v.value for v in r.validation_issues]) if r.validation_issues else None,
             r.notes),
        )
        count += 1

    conn.commit()
    return count


def load_apple_health(
    conn: sqlite3.Connection,
    export: AppleHealthExport,
    user_id: str = "default",
    source_filename: str = "export.xml",
) -> int:
    """Load Apple Health daily aggregates into the canonical store."""
    # Create source document
    cursor = conn.execute(
        """INSERT INTO source_document (user_id, source_type, original_filename)
           VALUES (?, 'HEALTH_XML', ?)""",
        (user_id, source_filename),
    )
    source_id = cursor.lastrowid

    count = 0
    for d in export.daily:
        conn.execute(
            """INSERT OR REPLACE INTO wearable_observation
               (user_id, metric, observation_date, value_mean, value_min, value_max,
                reading_count, unit, source_document_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, d.metric, d.date.isoformat(), d.mean, d.min, d.max,
             d.count, d.unit, source_id),
        )
        count += 1

    # Store workout/exercise summaries
    for w in export.workouts:
        # Training type
        conn.execute(
            """INSERT OR REPLACE INTO wearable_observation
               (user_id, metric, observation_date, value_mean, reading_count, unit, source_document_id, methodology)
               VALUES (?, 'training_load', ?, ?, ?, 'score', ?, ?)""",
            (user_id, w.date.isoformat(), w.duration_min, w.workout_count, source_id,
             f"{w.training_type}|{w.intensity}"),
        )
        # Duration
        conn.execute(
            """INSERT OR REPLACE INTO wearable_observation
               (user_id, metric, observation_date, value_mean, reading_count, unit, source_document_id)
               VALUES (?, 'training_duration', ?, ?, 1, 'min', ?)""",
            (user_id, w.date.isoformat(), w.duration_min, source_id),
        )
        # Calories
        conn.execute(
            """INSERT OR REPLACE INTO wearable_observation
               (user_id, metric, observation_date, value_mean, reading_count, unit, source_document_id)
               VALUES (?, 'training_calories', ?, ?, 1, 'kcal', ?)""",
            (user_id, w.date.isoformat(), w.calories, source_id),
        )
        count += 3

    conn.commit()
    return count


def load_compound_events(
    conn: sqlite3.Connection,
    events: list[CompoundEvent],
    user_id: str = "default",
) -> int:
    """Load cycle log events into the canonical store."""
    count = 0
    for e in events:
        conn.execute(
            """INSERT INTO compound_event
               (user_id, compound_id, event_type, timestamp, dose_mg,
                frequency, route, source_quality, confidence, user_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id,
             e.compound_id,
             e.event_type.value,
             e.timestamp.isoformat(),
             e.dose_mg,
             e.frequency.value if e.frequency else None,
             e.route.value if e.route else None,
             e.source_quality.value,
             e.confidence,
             e.user_notes),
        )
        count += 1

    conn.commit()
    return count


def load_bp_reading(
    conn: sqlite3.Connection,
    reading: BPReading,
    user_id: str = "default",
) -> int:
    """Load a manual BP reading into the canonical store."""
    classification = classify_bp(reading.systolic, reading.diastolic)
    conn.execute(
        """INSERT INTO bp_reading
           (user_id, systolic, diastolic, heart_rate, timestamp,
            time_of_day, position, classification, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id,
         reading.systolic,
         reading.diastolic,
         reading.heart_rate,
         reading.timestamp.isoformat(),
         reading.time_of_day,
         reading.position,
         classification,
         reading.notes),
    )
    conn.commit()
    return 1
