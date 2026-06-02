"""Multi-tenant database for Coach Platform.

Shared data tables (wearable_observation, metric_observation, compound_event,
drug_level, finding, cycle_phase, bp_reading) use CDE-compatible column names
so CDE's functions (detectors, PK model, LLM tools) work against this DB
without modification. The key column: `user_id` stores the athlete's ID.

Coach Platform-specific tables (coach, athlete, coach_athlete, training_block,
nutrition_target, recovery_note, operation_log, integration_status) use
`athlete_id` and `coach_id` for multi-tenant clarity.
"""
import sqlite3
import os
from coach.config import COACH_DB_PATH


def get_db() -> sqlite3.Connection:
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        COACH_DB_PATH,
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection):
    conn.executescript("""

    -- ══════════════════════════════════════════════════════════
    -- Coach Platform-specific tables (multi-tenant identity)
    -- ══════════════════════════════════════════════════════════

    CREATE TABLE IF NOT EXISTS coach (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS athlete (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        avatar_color TEXT NOT NULL DEFAULT '#C17A2F',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS coach_athlete (
        coach_id TEXT NOT NULL REFERENCES coach(id),
        athlete_id TEXT NOT NULL REFERENCES athlete(id),
        added_at TEXT NOT NULL DEFAULT (datetime('now')),
        status TEXT NOT NULL DEFAULT 'active',
        PRIMARY KEY (coach_id, athlete_id)
    );

    CREATE TABLE IF NOT EXISTS integration_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id TEXT NOT NULL REFERENCES athlete(id),
        provider TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'connected',
        last_sync TEXT,
        UNIQUE(athlete_id, provider)
    );

    -- ══════════════════════════════════════════════════════════
    -- CDE-compatible data tables (user_id = athlete.id)
    -- Column names match CDE's schema so CDE functions work
    -- ══════════════════════════════════════════════════════════

    CREATE TABLE IF NOT EXISTS source_document (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL,
        source_type     TEXT NOT NULL,
        uploaded_at     TEXT NOT NULL DEFAULT (datetime('now')),
        extractor_version TEXT,
        raw_storage_path TEXT,
        metadata_json   TEXT
    );

    CREATE TABLE IF NOT EXISTS metric_definition (
        loinc_code      TEXT PRIMARY KEY,
        canonical_name  TEXT NOT NULL,
        canonical_unit  TEXT NOT NULL DEFAULT '',
        category        TEXT,
        plausibility_min REAL,
        plausibility_max REAL,
        default_ref_low_male REAL,
        default_ref_high_male REAL
    );

    CREATE TABLE IF NOT EXISTS metric_observation (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             TEXT NOT NULL,
        metric_loinc        TEXT NOT NULL,
        value_canonical     REAL,
        value_string        TEXT,
        unit_canonical      TEXT NOT NULL,
        observation_date    TEXT NOT NULL,
        observation_timestamp TEXT,
        source_document_id  INTEGER REFERENCES source_document(id),
        extraction_confidence REAL,
        reference_low       REAL,
        reference_high      REAL,
        reference_source    TEXT,
        flag                TEXT,
        validation_issues   TEXT,
        created_at          TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wearable_observation (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL,
        metric          TEXT NOT NULL,
        observation_date TEXT NOT NULL,
        value_mean      REAL NOT NULL,
        value_min       REAL,
        value_max       REAL,
        reading_count   INTEGER NOT NULL DEFAULT 1,
        unit            TEXT NOT NULL,
        source          TEXT,
        methodology     TEXT,
        source_document_id INTEGER REFERENCES source_document(id),
        UNIQUE(user_id, metric, observation_date, source)
    );

    CREATE TABLE IF NOT EXISTS compound_definition (
        id              TEXT PRIMARY KEY,
        canonical_name  TEXT NOT NULL,
        compound_class  TEXT,
        ester           TEXT,
        parent          TEXT,
        half_life_hours REAL,
        half_life_source TEXT,
        route           TEXT,
        is_17aa         INTEGER DEFAULT 0,
        dose_range_trt  TEXT,
        dose_range_supra TEXT,
        monitoring_markers_json TEXT,
        mechanism_summary TEXT,
        notes           TEXT
    );

    CREATE TABLE IF NOT EXISTS compound_event (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL,
        compound_id     TEXT NOT NULL REFERENCES compound_definition(id),
        event_type      TEXT NOT NULL,
        timestamp       TEXT NOT NULL,
        dose_mg         REAL,
        frequency       TEXT,
        route           TEXT,
        source_quality  TEXT NOT NULL DEFAULT 'unknown',
        confidence      REAL NOT NULL DEFAULT 1.0,
        user_notes      TEXT
    );

    CREATE TABLE IF NOT EXISTS drug_level (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL,
        compound_id     TEXT NOT NULL REFERENCES compound_definition(id),
        observation_date TEXT NOT NULL,
        estimated_level REAL NOT NULL,
        dose_active_mg  REAL,
        days_since_start INTEGER,
        at_steady_state INTEGER NOT NULL DEFAULT 0,
        UNIQUE(user_id, compound_id, observation_date)
    );

    CREATE TABLE IF NOT EXISTS bp_reading (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL,
        systolic        INTEGER NOT NULL,
        diastolic       INTEGER NOT NULL,
        heart_rate      INTEGER,
        timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
        time_of_day     TEXT,
        position        TEXT DEFAULT 'seated',
        classification  TEXT,
        notes           TEXT
    );

    CREATE TABLE IF NOT EXISTS finding (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL,
        detector_id     TEXT NOT NULL,
        severity        TEXT NOT NULL,
        summary         TEXT NOT NULL,
        detail          TEXT,
        supporting_observation_ids TEXT,
        detected_at     TEXT NOT NULL DEFAULT (datetime('now')),
        time_window_start TEXT,
        time_window_end TEXT,
        confidence      REAL,
        status          TEXT NOT NULL DEFAULT 'active',
        dismiss_reason  TEXT
    );

    CREATE TABLE IF NOT EXISTS cycle_phase (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        phase TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT
    );

    CREATE TABLE IF NOT EXISTS scheduled_event (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL,
        event_type      TEXT NOT NULL,
        scheduled_date  TEXT NOT NULL,
        compound_id     TEXT,
        description     TEXT,
        recurring       INTEGER NOT NULL DEFAULT 0,
        recurrence_rule TEXT,
        status          TEXT NOT NULL DEFAULT 'upcoming',
        created_by      TEXT DEFAULT 'system',
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ══════════════════════════════════════════════════════════
    -- Coach Platform coaching-surface tables
    -- ══════════════════════════════════════════════════════════

    CREATE TABLE IF NOT EXISTS training_block (
        id TEXT PRIMARY KEY,
        athlete_id TEXT NOT NULL REFERENCES athlete(id),
        coach_id TEXT NOT NULL REFERENCES coach(id),
        name TEXT NOT NULL,
        block_type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        notes TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS nutrition_target (
        id TEXT PRIMARY KEY,
        athlete_id TEXT NOT NULL REFERENCES athlete(id),
        coach_id TEXT NOT NULL REFERENCES coach(id),
        calories INTEGER NOT NULL,
        protein_g INTEGER NOT NULL,
        carbs_g INTEGER NOT NULL,
        fat_g INTEGER NOT NULL,
        notes TEXT,
        effective_date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS recovery_note (
        id TEXT PRIMARY KEY,
        athlete_id TEXT NOT NULL REFERENCES athlete(id),
        coach_id TEXT NOT NULL REFERENCES coach(id),
        note_type TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS operation_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_id TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        rendered_text TEXT NOT NULL,
        committed_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ══════════════════════════════════════════════════════════
    -- Hevy integration tables
    -- ══════════════════════════════════════════════════════════

    CREATE TABLE IF NOT EXISTS workout_session (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        hevy_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        duration_seconds INTEGER,
        notes TEXT,
        synced_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS workout_set (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES workout_session(id),
        user_id TEXT NOT NULL,
        exercise_template_id TEXT NOT NULL,
        exercise_name TEXT NOT NULL,
        set_index INTEGER NOT NULL,
        set_type TEXT NOT NULL,
        weight_kg REAL,
        reps INTEGER,
        rpe REAL,
        estimated_1rm REAL,
        UNIQUE(session_id, exercise_template_id, set_index)
    );

    CREATE TABLE IF NOT EXISTS exercise_template (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        muscle_group TEXT,
        equipment TEXT,
        is_custom INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS routine_push (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coach_id TEXT NOT NULL,
        athlete_id TEXT NOT NULL,
        hevy_routine_id TEXT,
        title TEXT NOT NULL,
        routine_json TEXT NOT NULL,
        pushed_at TEXT NOT NULL DEFAULT (datetime('now')),
        status TEXT DEFAULT 'active'
    );

    CREATE TABLE IF NOT EXISTS lift_progression (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        exercise_template_id TEXT NOT NULL,
        exercise_name TEXT NOT NULL,
        session_date TEXT NOT NULL,
        working_weight_kg REAL,
        best_set_reps INTEGER,
        estimated_1rm REAL,
        total_volume_kg REAL,
        set_count INTEGER,
        UNIQUE(user_id, exercise_template_id, session_date)
    );

    CREATE TABLE IF NOT EXISTS notification (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        actor_id TEXT,
        actor_role TEXT,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT,
        detail_json TEXT,
        read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ══════════════════════════════════════════════════════════
    -- Indexes
    -- ══════════════════════════════════════════════════════════

    CREATE INDEX IF NOT EXISTS idx_metric_obs_user_date ON metric_observation(user_id, observation_date);
    CREATE INDEX IF NOT EXISTS idx_metric_obs_loinc_date ON metric_observation(metric_loinc, observation_date);
    CREATE INDEX IF NOT EXISTS idx_wearable_user_date ON wearable_observation(user_id, observation_date);
    CREATE INDEX IF NOT EXISTS idx_wearable_metric_date ON wearable_observation(metric, observation_date);
    CREATE INDEX IF NOT EXISTS idx_compound_event_user ON compound_event(user_id, compound_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_drug_level_compound_date ON drug_level(compound_id, observation_date);
    CREATE INDEX IF NOT EXISTS idx_finding_user_status ON finding(user_id, status);
    CREATE INDEX IF NOT EXISTS idx_training_athlete ON training_block(athlete_id);
    CREATE INDEX IF NOT EXISTS idx_nutrition_athlete ON nutrition_target(athlete_id);
    CREATE INDEX IF NOT EXISTS idx_scheduled_user ON scheduled_event(user_id, scheduled_date);
    CREATE INDEX IF NOT EXISTS idx_bp_user ON bp_reading(user_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_workout_session_user ON workout_session(user_id, started_at);
    CREATE INDEX IF NOT EXISTS idx_workout_set_session ON workout_set(session_id);
    CREATE INDEX IF NOT EXISTS idx_workout_set_exercise ON workout_set(user_id, exercise_template_id);
    CREATE INDEX IF NOT EXISTS idx_lift_prog_user_ex ON lift_progression(user_id, exercise_template_id, session_date);
    CREATE INDEX IF NOT EXISTS idx_notification_user ON notification(user_id, read, created_at);
    """)
    conn.commit()
