"""Coach Platform API — FastAPI backend.

Multi-tenant read layer for coaches, self-logging for athletes.
The substance boundary is enforced here: no coach endpoint writes substance data.

CDE-compatible tables use `user_id` (= athlete.id).
Coach Platform tables use `athlete_id` / `coach_id`.
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
import tempfile
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, date

from coach.database import get_db, init_db
from coach.config import SEED_MOCK
from coach.operations import (
    SetTrainingBlock, EndTrainingBlock, SetNutritionTarget,
    AddRecoveryNote, UserLogSubstanceEvent,
    commit_operation,
)


DETECTOR_THEMES = {
    "cv_stress": "cardiovascular", "cardiovascular_drift": "cardiovascular",
    "hepatic_load": "hepatic", "hepatic_response": "hepatic",
    "hormonal_balance": "hormonal", "metabolic_health": "metabolic",
    "metabolic_adaptation": "metabolic", "metabolic_glucose": "metabolic",
    "renal_function": "renal", "hematological": "hematological",
    "hematological_drift": "hematological", "inflammation_vascular": "inflammation",
    "recovery_hpta": "recovery", "lipid_recovery": "cardiovascular",
}

def _parse_finding(f) -> dict:
    """Parse a finding row — handles both mock (headline in detail) and real detector output."""
    detail = {}
    if f["detail"]:
        try:
            detail = json.loads(f["detail"])
        except (json.JSONDecodeError, TypeError):
            pass

    # Theme: from detail JSON, or from detector_id mapping
    theme = detail.get("theme", DETECTOR_THEMES.get(f["detector_id"], f["detector_id"].replace("_", " ")))

    # Headline: from detail JSON, or from summary (first sentence)
    headline = detail.get("headline", f["summary"].split(".")[0] if f["summary"] else f["detector_id"])

    # Signals: handle both mock format and real detector format
    raw_signals = detail.get("signals", [])
    signals = []
    for sig in raw_signals:
        if "label" in sig:
            # Mock format: {label, value, direction, delta}
            signals.append(sig)
        elif "metric" in sig:
            # Real detector format: {metric, description, current, baseline, change, trend}
            direction = {"rising": "up", "falling": "down", "stable": "flat"}.get(sig.get("trend", ""), "flat")
            delta = ""
            if sig.get("change") is not None and sig.get("baseline"):
                pct = abs(sig["change"] / sig["baseline"] * 100) if sig["baseline"] else 0
                delta = f"{'+' if sig['change'] > 0 else ''}{sig['change']:.1f} ({pct:.0f}%)"
            signals.append({
                "label": sig.get("metric", ""),
                "value": f"{sig.get('current', '')}" if sig.get("current") is not None else "",
                "direction": direction,
                "delta": delta,
            })

    return {
        "id": f["id"],
        "detector_id": f["detector_id"],
        "severity": f["severity"],
        "headline": headline,
        "theme": theme,
        "summary": f["summary"],
        "signals": signals,
        "detected_at": f["detected_at"],
        "status": f["status"],
        "time_window_start": f["time_window_start"],
        "time_window_end": f["time_window_end"],
    }


def _day_in_phase(started_at: str | None) -> int:
    if not started_at:
        return 0
    try:
        start = datetime.fromisoformat(started_at)
        return (datetime.now() - start).days
    except (ValueError, TypeError):
        return 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_db()
    init_db(conn)
    from coach.loaders import seed_metric_definitions, seed_compound_definitions
    seed_metric_definitions(conn)
    seed_compound_definitions(conn)
    # Ensure LOINC codes used in mock data have display names
    _extra_loinc = [
        ("2930-0", "Hematocrit", "%", "hematology"),
        ("789-8", "RBC", "M/uL", "hematology"),
        ("2093-3", "Total Cholesterol", "mg/dL", "lipids"),
        ("2571-8", "Triglycerides", "mg/dL", "lipids"),
        ("1742-6", "ALT", "U/L", "liver"),
        ("1920-8", "AST", "U/L", "liver"),
        ("2085-9", "HDL", "mg/dL", "lipids"),
        ("2823-3", "Potassium", "mEq/L", "kidney"),
        ("2160-0", "Creatinine", "mg/dL", "kidney"),
        ("2345-7", "Blood Glucose", "mg/dL", "metabolic"),
    ]
    for loinc, name, unit, cat in _extra_loinc:
        conn.execute("INSERT OR IGNORE INTO metric_definition (loinc_code, canonical_name, canonical_unit, category) VALUES (?, ?, ?, ?)",
                     (loinc, name, unit, cat))
    conn.commit()
    if SEED_MOCK:
        count = conn.execute("SELECT COUNT(*) FROM coach").fetchone()[0]
        if count == 0:
            from coach.mock_data import seed_mock_data
            seed_mock_data(conn)
        # Seed mock workout data if not yet present
        wcount = conn.execute("SELECT COUNT(*) FROM workout_session").fetchone()[0]
        if wcount == 0:
            from coach.hevy import seed_mock_workouts, detect_training_stall
            for aid in ["athlete-001", "athlete-002", "athlete-003"]:
                seed_mock_workouts(conn, aid)
                detect_training_stall(conn, aid)
    conn.close()
    yield


app = FastAPI(title="Coach Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3847"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Coach Roster ──

@app.get("/api/coach/{coach_id}/roster")
def get_roster(coach_id: str):
    conn = get_db()
    try:
        athletes = conn.execute("""
            SELECT a.id, a.name, a.email, a.avatar_color, ca.added_at
            FROM athlete a JOIN coach_athlete ca ON a.id = ca.athlete_id
            WHERE ca.coach_id = ? AND ca.status = 'active'
        """, (coach_id,)).fetchall()

        severity_order = {"concerning": 0, "notable": 1, "info": 2}
        roster = []

        for athlete in athletes:
            aid = athlete["id"]

            integrations = [r["provider"] for r in conn.execute(
                "SELECT provider FROM integration_status WHERE athlete_id = ? AND status = 'connected'", (aid,)
            ).fetchall()]

            last_sync = conn.execute(
                "SELECT MAX(last_sync) as ls FROM integration_status WHERE athlete_id = ?", (aid,)
            ).fetchone()

            phase_row = conn.execute(
                "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1", (aid,)
            ).fetchone()

            phase = phase_row["phase"] if phase_row else "unknown"
            day = _day_in_phase(phase_row["started_at"] if phase_row else None)

            # Findings (CDE table — user_id)
            findings = conn.execute(
                "SELECT * FROM finding WHERE user_id = ? AND status = 'active' ORDER BY detected_at DESC", (aid,)
            ).fetchall()

            top_finding = None
            if findings:
                best = sorted(findings, key=lambda f: severity_order.get(f["severity"], 3))[0]
                top_finding = _parse_finding(best)

            roster.append({
                "athlete": {
                    "id": aid, "name": athlete["name"], "email": athlete["email"],
                    "avatar_color": athlete["avatar_color"], "connected_at": athlete["added_at"],
                    "last_sync": last_sync["ls"] if last_sync else None, "integrations": integrations,
                },
                "top_finding": top_finding,
                "finding_count": len(findings),
                "phase": phase,
                "day_in_phase": day,
            })

        roster.sort(key=lambda r: severity_order.get(
            r["top_finding"]["severity"] if r["top_finding"] else "info", 3))
        return {"roster": roster, "coach_id": coach_id}
    finally:
        conn.close()


# ── Client Detail ──

@app.get("/api/coach/{coach_id}/client/{athlete_id}")
def get_client_detail(coach_id: str, athlete_id: str):
    conn = get_db()
    try:
        rel = conn.execute(
            "SELECT 1 FROM coach_athlete WHERE coach_id = ? AND athlete_id = ? AND status = 'active'",
            (coach_id, athlete_id)).fetchone()
        if not rel:
            raise HTTPException(status_code=403, detail="Not your client")

        athlete = conn.execute("SELECT * FROM athlete WHERE id = ?", (athlete_id,)).fetchone()
        if not athlete:
            raise HTTPException(status_code=404, detail="Athlete not found")

        phase_row = conn.execute(
            "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (athlete_id,)).fetchone()
        phase = phase_row["phase"] if phase_row else "unknown"
        day = _day_in_phase(phase_row["started_at"] if phase_row else None)

        integrations = [r["provider"] for r in conn.execute(
            "SELECT provider FROM integration_status WHERE athlete_id = ? AND status = 'connected'", (athlete_id,)
        ).fetchall()]
        last_sync = conn.execute(
            "SELECT MAX(last_sync) as ls FROM integration_status WHERE athlete_id = ?", (athlete_id,)
        ).fetchone()

        # Findings (CDE table) — severity-ranked, deduplicated by detector_id (keep latest)
        all_findings = conn.execute("""
            SELECT * FROM finding WHERE user_id = ?
            ORDER BY
                CASE severity WHEN 'concerning' THEN 0 WHEN 'notable' THEN 1 WHEN 'info' THEN 2 ELSE 3 END,
                detected_at DESC
        """, (athlete_id,)).fetchall()
        seen_detectors: set[str] = set()
        findings = []
        for f in all_findings:
            key = f["detector_id"]
            if key not in seen_detectors:
                seen_detectors.add(key)
                findings.append(_parse_finding(f))

        # Wearables (CDE table — user_id)
        wearables = [dict(w) for w in conn.execute("""
            SELECT metric, observation_date, value_mean, unit, source, methodology
            FROM wearable_observation WHERE user_id = ?
            ORDER BY observation_date DESC LIMIT 200
        """, (athlete_id,)).fetchall()]

        # Labs (CDE table — user_id). Join metric_definition for canonical_name.
        labs = []
        for l in conn.execute("""
            SELECT mo.metric_loinc, COALESCE(md.canonical_name, mo.metric_loinc) as metric_name,
                   mo.value_canonical, mo.unit_canonical, mo.observation_date, mo.flag,
                   mo.reference_low, mo.reference_high, COALESCE(md.category, 'unknown') as category
            FROM metric_observation mo
            LEFT JOIN metric_definition md ON mo.metric_loinc = md.loinc_code
            WHERE mo.user_id = ?
            ORDER BY mo.observation_date DESC
        """, (athlete_id,)).fetchall():
            labs.append(dict(l))

        # Substance events (CDE table — user_id, compound_id). Join compound_definition for names.
        substance_events = []
        for s in conn.execute("""
            SELECT COALESCE(cd.canonical_name, ce.compound_id) as compound_name,
                   COALESCE(cd.compound_class, 'unknown') as compound_class,
                   ce.event_type, ce.dose_mg, ce.frequency, ce.route, ce.timestamp
            FROM compound_event ce
            LEFT JOIN compound_definition cd ON ce.compound_id = cd.id
            WHERE ce.user_id = ?
            ORDER BY ce.timestamp DESC
        """, (athlete_id,)).fetchall():
            substance_events.append(dict(s))

        # Drug levels (CDE table — user_id, compound_id, estimated_level)
        drug_levels = []
        for d in conn.execute("""
            SELECT COALESCE(cd.canonical_name, dl.compound_id) as compound_name,
                   COALESCE(cd.compound_class, 'unknown') as compound_class,
                   dl.estimated_level as level, dl.dose_active_mg, dl.at_steady_state, dl.observation_date
            FROM drug_level dl
            LEFT JOIN compound_definition cd ON dl.compound_id = cd.id
            WHERE dl.user_id = ?
            ORDER BY dl.observation_date DESC LIMIT 50
        """, (athlete_id,)).fetchall():
            drug_levels.append(dict(d))

        # Training (Coach Platform table — athlete_id)
        training = [dict(t) for t in conn.execute("""
            SELECT id, name, block_type, start_date, end_date, notes, status
            FROM training_block WHERE athlete_id = ? ORDER BY start_date DESC
        """, (athlete_id,)).fetchall()]

        # Nutrition (Coach Platform table — athlete_id)
        nutrition = [dict(n) for n in conn.execute("""
            SELECT id, calories, protein_g, carbs_g, fat_g, notes, effective_date
            FROM nutrition_target WHERE athlete_id = ? ORDER BY effective_date DESC
        """, (athlete_id,)).fetchall()]

        # Recovery (Coach Platform table — athlete_id)
        recovery = [dict(r) for r in conn.execute("""
            SELECT id, note_type, content, created_at
            FROM recovery_note WHERE athlete_id = ? ORDER BY created_at DESC
        """, (athlete_id,)).fetchall()]

        return {
            "athlete": {
                "id": athlete["id"], "name": athlete["name"], "email": athlete["email"],
                "avatar_color": athlete["avatar_color"],
                "last_sync": last_sync["ls"] if last_sync else None, "integrations": integrations,
            },
            "phase": phase, "day_in_phase": day,
            "phase_started_at": phase_row["started_at"] if phase_row else None,
            "findings": findings, "wearables": wearables, "labs": labs,
            "substance_events": substance_events, "drug_levels": drug_levels,
            "training": training, "nutrition": nutrition, "recovery": recovery,
        }
    finally:
        conn.close()


# ── Coaching Surface (write operations) ──

class TrainingBlockRequest(BaseModel):
    name: str
    block_type: str
    start_date: str
    end_date: Optional[str] = None
    notes: Optional[str] = None

class EndTrainingBlockRequest(BaseModel):
    block_id: str
    end_date: str

class NutritionTargetRequest(BaseModel):
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    effective_date: str
    notes: Optional[str] = None

class RecoveryNoteRequest(BaseModel):
    note_type: str
    content: str

class SubstanceEventRequest(BaseModel):
    compound_name: str
    compound_class: str
    event_type: str
    dose_mg: Optional[float] = None
    frequency: Optional[str] = None
    route: Optional[str] = None


@app.post("/api/coach/{coach_id}/client/{athlete_id}/training")
def set_training_block(coach_id: str, athlete_id: str, req: TrainingBlockRequest):
    conn = get_db()
    try:
        op = SetTrainingBlock(athlete_id=athlete_id, name=req.name, block_type=req.block_type,
                              start_date=req.start_date, end_date=req.end_date, notes=req.notes)
        result = commit_operation(conn, coach_id, "coach", op)
        from coach.hevy import create_notification
        create_notification(conn, athlete_id, coach_id, "coach", "training_updated",
                            f"Your coach set a new training block: {req.name}", result["rendered"], None)
        return {"status": "committed", **result}
    finally:
        conn.close()

@app.post("/api/coach/{coach_id}/client/{athlete_id}/training/end")
def end_training_block(coach_id: str, athlete_id: str, req: EndTrainingBlockRequest):
    conn = get_db()
    try:
        op = EndTrainingBlock(athlete_id=athlete_id, block_id=req.block_id, end_date=req.end_date)
        result = commit_operation(conn, coach_id, "coach", op)
        return {"status": "committed", **result}
    finally:
        conn.close()

@app.post("/api/coach/{coach_id}/client/{athlete_id}/nutrition")
def set_nutrition_target(coach_id: str, athlete_id: str, req: NutritionTargetRequest):
    conn = get_db()
    try:
        op = SetNutritionTarget(athlete_id=athlete_id, calories=req.calories, protein_g=req.protein_g,
                                carbs_g=req.carbs_g, fat_g=req.fat_g, effective_date=req.effective_date, notes=req.notes)
        result = commit_operation(conn, coach_id, "coach", op)
        from coach.hevy import create_notification
        create_notification(conn, athlete_id, coach_id, "coach", "nutrition_updated",
                            f"Your coach updated your nutrition targets", result["rendered"], None)
        return {"status": "committed", **result}
    finally:
        conn.close()

@app.post("/api/coach/{coach_id}/client/{athlete_id}/recovery")
def add_recovery_note(coach_id: str, athlete_id: str, req: RecoveryNoteRequest):
    conn = get_db()
    try:
        op = AddRecoveryNote(athlete_id=athlete_id, note_type=req.note_type, content=req.content)
        result = commit_operation(conn, coach_id, "coach", op)
        from coach.hevy import create_notification
        create_notification(conn, athlete_id, coach_id, "coach", "recovery_note",
                            f"Your coach added a note: {req.content[:50]}", result["rendered"], None)
        return {"status": "committed", **result}
    finally:
        conn.close()


# ── Athlete endpoints ──

@app.get("/api/athlete/{athlete_id}/dashboard")
def get_athlete_dashboard(athlete_id: str):
    conn = get_db()
    try:
        athlete = conn.execute("SELECT * FROM athlete WHERE id = ?", (athlete_id,)).fetchone()
        if not athlete:
            raise HTTPException(status_code=404, detail="Athlete not found")

        phase_row = conn.execute(
            "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (athlete_id,)).fetchone()
        phase = phase_row["phase"] if phase_row else "unknown"
        day = _day_in_phase(phase_row["started_at"] if phase_row else None)

        wearables = [dict(w) for w in conn.execute("""
            SELECT metric, observation_date, value_mean, unit, source
            FROM wearable_observation WHERE user_id = ? ORDER BY observation_date DESC LIMIT 60
        """, (athlete_id,)).fetchall()]

        # Drug levels (latest date, joined with compound_definition for display names)
        drug_levels_raw = conn.execute("""
            SELECT COALESCE(cd.canonical_name, dl.compound_id) as compound_name,
                   COALESCE(cd.compound_class, 'unknown') as compound_class,
                   dl.estimated_level as level, dl.dose_active_mg, dl.at_steady_state, dl.observation_date
            FROM drug_level dl
            LEFT JOIN compound_definition cd ON dl.compound_id = cd.id
            WHERE dl.user_id = ? AND dl.observation_date = (
                SELECT MAX(observation_date) FROM drug_level WHERE user_id = ?
            )
        """, (athlete_id, athlete_id)).fetchall()
        drug_levels = [{**dict(d), "at_steady_state": bool(d["at_steady_state"])} for d in drug_levels_raw]

        findings = [_parse_finding(f) for f in conn.execute("""
            SELECT * FROM finding WHERE user_id = ? AND status = 'active'
            ORDER BY
                CASE severity WHEN 'concerning' THEN 0 WHEN 'notable' THEN 1 WHEN 'info' THEN 2 ELSE 3 END,
                detected_at DESC
        """, (athlete_id,)).fetchall()]

        integrations = [dict(i) for i in conn.execute(
            "SELECT provider, status, last_sync FROM integration_status WHERE athlete_id = ?",
            (athlete_id,)).fetchall()]

        # Coach-managed data visible to athlete (the two-sided loop)
        training = [dict(t) for t in conn.execute("""
            SELECT id, name, block_type, start_date, end_date, notes, status
            FROM training_block WHERE athlete_id = ? ORDER BY start_date DESC
        """, (athlete_id,)).fetchall()]

        nutrition = [dict(n) for n in conn.execute("""
            SELECT id, calories, protein_g, carbs_g, fat_g, notes, effective_date
            FROM nutrition_target WHERE athlete_id = ? ORDER BY effective_date DESC
        """, (athlete_id,)).fetchall()]

        recovery = [dict(r) for r in conn.execute("""
            SELECT id, note_type, content, created_at
            FROM recovery_note WHERE athlete_id = ? ORDER BY created_at DESC
        """, (athlete_id,)).fetchall()]

        return {
            "athlete": {"id": athlete["id"], "name": athlete["name"], "avatar_color": athlete["avatar_color"]},
            "phase": phase, "day_in_phase": day,
            "wearables": wearables, "drug_levels": drug_levels,
            "findings": findings, "integrations": integrations,
            "training": training, "nutrition": nutrition, "recovery": recovery,
        }
    finally:
        conn.close()


@app.post("/api/athlete/{athlete_id}/substance")
def log_substance_event(athlete_id: str, req: SubstanceEventRequest):
    """User self-logs a substance event. ATHLETE-ONLY, coach cannot invoke."""
    conn = get_db()
    try:
        op = UserLogSubstanceEvent(
            athlete_id=athlete_id, compound_name=req.compound_name,
            compound_class=req.compound_class, event_type=req.event_type,
            dose_mg=req.dose_mg, frequency=req.frequency, route=req.route,
        )
        result = commit_operation(conn, athlete_id, "athlete", op)
        # Trigger PK regeneration + detectors
        try:
            from coach.ingest import after_compound_change
            findings = after_compound_change(conn, athlete_id)
            result["new_findings"] = len(findings)
        except Exception:
            result["new_findings"] = 0
        return {"status": "committed", **result}
    finally:
        conn.close()


# Coach CAN now modify substances. Athlete gets notified and must confirm.
@app.post("/api/coach/{coach_id}/client/{athlete_id}/substance")
def coach_modify_substance(coach_id: str, athlete_id: str, req: SubstanceEventRequest):
    """Coach modifies athlete's substance protocol. Athlete is notified."""
    conn = get_db()
    try:
        # Look up compound_id
        cid_row = conn.execute(
            "SELECT id FROM compound_definition WHERE canonical_name = ? OR id = ? OR LOWER(canonical_name) = LOWER(?)",
            (req.compound_name, req.compound_name.lower().replace(" ", "_"), req.compound_name)
        ).fetchone()
        if not cid_row:
            try:
                from coach.compound_db import COMPOUNDS
                for cid, comp in COMPOUNDS.items():
                    if req.compound_name.lower() in [a.lower() for a in comp.aliases] or req.compound_name.lower() == comp.canonical_name.lower():
                        cid_row = {"id": cid}
                        break
            except ImportError:
                pass
        compound_id = cid_row["id"] if cid_row else req.compound_name.lower().replace(" ", "_")

        from datetime import datetime as dt
        conn.execute(
            "INSERT INTO compound_event (user_id, compound_id, event_type, dose_mg, frequency, route, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (athlete_id, compound_id, req.event_type, req.dose_mg, req.frequency, req.route, dt.now().isoformat())
        )

        # Log operation
        rendered = f"Coach {req.event_type.lower()} {req.compound_name}"
        if req.dose_mg:
            rendered += f" {req.dose_mg}mg"
        if req.frequency:
            rendered += f" {req.frequency}"
        conn.execute(
            "INSERT INTO operation_log (actor_id, actor_role, operation_type, payload_json, rendered_text) VALUES (?, 'coach', 'CoachSubstanceModification', ?, ?)",
            (coach_id, json.dumps({"compound": req.compound_name, "event_type": req.event_type, "dose_mg": req.dose_mg, "frequency": req.frequency, "route": req.route}), rendered)
        )

        # Notify athlete
        from coach.hevy import create_notification
        create_notification(conn, athlete_id, coach_id, "coach",
                            "substance_modified",
                            f"Your coach modified your protocol: {rendered}",
                            f"{rendered}. Please review and confirm this change.",
                            json.dumps({"compound": req.compound_name, "event_type": req.event_type, "dose_mg": req.dose_mg}))

        conn.commit()

        # Trigger PK regeneration + detectors
        try:
            from coach.ingest import after_compound_change
            findings = after_compound_change(conn, athlete_id)
        except Exception:
            findings = []

        return {"status": "committed", "rendered": rendered, "new_findings": len(findings)}
    finally:
        conn.close()


# ── Ingestion endpoints ──

@app.post("/api/athlete/{athlete_id}/upload")
async def upload_bloodwork(athlete_id: str, file: UploadFile = File(...)):
    """Upload bloodwork PDF/image. Extract, validate, load, run detectors."""
    conn = get_db()
    try:
        suffix = os.path.splitext(file.filename or "upload.pdf")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            from coach.extraction.extractor import extract_bloodwork
            from coach.extraction.validator import validate_extraction
            from coach.loaders import load_bloodwork
            from coach.ingest import after_data_write

            extraction = extract_bloodwork(tmp_path)
            if extraction.document_rejected:
                return {"status": "rejected", "reason": extraction.rejection_reason}

            validated = validate_extraction(extraction)
            count = load_bloodwork(conn, validated, user_id=athlete_id)
            findings = after_data_write(conn, "bloodwork", athlete_id)

            return {
                "status": "success",
                "results_count": count,
                "draw_date": extraction.draw_date,
                "findings_count": len(findings),
            }
        finally:
            os.unlink(tmp_path)
    finally:
        conn.close()


@app.post("/api/athlete/{athlete_id}/import/apple-health")
async def import_apple_health(athlete_id: str, file: UploadFile = File(...)):
    """Import Apple Health export (ZIP or XML)."""
    conn = get_db()
    try:
        suffix = os.path.splitext(file.filename or "export.zip")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            from coach.apple_health import parse_apple_health_xml
            from coach.loaders import load_apple_health
            from coach.ingest import regenerate_drug_levels, after_data_write

            xml_path = tmp_path
            if tmp_path.endswith(".zip"):
                with zipfile.ZipFile(tmp_path) as zf:
                    xml_name = next((n for n in zf.namelist() if n.endswith("export.xml")), None)
                    if not xml_name:
                        return {"status": "error", "reason": "No export.xml found in ZIP"}
                    xml_path = zf.extract(xml_name, os.path.dirname(tmp_path))

            export = parse_apple_health_xml(xml_path)
            count = load_apple_health(conn, export, user_id=athlete_id)
            regenerate_drug_levels(conn, athlete_id)
            findings = after_data_write(conn, "wearable", athlete_id)

            return {
                "status": "success",
                "records": count,
                "days": len(set(d.date.isoformat() for d in export.daily)),
                "findings_count": len(findings),
            }
        finally:
            os.unlink(tmp_path)
    finally:
        conn.close()


class DailyEntryRequest(BaseModel):
    metric: str
    value: float
    value2: Optional[float] = None
    unit: Optional[str] = None
    entry_date: Optional[str] = None

@app.post("/api/athlete/{athlete_id}/daily")
def submit_daily_entry(athlete_id: str, req: DailyEntryRequest):
    """Submit a daily health entry (weight, BP, blood glucose)."""
    conn = get_db()
    try:
        target_date = req.entry_date or date.today().isoformat()
        from coach.ingest import after_data_write

        if req.metric == "weight":
            conn.execute(
                "INSERT OR REPLACE INTO wearable_observation (user_id, metric, observation_date, value_mean, unit, source) VALUES (?, 'weight_kg', ?, ?, 'kg', 'manual')",
                (athlete_id, target_date, req.value))
            conn.commit()
        elif req.metric == "bp" and req.value2:
            from coach.bp_entry import BPReading, validate_bp, classify_bp
            reading = BPReading(systolic=int(req.value), diastolic=int(req.value2))
            issues = validate_bp(reading)
            if issues:
                return {"status": "error", "issues": issues}
            classification = classify_bp(int(req.value), int(req.value2))
            conn.execute(
                "INSERT INTO bp_reading (user_id, systolic, diastolic, timestamp, classification) VALUES (?, ?, ?, ?, ?)",
                (athlete_id, int(req.value), int(req.value2), datetime.now().isoformat(), classification))
            conn.commit()
            findings = after_data_write(conn, "daily", athlete_id)
            return {"status": "ok", "date": target_date, "classification": classification, "findings_count": len(findings)}
        elif req.metric == "blood_glucose":
            flag = "high" if req.value > 125 else "normal"
            conn.execute(
                "INSERT INTO metric_observation (user_id, metric_loinc, value_canonical, unit_canonical, observation_date, flag) VALUES (?, '2345-7', ?, 'mg/dL', ?, ?)",
                (athlete_id, req.value, target_date, flag))
            conn.commit()
            findings = after_data_write(conn, "daily", athlete_id)
            return {"status": "ok", "date": target_date, "flag": flag, "findings_count": len(findings)}
        else:
            return {"status": "error", "reason": f"Unknown metric: {req.metric}"}

        findings = after_data_write(conn, "daily", athlete_id)
        return {"status": "ok", "date": target_date, "findings_count": len(findings)}
    finally:
        conn.close()


# ── Chat endpoints ──

class ChatRequest(BaseModel):
    message: str
    thread_type: str = "free"  # "free" or "finding"
    finding_id: Optional[str] = None
    history: Optional[list] = None

@app.post("/api/coach/{coach_id}/client/{athlete_id}/chat")
def coach_chat(coach_id: str, athlete_id: str, req: ChatRequest):
    """Coach investigates client data through LLM chat."""
    conn = get_db()
    try:
        from coach.chat import chat_coach
        response = chat_coach(
            conn, coach_id, athlete_id,
            message=req.message,
            finding_id=req.finding_id if req.thread_type == "finding" else None,
            history=req.history,
        )
        return {"response": response}
    except Exception as e:
        return {"response": f"Chat error: {str(e)}", "error": True}
    finally:
        conn.close()

@app.post("/api/athlete/{athlete_id}/chat")
def athlete_chat(athlete_id: str, req: ChatRequest):
    """Athlete interacts with their own data through LLM chat."""
    conn = get_db()
    try:
        from coach.chat import chat_athlete
        response = chat_athlete(
            conn, athlete_id,
            message=req.message,
            finding_id=req.finding_id if req.thread_type == "finding" else None,
            history=req.history,
        )
        return {"response": response}
    except Exception as e:
        return {"response": f"Chat error: {str(e)}", "error": True}
    finally:
        conn.close()


# ── Calendar endpoints ──

@app.get("/api/athlete/{athlete_id}/calendar/{target_date}")
def athlete_calendar_day(athlete_id: str, target_date: str):
    conn = get_db()
    try:
        from coach.calendar import get_calendar_day
        return get_calendar_day(conn, athlete_id, target_date)
    finally:
        conn.close()

@app.get("/api/athlete/{athlete_id}/calendar/range/{start}/{end}")
def athlete_calendar_range(athlete_id: str, start: str, end: str):
    conn = get_db()
    try:
        from coach.calendar import get_calendar_range
        return get_calendar_range(conn, athlete_id, start, end)
    finally:
        conn.close()

@app.get("/api/coach/{coach_id}/client/{athlete_id}/calendar/{target_date}")
def coach_client_calendar(coach_id: str, athlete_id: str, target_date: str):
    conn = get_db()
    try:
        rel = conn.execute("SELECT 1 FROM coach_athlete WHERE coach_id = ? AND athlete_id = ?", (coach_id, athlete_id)).fetchone()
        if not rel:
            raise HTTPException(status_code=403, detail="Not your client")
        from coach.calendar import get_calendar_day
        return get_calendar_day(conn, athlete_id, target_date)
    finally:
        conn.close()


# ── Hevy / Workout endpoints ──

@app.get("/api/coach/{coach_id}/client/{athlete_id}/workouts")
def get_client_workouts(coach_id: str, athlete_id: str, days: int = 14):
    """Coach views athlete's recent workouts — structured JSON."""
    conn = get_db()
    try:
        from coach.hevy import get_workout_history, get_training_summary
        from datetime import timedelta
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        sessions = conn.execute("""
            SELECT id, title, started_at, duration_seconds FROM workout_session
            WHERE user_id = ? AND started_at >= ? ORDER BY started_at DESC
        """, (athlete_id, cutoff)).fetchall()

        workouts = []
        for s in sessions:
            sets = conn.execute("""
                SELECT exercise_name, set_type, weight_kg, reps, rpe
                FROM workout_set WHERE session_id = ? AND set_type IN ('normal', 'failure')
                ORDER BY exercise_name, set_index
            """, (s['id'],)).fetchall()
            by_ex: dict[str, list] = {}
            for st in sets:
                by_ex.setdefault(st['exercise_name'], []).append({
                    "weight_kg": round(st['weight_kg'] * 2) / 2 if st['weight_kg'] else 0,
                    "reps": st['reps'] or 0,
                    "type": st['set_type'],
                })
            workouts.append({
                "id": s['id'],
                "title": s['title'],
                "date": s['started_at'][:10],
                "duration_min": (s['duration_seconds'] or 0) // 60,
                "exercises": [{"name": name, "sets": ex_sets} for name, ex_sets in by_ex.items()],
            })

        return {
            "workouts": workouts,
            "text_summary": get_training_summary(conn, athlete_id, days),
        }
    finally:
        conn.close()


@app.get("/api/coach/{coach_id}/client/{athlete_id}/lifts")
def get_client_lifts(coach_id: str, athlete_id: str, days: int = 28):
    """Structured lift progression data for frontend charts."""
    conn = get_db()
    try:
        from coach.hevy import get_structured_lifts
        return get_structured_lifts(conn, athlete_id, days)
    finally:
        conn.close()


@app.get("/api/coach/{coach_id}/client/{athlete_id}/lift/{exercise_name}")
def get_client_lift(coach_id: str, athlete_id: str, exercise_name: str, days: int = 28):
    """Coach views per-exercise progression."""
    conn = get_db()
    try:
        from coach.hevy import get_lift_progression
        return {"progression": get_lift_progression(conn, athlete_id, exercise_name, days)}
    finally:
        conn.close()


@app.get("/api/athlete/{athlete_id}/workouts")
def get_athlete_workouts(athlete_id: str, days: int = 14):
    """Athlete views their own workouts."""
    conn = get_db()
    try:
        from coach.hevy import get_workout_history, get_training_summary
        return {
            "workouts": get_workout_history(conn, athlete_id, days),
            "summary": get_training_summary(conn, athlete_id, days),
        }
    finally:
        conn.close()


class RoutinePushRequest(BaseModel):
    title: str
    exercises: list

@app.post("/api/coach/{coach_id}/client/{athlete_id}/routine")
def push_routine(coach_id: str, athlete_id: str, req: RoutinePushRequest):
    """Coach pushes a routine to athlete's Hevy."""
    conn = get_db()
    try:
        from coach.hevy import push_routine_to_hevy
        result = push_routine_to_hevy(conn, coach_id, athlete_id, req.title, req.exercises)
        return {"status": "pushed", **result}
    finally:
        conn.close()


class RoutineUpdateRequest(BaseModel):
    routine_push_id: int
    title: str
    exercises: list

@app.put("/api/coach/{coach_id}/client/{athlete_id}/routine")
def update_routine(coach_id: str, athlete_id: str, req: RoutineUpdateRequest):
    """Coach updates an existing routine in athlete's Hevy."""
    conn = get_db()
    try:
        from coach.hevy import update_routine_in_hevy
        result = update_routine_in_hevy(conn, coach_id, athlete_id, req.routine_push_id, req.title, req.exercises)
        return {"status": "updated", **result}
    finally:
        conn.close()


# ── Notifications ──

@app.get("/api/athlete/{athlete_id}/notifications")
def get_athlete_notifications(athlete_id: str, unread_only: bool = False):
    conn = get_db()
    try:
        from coach.hevy import get_notifications
        notifs = get_notifications(conn, athlete_id, unread_only=unread_only)
        unread = conn.execute("SELECT COUNT(*) as c FROM notification WHERE user_id = ? AND read = 0", (athlete_id,)).fetchone()["c"]
        return {"notifications": notifs, "unread_count": unread}
    finally:
        conn.close()


class MarkReadRequest(BaseModel):
    notification_ids: list[int] | None = None

@app.post("/api/athlete/{athlete_id}/notifications/read")
def mark_read(athlete_id: str, req: MarkReadRequest):
    conn = get_db()
    try:
        from coach.hevy import mark_notifications_read
        mark_notifications_read(conn, athlete_id, req.notification_ids)
        return {"status": "ok"}
    finally:
        conn.close()


# ── Change log ──

@app.get("/api/coach/{coach_id}/client/{athlete_id}/changelog")
def get_changelog(coach_id: str, athlete_id: str, limit: int = 50):
    """Universal change log for a client — all modifications."""
    conn = get_db()
    try:
        # Operation log for this athlete
        ops = conn.execute("""
            SELECT operation_type, actor_role, rendered_text, committed_at
            FROM operation_log
            WHERE payload_json LIKE ? OR payload_json LIKE ?
            ORDER BY committed_at DESC LIMIT ?
        """, (f'%{athlete_id}%', f'%"athlete_id": "{athlete_id}"%', limit)).fetchall()

        # Also include notifications (which capture coach actions even outside operation_log)
        notifs = conn.execute("""
            SELECT type as operation_type, actor_role, title as rendered_text, created_at as committed_at
            FROM notification
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (athlete_id, limit)).fetchall()

        # Merge and sort
        entries = []
        seen = set()
        for row in list(ops) + list(notifs):
            key = f"{row['committed_at'][:16]}:{row['rendered_text'][:50]}"
            if key not in seen:
                seen.add(key)
                entries.append({
                    "type": row["operation_type"],
                    "actor": row["actor_role"] or "system",
                    "text": row["rendered_text"],
                    "timestamp": row["committed_at"],
                })
        entries.sort(key=lambda e: e["timestamp"], reverse=True)
        return {"changelog": entries[:limit]}
    finally:
        conn.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "coach-platform"}
