"""Mock data seeder for Coach Platform demo.

6 realistic physique clients with cross-metric patterns.
CDE-compatible tables use `user_id` column (= athlete.id).
Coach Platform-specific tables use `athlete_id`.
"""
import uuid
import json
from datetime import datetime, timedelta
import random

COACH_ID = "coach-001"
COACH_NAME = "Demo Coach"
COACH_EMAIL = "coach@demo.com"

ATHLETES = [
    {"id": "athlete-001", "name": "Marcus D.", "email": "marcus@demo.com", "avatar_color": "#C44536", "phase": "blast", "phase_day": 28, "integrations": ["whoop", "apple_health"]},
    {"id": "athlete-002", "name": "Jordan K.", "email": "jordan@demo.com", "avatar_color": "#C17A2F", "phase": "blast", "phase_day": 42, "integrations": ["whoop", "withings"]},
    {"id": "athlete-003", "name": "Alex M.", "email": "alex@demo.com", "avatar_color": "#4A7FA5", "phase": "cruise", "phase_day": 18, "integrations": ["whoop", "apple_health", "withings"]},
    {"id": "athlete-004", "name": "Riley P.", "email": "riley@demo.com", "avatar_color": "#5A8A5C", "phase": "off", "phase_day": 12, "integrations": ["apple_health"]},
    {"id": "athlete-005", "name": "Sam T.", "email": "sam@demo.com", "avatar_color": "#8B6E99", "phase": "prep", "phase_day": 65, "integrations": ["whoop", "apple_health", "dexcom"]},
    {"id": "athlete-006", "name": "Casey W.", "email": "casey@demo.com", "avatar_color": "#7A8B6E", "phase": "offseason", "phase_day": 45, "integrations": ["apple_health", "dexcom"]},
]


def _date(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

def _ts(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).isoformat()


def seed_mock_data(conn):
    """Seed the database with realistic mock data."""
    conn.execute("INSERT OR IGNORE INTO coach (id, name, email) VALUES (?, ?, ?)", (COACH_ID, COACH_NAME, COACH_EMAIL))

    for a in ATHLETES:
        conn.execute("INSERT OR IGNORE INTO athlete (id, name, email, avatar_color) VALUES (?, ?, ?, ?)",
                     (a["id"], a["name"], a["email"], a["avatar_color"]))
        conn.execute("INSERT OR IGNORE INTO coach_athlete (coach_id, athlete_id) VALUES (?, ?)",
                     (COACH_ID, a["id"]))
        for provider in a["integrations"]:
            conn.execute("INSERT OR IGNORE INTO integration_status (athlete_id, provider, status, last_sync) VALUES (?, ?, 'connected', ?)",
                         (a["id"], provider, _ts(0)))
        conn.execute("INSERT OR IGNORE INTO cycle_phase (user_id, phase, started_at) VALUES (?, ?, ?)",
                     (a["id"], a["phase"], _ts(a["phase_day"])))

    _seed_wearables(conn)
    _seed_labs(conn)
    _seed_compounds(conn)
    _seed_findings(conn)
    _seed_training(conn)
    _seed_nutrition(conn)
    _seed_recovery(conn)
    conn.commit()


def _seed_wearables(conn):
    profiles = {
        "athlete-001": {"resting_hr": (58, 62, 0.1), "hrv_rmssd": (45, 55, -0.2), "weight_kg": (103, 105, 0.05), "recovery_score": (55, 75, -0.3)},
        "athlete-002": {"resting_hr": (56, 65, 0.3), "hrv_rmssd": (52, 65, -0.4), "weight_kg": (92, 94, 0.02), "recovery_score": (45, 70, -0.5)},
        "athlete-003": {"resting_hr": (54, 58, 0.05), "hrv_rmssd": (58, 68, 0.1), "weight_kg": (88, 90, 0.01), "recovery_score": (65, 80, 0.1)},
        "athlete-004": {"resting_hr": (60, 65, -0.15), "hrv_rmssd": (35, 50, 0.5), "weight_kg": (82, 84, -0.03), "recovery_score": (55, 75, 0.4)},
        "athlete-005": {"resting_hr": (50, 54, 0.1), "hrv_rmssd": (60, 72, -0.1), "weight_kg": (58, 60, -0.06), "recovery_score": (50, 65, -0.2)},
        "athlete-006": {"resting_hr": (55, 60, 0.05), "hrv_rmssd": (55, 65, 0.05), "weight_kg": (64, 66, 0.04), "recovery_score": (60, 75, 0.1)},
    }
    for uid, metrics in profiles.items():
        source = "WHOOP" if uid in ("athlete-001", "athlete-002", "athlete-003", "athlete-005") else "Apple Watch"
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
        ("athlete-001", "2930-0", 48.0, "%", "normal", 38.3, 48.6, 45),
        ("athlete-001", "2930-0", 50.2, "%", "normal", 38.3, 48.6, 28),
        ("athlete-001", "2930-0", 52.1, "%", "high", 38.3, 48.6, 3),
        ("athlete-001", "789-8", 5.2, "M/uL", "normal", 4.14, 5.8, 45),
        ("athlete-001", "789-8", 5.6, "M/uL", "normal", 4.14, 5.8, 28),
        ("athlete-001", "789-8", 5.9, "M/uL", "high", 4.14, 5.8, 3),
        ("athlete-001", "2093-3", 220, "mg/dL", "high", 0, 200, 28),
        ("athlete-001", "2571-8", 165, "mg/dL", "high", 0, 150, 28),
        ("athlete-001", "1742-6", 38, "U/L", "normal", 7, 56, 28),
        ("athlete-003", "1742-6", 32, "U/L", "normal", 7, 56, 45),
        ("athlete-003", "1742-6", 74, "U/L", "high", 7, 56, 5),
        ("athlete-003", "1920-8", 28, "U/L", "normal", 10, 40, 45),
        ("athlete-003", "1920-8", 52, "U/L", "high", 10, 40, 5),
        ("athlete-003", "2093-3", 195, "mg/dL", "normal", 0, 200, 5),
        ("athlete-003", "2085-9", 38, "mg/dL", "low", 40, 60, 5),
        ("athlete-004", "2093-3", 235, "mg/dL", "high", 0, 200, 14),
        ("athlete-004", "2085-9", 29, "mg/dL", "low", 40, 60, 14),
        ("athlete-004", "2571-8", 180, "mg/dL", "high", 0, 150, 14),
        ("athlete-004", "2823-3", 4.2, "mEq/L", "normal", 3.5, 5.0, 14),
        ("athlete-004", "2160-0", 1.1, "mg/dL", "normal", 0.7, 1.3, 14),
    ]
    for uid, loinc, val, unit, flag, ref_l, ref_h, days_ago in labs:
        conn.execute(
            "INSERT INTO metric_observation (user_id, metric_loinc, value_canonical, unit_canonical, observation_date, flag, reference_low, reference_high) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, loinc, val, unit, _date(days_ago), flag, ref_l, ref_h))


def _seed_compounds(conn):
    COMPOUND_MAP = {
        "Testosterone Cypionate": "test_cyp", "Testosterone Enanthate": "test_e",
        "Testosterone Propionate": "test_prop", "Equipoise": "eq",
        "Trenbolone Acetate": "tren_a", "Anavar": "anavar",
        "Anastrozole": "anastrozole",
    }
    events = {
        "athlete-001": [("Testosterone Cypionate", "START", 500, "e3.5d", "IM", 28), ("Equipoise", "START", 400, "e3.5d", "IM", 28), ("Anastrozole", "START", 0.5, "e3.5d", "oral", 28)],
        "athlete-002": [("Testosterone Enanthate", "START", 300, "e3.5d", "IM", 42), ("Trenbolone Acetate", "START", 200, "eod", "IM", 42)],
        "athlete-003": [("Testosterone Cypionate", "START", 150, "e3.5d", "IM", 90), ("Anavar", "START", 50, "daily", "oral", 21)],
        "athlete-004": [("Testosterone Cypionate", "START", 200, "e3.5d", "IM", 120), ("Testosterone Cypionate", "STOP", None, None, None, 12)],
        "athlete-005": [("Testosterone Propionate", "START", 50, "eod", "IM", 65), ("Anavar", "START", 10, "daily", "oral", 65)],
        "athlete-006": [],
    }
    for uid, evts in events.items():
        for name, evt_type, dose, freq, route, days_ago in evts:
            cid = COMPOUND_MAP.get(name, name.lower().replace(" ", "_"))
            conn.execute(
                "INSERT INTO compound_event (user_id, compound_id, event_type, dose_mg, frequency, route, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, cid, evt_type, dose, freq, route, _ts(days_ago)))

    active_levels = {
        "athlete-001": [("test_cyp", 0.85, 425, True), ("eq", 0.62, 248, False)],
        "athlete-002": [("test_e", 0.92, 276, True), ("tren_a", 0.78, 156, True)],
        "athlete-003": [("test_cyp", 0.95, 143, True), ("anavar", 0.88, 44, True)],
        "athlete-004": [("test_cyp", 0.12, 24, False)],
        "athlete-005": [("test_prop", 0.65, 33, True), ("anavar", 0.90, 9, True)],
    }
    for uid, levels in active_levels.items():
        for cid, level, dose_mg, steady in levels:
            for day in range(14):
                decay = 1.0 if steady else max(0.05, level - day * 0.02)
                est = round(level * decay + random.uniform(-0.03, 0.03), 3)
                conn.execute(
                    "INSERT OR IGNORE INTO drug_level (user_id, compound_id, observation_date, estimated_level, dose_active_mg, days_since_start, at_steady_state) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (uid, cid, _date(13 - day), est, dose_mg, 28 + day if steady else day, 1 if steady else 0))


def _seed_findings(conn):
    findings = [
        {"user_id": "athlete-001", "detector_id": "hematological_drift", "severity": "concerning",
         "summary": "HCT has risen from 48.0% to 52.1% over 6 weeks. RBC trending in parallel (5.2->5.9 M/uL). Currently above reference range (48.6%). Correlates with blast phase week 4.",
         "detail": json.dumps({"headline": "Hematocrit trending above range", "theme": "hematological",
            "signals": [{"label": "Hematocrit", "value": "52.1%", "direction": "up", "delta": "+4.1% over 6wk"},
                        {"label": "RBC", "value": "5.9 M/uL", "direction": "up", "delta": "+0.7 over 6wk"},
                        {"label": "Phase", "value": "Blast day 28", "direction": "flat", "delta": ""}]}),
         "detected_at": _ts(1), "status": "active", "tw_start": _date(45), "tw_end": _date(3)},
        {"user_id": "athlete-002", "detector_id": "cardiovascular_drift", "severity": "concerning",
         "summary": "Resting HR increased from 56 to 65 bpm over 14 days while recovery declined from 70% to 45%. HRV (RMSSD) trending down. Cross-metric cardiovascular stress pattern.",
         "detail": json.dumps({"headline": "Resting HR rising with declining recovery", "theme": "cardiovascular",
            "signals": [{"label": "Resting HR", "value": "65 bpm", "direction": "up", "delta": "+9 bpm / 14d"},
                        {"label": "Recovery", "value": "45%", "direction": "down", "delta": "-25% / 14d"},
                        {"label": "HRV (RMSSD)", "value": "52 ms", "direction": "down", "delta": "-13 ms / 14d"}]}),
         "detected_at": _ts(0), "status": "active", "tw_start": _date(14), "tw_end": _date(0)},
        {"user_id": "athlete-003", "detector_id": "hepatic_response", "severity": "notable",
         "summary": "ALT risen from 32 to 74 U/L (2.3x baseline) at 3 weeks into Anavar. AST also elevated (28->52). Expected hepatic response to 17-alpha-alkylated orals.",
         "detail": json.dumps({"headline": "ALT elevated — time-locked to oral compound start", "theme": "hepatic",
            "signals": [{"label": "ALT", "value": "74 U/L", "direction": "up", "delta": "2.3x baseline"},
                        {"label": "AST", "value": "52 U/L", "direction": "up", "delta": "1.9x baseline"},
                        {"label": "Compound", "value": "Anavar 50mg ED", "direction": "flat", "delta": "day 21"}]}),
         "detected_at": _ts(2), "status": "active", "tw_start": _date(45), "tw_end": _date(5)},
        {"user_id": "athlete-004", "detector_id": "lipid_recovery", "severity": "notable",
         "summary": "HDL remains low (29 mg/dL, ref >40) and total cholesterol elevated (235 mg/dL) at 12 days post-cessation. Lipid recovery typically takes 4-8 weeks.",
         "detail": json.dumps({"headline": "Lipids suppressed post-cycle — expected recovery timeline", "theme": "cardiovascular",
            "signals": [{"label": "HDL", "value": "29 mg/dL", "direction": "down", "delta": "below ref"},
                        {"label": "Total Chol", "value": "235 mg/dL", "direction": "up", "delta": "above ref"},
                        {"label": "HRV trend", "value": "improving", "direction": "up", "delta": "+15 ms / 12d"}]}),
         "detected_at": _ts(3), "status": "active", "tw_start": _date(14), "tw_end": _date(0)},
        {"user_id": "athlete-005", "detector_id": "metabolic_adaptation", "severity": "info",
         "summary": "Weight stalled at 58.8 kg despite macro adherence. NEAT likely declining at prep week 9+. Recovery trending down. Expected prep wall.",
         "detail": json.dumps({"headline": "Weight loss plateau — metabolic adaptation at prep week 9", "theme": "metabolic",
            "signals": [{"label": "Weight", "value": "58.8 kg", "direction": "flat", "delta": "-0.1 kg / 7d"},
                        {"label": "Recovery", "value": "52%", "direction": "down", "delta": "-13% / 14d"},
                        {"label": "Phase", "value": "Prep day 65", "direction": "flat", "delta": ""}]}),
         "detected_at": _ts(1), "status": "active", "tw_start": _date(14), "tw_end": _date(0)},
        {"user_id": "athlete-006", "detector_id": "metabolic_glucose", "severity": "info",
         "summary": "CGM data shows increased glucose variability (CV up from 12% to 19%) in 2 weeks since ending caloric deficit. Typical metabolic readaptation.",
         "detail": json.dumps({"headline": "Glucose variability increased post-diet", "theme": "metabolic",
            "signals": [{"label": "Glucose CV", "value": "19%", "direction": "up", "delta": "+7% / 14d"},
                        {"label": "Avg glucose", "value": "94 mg/dL", "direction": "flat", "delta": ""},
                        {"label": "Phase", "value": "Offseason day 45", "direction": "flat", "delta": ""}]}),
         "detected_at": _ts(4), "status": "active", "tw_start": _date(14), "tw_end": _date(0)},
    ]
    for f in findings:
        conn.execute(
            "INSERT INTO finding (user_id, detector_id, severity, summary, detail, detected_at, status, time_window_start, time_window_end) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f["user_id"], f["detector_id"], f["severity"], f["summary"], f["detail"], f["detected_at"], f["status"], f["tw_start"], f["tw_end"]))


def _seed_training(conn):
    blocks = [
        ("athlete-001", "Upper/Lower Hypertrophy", "hypertrophy", 28, None, "4-day split, progressive overload focus"),
        ("athlete-002", "Push/Pull/Legs Volume", "hypertrophy", 42, None, "6-day PPL, high volume phase"),
        ("athlete-003", "Maintenance Block", "hypertrophy", 18, None, "4-day upper/lower, cruise volume"),
        ("athlete-004", "Recovery Transition", "deload", 12, None, "3-day full body, reduced volume post-cycle"),
        ("athlete-005", "Prep Training Block C", "prep", 65, None, "5-day bro split, refeed day Saturday"),
        ("athlete-006", "Offseason Strength", "strength", 45, None, "4-day upper/lower, strength focus"),
    ]
    for athlete_id, name, btype, days_ago, end, notes in blocks:
        conn.execute(
            "INSERT INTO training_block (id, athlete_id, coach_id, name, block_type, start_date, end_date, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')",
            (str(uuid.uuid4()), athlete_id, COACH_ID, name, btype, _date(days_ago), end, notes))


def _seed_nutrition(conn):
    targets = [
        ("athlete-001", 3800, 280, 420, 100, "Surplus, high carb training days"),
        ("athlete-002", 3400, 260, 380, 85, "Moderate surplus, even split"),
        ("athlete-003", 2800, 210, 310, 75, "Cruise maintenance"),
        ("athlete-004", 2600, 200, 280, 72, "Slight deficit during recovery"),
        ("athlete-005", 1650, 155, 130, 55, "Contest prep, low carb non-refeed"),
        ("athlete-006", 2400, 145, 280, 72, "Reverse diet week 3"),
    ]
    for athlete_id, cal, pro, carb, fat, notes in targets:
        conn.execute(
            "INSERT INTO nutrition_target (id, athlete_id, coach_id, calories, protein_g, carbs_g, fat_g, notes, effective_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), athlete_id, COACH_ID, cal, pro, carb, fat, notes, _date(7)))


def _seed_recovery(conn):
    notes = [
        ("athlete-001", "note", "Monitor BP — weight up, compounds active. Next draw in 2 weeks.", 5),
        ("athlete-002", "rest_day", "Added extra rest day Wednesday due to recovery scores.", 3),
        ("athlete-002", "note", "Client reports poor sleep quality — investigate stress/stimulant use.", 1),
        ("athlete-003", "note", "Liver values expected to bump with oral — recheck at 6 weeks.", 4),
        ("athlete-004", "deload", "Full deload this week, reduced to 3x training frequency.", 7),
        ("athlete-005", "note", "Prep wall approaching — may need refeed adjustment.", 2),
        ("athlete-005", "sleep", "Sleep quality declining, recommend 9hr target.", 1),
        ("athlete-006", "active_recovery", "Added 2x LISS sessions for metabolic flexibility.", 6),
    ]
    for athlete_id, ntype, content, days_ago in notes:
        conn.execute(
            "INSERT INTO recovery_note (id, athlete_id, coach_id, note_type, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), athlete_id, COACH_ID, ntype, content, _ts(days_ago)))
