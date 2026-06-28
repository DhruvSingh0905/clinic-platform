"""Incremental detector triggers.

After any data write (bloodwork, wearable sync, compound change, daily entry),
run relevant detectors and update findings. This is the "nervous system" —
data arrives, system reacts.

Usage:
    from clinic.triggers import on_data_changed
    on_data_changed(conn, "bloodwork")  # after uploading labs
    on_data_changed(conn, "wearable")   # after Apple Health / Whoop sync
    on_data_changed(conn, "compound")   # after compound add/stop/change
    on_data_changed(conn, "daily")      # after manual daily entry
"""

from __future__ import annotations

import sqlite3
from datetime import date

from clinic.detectors.themes import run_all_detectors


# Which detectors to run based on what data changed
TRIGGER_MAP = {
    "bloodwork": [
        "cv_stress",          # hematocrit, lipids, hemoglobin
        "hepatic_load",       # ALT, AST, GGT, bilirubin
        "hormonal_balance",   # E2, T:E2 ratio, prolactin, SHBG
        "metabolic_health",   # glucose, insulin, A1c
        "renal_function",     # creatinine, BUN, eGFR
        "hematological",      # full CBC
        "inflammation_vascular",  # CRP, homocysteine, ApoB
        "recovery_hpta",      # LH, FSH, T recovery
    ],
    "wearable": [
        "cv_stress",          # resting HR, HRV, BP trends
    ],
    "compound": [
        "cv_stress",          # compound changes affect CV risk
        "hepatic_load",       # 17aa oral starts
        "hormonal_balance",   # AI/SERM changes
    ],
    "daily": [
        "cv_stress",          # BP manual entry
        "metabolic_health",   # blood glucose manual entry
    ],
}


def on_data_changed(
    conn: sqlite3.Connection,
    data_type: str,
    user_id: str = "default",
) -> list[dict]:
    """Run relevant detectors after a data change.

    Args:
        conn: Database connection
        data_type: What changed — "bloodwork", "wearable", "compound", "daily"
        user_id: User whose data changed

    Returns:
        List of new findings created (may be empty if nothing flagged)
    """
    as_of = date.today().isoformat()

    # Clear previous findings for detectors we're about to re-run
    # (prevents stale findings from accumulating)
    relevant_detectors = TRIGGER_MAP.get(data_type, [])
    if not relevant_detectors:
        return []

    # Mark old findings as resolved before re-running
    placeholders = ",".join("?" for _ in relevant_detectors)
    conn.execute(f"""
        UPDATE finding SET status = 'resolved'
        WHERE user_id = ? AND detector_id IN ({placeholders}) AND status IN ('active', 'viewed')
    """, [user_id] + relevant_detectors)
    conn.commit()

    # Run all detectors (they check their own data availability)
    findings = run_all_detectors(conn, user_id=user_id, as_of=as_of)

    return [{"id": f.detector_id, "severity": f.severity.value, "headline": f.headline} for f in findings]
