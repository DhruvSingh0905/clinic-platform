"""Mock data seeder for Clinic Platform demo.

6 realistic TRT/HRT clinic patients with cross-metric patterns.
CDE-compatible tables use `user_id` column (= patient.id).
Clinic Platform-specific tables use `patient_id`.
"""
import uuid
from datetime import datetime, timedelta
import random

CLINICIAN_ID = "clinician-001"
CLINICIAN_NAME = "Demo Clinician"
CLINICIAN_EMAIL = "clinician@demo.com"

PATIENTS = [
    {"id": "patient-001", "name": "Marcus D.", "email": "marcus@demo.com", "avatar_color": "#C44536", "status": "active_treatment", "status_day": 28, "integrations": ["whoop", "apple_health"]},
    {"id": "patient-002", "name": "Jordan K.", "email": "jordan@demo.com", "avatar_color": "#C17A2F", "status": "monitoring", "status_day": 90, "integrations": ["whoop", "withings"]},
    {"id": "patient-003", "name": "Alex M.", "email": "alex@demo.com", "avatar_color": "#4A7FA5", "status": "active_treatment", "status_day": 18, "integrations": ["whoop", "apple_health", "withings"]},
    {"id": "patient-004", "name": "Riley P.", "email": "riley@demo.com", "avatar_color": "#5A8A5C", "status": "discontinued", "status_day": 12, "integrations": ["apple_health"]},
    {"id": "patient-005", "name": "Sam T.", "email": "sam@demo.com", "avatar_color": "#8B6E99", "status": "initial_consult", "status_day": 5, "integrations": ["whoop", "apple_health", "dexcom"]},
    {"id": "patient-006", "name": "Casey W.", "email": "casey@demo.com", "avatar_color": "#7A8B6E", "status": "tapering", "status_day": 45, "integrations": ["apple_health", "dexcom"]},
]


def _date(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

def _ts(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).isoformat()


def seed_mock_data(conn):
    """Seed the database with realistic mock data."""
    conn.execute("INSERT OR IGNORE INTO clinician (id, name, email) VALUES (?, ?, ?)", (CLINICIAN_ID, CLINICIAN_NAME, CLINICIAN_EMAIL))

    for a in PATIENTS:
        conn.execute("INSERT OR IGNORE INTO patient (id, name, email, avatar_color) VALUES (?, ?, ?, ?)",
                     (a["id"], a["name"], a["email"], a["avatar_color"]))
        conn.execute("INSERT OR IGNORE INTO clinician_patient (clinician_id, patient_id) VALUES (?, ?)",
                     (CLINICIAN_ID, a["id"]))
        for provider in a["integrations"]:
            conn.execute("INSERT OR IGNORE INTO integration_status (patient_id, provider, status, last_sync) VALUES (?, ?, 'connected', ?)",
                         (a["id"], provider, _ts(0)))
        conn.execute("INSERT OR IGNORE INTO cycle_phase (user_id, phase, started_at) VALUES (?, ?, ?)",
                     (a["id"], a["status"], _ts(a["status_day"])))

    _seed_wearables(conn)
    _seed_labs(conn)
    _seed_compounds(conn)
    _seed_training(conn)
    _seed_nutrition(conn)
    _seed_recovery(conn)
    conn.commit()


def _seed_wearables(conn):
    profiles = {
        "patient-001": {"resting_hr": (58, 62, 0.1), "hrv_rmssd": (45, 55, -0.2), "weight_kg": (103, 105, 0.05), "recovery_score": (55, 75, -0.3)},
        "patient-002": {"resting_hr": (56, 65, 0.3), "hrv_rmssd": (52, 65, -0.4), "weight_kg": (92, 94, 0.02), "recovery_score": (45, 70, -0.5)},
        "patient-003": {"resting_hr": (54, 58, 0.05), "hrv_rmssd": (58, 68, 0.1), "weight_kg": (88, 90, 0.01), "recovery_score": (65, 80, 0.1)},
        "patient-004": {"resting_hr": (60, 65, -0.15), "hrv_rmssd": (35, 50, 0.5), "weight_kg": (82, 84, -0.03), "recovery_score": (55, 75, 0.4)},
        "patient-005": {"resting_hr": (50, 54, 0.1), "hrv_rmssd": (60, 72, -0.1), "weight_kg": (58, 60, -0.06), "recovery_score": (50, 65, -0.2)},
        "patient-006": {"resting_hr": (55, 60, 0.05), "hrv_rmssd": (55, 65, 0.05), "weight_kg": (64, 66, 0.04), "recovery_score": (60, 75, 0.1)},
    }
    for uid, metrics in profiles.items():
        source = "WHOOP" if uid in ("patient-001", "patient-002", "patient-003", "patient-005") else "Apple Watch"
        for day in range(30):
            date = _date(29 - day)
            for metric, (low, high, trend) in metrics.items():
                base = low + (high - low) * (day / 30)
                value = base + trend * day + random.uniform(-1.5, 1.5)
                value = round(max(low * 0.8, min(high * 1.2, value)), 1)
                unit = {"resting_hr": "bpm", "hrv_rmssd": "ms", "weight_kg": "kg", "recovery_score": "%"}.get(metric, "")
                methodology = "rmssd" if metric == "hrv_rmssd" else None
                conn.execute(
                    "INSERT OR IGNORE INTO wearable_observation (user_id, metric, observation_date, value_mean, unit, source, methodology) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (uid, metric, date, value, unit, source, methodology))


def _seed_labs(conn):
    labs = [
        ("patient-001", "2930-0", 48.0, "%", "normal", 38.3, 48.6, 45),
        ("patient-001", "2930-0", 50.2, "%", "normal", 38.3, 48.6, 28),
        ("patient-001", "2930-0", 52.1, "%", "high", 38.3, 48.6, 3),
        ("patient-001", "789-8", 5.2, "M/uL", "normal", 4.14, 5.8, 45),
        ("patient-001", "789-8", 5.6, "M/uL", "normal", 4.14, 5.8, 28),
        ("patient-001", "789-8", 5.9, "M/uL", "high", 4.14, 5.8, 3),
        ("patient-001", "2093-3", 220, "mg/dL", "high", 0, 200, 28),
        ("patient-001", "2571-8", 165, "mg/dL", "high", 0, 150, 28),
        ("patient-001", "1742-6", 38, "U/L", "normal", 7, 56, 28),
        ("patient-003", "1742-6", 32, "U/L", "normal", 7, 56, 45),
        ("patient-003", "1742-6", 74, "U/L", "high", 7, 56, 5),
        ("patient-003", "1920-8", 28, "U/L", "normal", 10, 40, 45),
        ("patient-003", "1920-8", 52, "U/L", "high", 10, 40, 5),
        ("patient-003", "2093-3", 195, "mg/dL", "normal", 0, 200, 5),
        ("patient-003", "2085-9", 38, "mg/dL", "low", 40, 60, 5),
        ("patient-004", "2093-3", 235, "mg/dL", "high", 0, 200, 14),
        ("patient-004", "2085-9", 29, "mg/dL", "low", 40, 60, 14),
        ("patient-004", "2571-8", 180, "mg/dL", "high", 0, 150, 14),
        ("patient-004", "2823-3", 4.2, "mEq/L", "normal", 3.5, 5.0, 14),
        ("patient-004", "2160-0", 1.1, "mg/dL", "normal", 0.7, 1.3, 14),
    ]
    for uid, loinc, val, unit, flag, ref_l, ref_h, days_ago in labs:
        conn.execute(
            "INSERT INTO metric_observation (user_id, metric_loinc, value_canonical, unit_canonical, observation_date, flag, reference_low, reference_high) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, loinc, val, unit, _date(days_ago), flag, ref_l, ref_h))


def _seed_compounds(conn):
    COMPOUND_MAP = {
        "Testosterone Cypionate": "test_cyp", "Testosterone Enanthate": "test_e",
        "Anastrozole": "anastrozole",
    }
    events = {
        "patient-001": [("Testosterone Cypionate", "START", 200, "weekly", "IM", 28)],
        "patient-002": [("Testosterone Cypionate", "START", 160, "e3.5d", "IM", 90), ("Anastrozole", "START", 0.5, "e3.5d", "oral", 90)],
        "patient-003": [("Testosterone Enanthate", "START", 200, "weekly", "IM", 18), ("Anastrozole", "START", 0.5, "e3.5d", "oral", 18)],
        "patient-004": [("Testosterone Cypionate", "START", 200, "weekly", "IM", 120), ("Testosterone Cypionate", "STOP", None, None, None, 12)],
        "patient-005": [],
        "patient-006": [("Testosterone Cypionate", "START", 200, "weekly", "IM", 90), ("Testosterone Cypionate", "DOSE_CHANGE", 150, "weekly", "IM", 45)],
    }
    for uid, evts in events.items():
        for name, evt_type, dose, freq, route, days_ago in evts:
            cid = COMPOUND_MAP.get(name, name.lower().replace(" ", "_"))
            conn.execute(
                "INSERT INTO compound_event (user_id, compound_id, event_type, dose_mg, frequency, route, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, cid, evt_type, dose, freq, route, _ts(days_ago)))

    active_levels = {
        "patient-001": [("test_cyp", 0.92, 200, True)],
        "patient-002": [("test_cyp", 0.95, 160, True), ("anastrozole", 0.90, 0.5, True)],
        "patient-003": [("test_e", 0.78, 200, False), ("anastrozole", 0.85, 0.5, False)],
        "patient-004": [("test_cyp", 0.12, 24, False)],
        "patient-006": [("test_cyp", 0.88, 150, True)],
    }
    for uid, levels in active_levels.items():
        for cid, level, dose_mg, steady in levels:
            for day in range(14):
                decay = 1.0 if steady else max(0.05, level - day * 0.02)
                est = round(level * decay + random.uniform(-0.03, 0.03), 3)
                conn.execute(
                    "INSERT OR IGNORE INTO drug_level (user_id, compound_id, observation_date, estimated_level, dose_active_mg, days_since_start, at_steady_state) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (uid, cid, _date(13 - day), est, dose_mg, 28 + day if steady else day, 1 if steady else 0))


def _seed_training(conn):
    blocks = [
        ("patient-001", "Exercise Program A", "exercise", 28, None, "4-day upper/lower split, progressive overload"),
        ("patient-002", "Maintenance Program", "maintenance", 90, None, "3-day full body, steady state"),
        ("patient-003", "Exercise Program B", "exercise", 18, None, "4-day upper/lower, moderate volume"),
        ("patient-004", "Recovery Program", "maintenance", 12, None, "3-day full body, reduced volume"),
        ("patient-005", "Exercise Program C", "exercise", 5, None, "Initial program, awaiting labs"),
        ("patient-006", "Maintenance Program", "maintenance", 45, None, "4-day upper/lower, maintenance intensity"),
    ]
    for patient_id, name, btype, days_ago, end, notes in blocks:
        conn.execute(
            "INSERT INTO training_block (id, patient_id, clinician_id, name, block_type, start_date, end_date, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')",
            (str(uuid.uuid4()), patient_id, CLINICIAN_ID, name, btype, _date(days_ago), end, notes))


def _seed_nutrition(conn):
    targets = [
        ("patient-001", 2800, 210, 310, 75, "Standard maintenance, balanced macros"),
        ("patient-002", 2600, 200, 280, 72, "Moderate intake, monitoring weight"),
        ("patient-003", 2500, 190, 270, 70, "Initial targets, adjust at follow-up"),
        ("patient-004", 2200, 170, 240, 65, "Reduced intake during monitoring"),
        ("patient-005", 2400, 180, 260, 68, "Pending lab results, standard targets"),
        ("patient-006", 2300, 175, 250, 66, "Tapering phase, slight deficit"),
    ]
    for patient_id, cal, pro, carb, fat, notes in targets:
        conn.execute(
            "INSERT INTO nutrition_target (id, patient_id, clinician_id, calories, protein_g, carbs_g, fat_g, notes, effective_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), patient_id, CLINICIAN_ID, cal, pro, carb, fat, notes, _date(7)))


def _seed_recovery(conn):
    notes = [
        ("patient-001", "assessment", "Monitor BP — weight up, TRT active. Next draw in 2 weeks.", 5),
        ("patient-002", "follow_up", "Patient reports improved energy and mood on current protocol.", 3),
        ("patient-002", "subjective", "Patient reports poor sleep quality — investigate stress/stimulant use.", 1),
        ("patient-003", "plan", "Initial labs pending. Monitor liver values at 6 weeks.", 4),
        ("patient-004", "assessment", "Discontinued TRT per patient request. Monitoring recovery labs.", 7),
        ("patient-005", "plan", "Awaiting initial lab panel. Baseline assessment scheduled.", 2),
        ("patient-005", "subjective", "Patient reports fatigue and low energy — primary complaint.", 1),
        ("patient-006", "follow_up", "Dose tapering on schedule. Recheck labs at 60 days.", 6),
    ]
    for patient_id, ntype, content, days_ago in notes:
        conn.execute(
            "INSERT INTO recovery_note (id, patient_id, clinician_id, note_type, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), patient_id, CLINICIAN_ID, ntype, content, _ts(days_ago)))
