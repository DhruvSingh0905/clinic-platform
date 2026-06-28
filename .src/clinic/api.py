"""Clinic Platform API — FastAPI backend.

Multi-tenant read layer for clinicians, self-logging for patients.
The substance boundary is enforced here: no clinician endpoint writes substance data.

CDE-compatible tables use `user_id` (= patient.id).
Clinic Platform tables use `patient_id` / `clinician_id`.
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

from clinic.database import get_db, init_db
from clinic.config import SEED_MOCK
from clinic.operations import (
    SetTrainingBlock, EndTrainingBlock, SetNutritionTarget,
    AddRecoveryNote, UserLogSubstanceEvent,
    commit_operation,
)


def _treatment_duration(started_at: str | None) -> int:
    """How many days the patient has been on the current treatment status."""
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
    from clinic.loaders import seed_metric_definitions, seed_compound_definitions
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
    print(f"[startup] SEED_MOCK={SEED_MOCK}")
    if SEED_MOCK:
        try:
            count = conn.execute("SELECT COUNT(*) FROM clinician").fetchone()[0]
            patient_count = conn.execute("SELECT COUNT(*) FROM patient").fetchone()[0]
            if count == 0 or patient_count == 0:
                from clinic.mock_data import seed_mock_data
                seed_mock_data(conn)
                conn.commit()
                print(f"[startup] Seeded mock data: {conn.execute('SELECT COUNT(*) FROM patient').fetchone()[0]} patients")
        except Exception as e:
            print(f"[startup] Mock seeder error: {e}")
            import traceback
            traceback.print_exc()
            from clinic.mock_data import seed_mock_data
            seed_mock_data(conn)
            conn.commit()
        # Seed mock workout data if not yet present
        try:
            wcount = conn.execute("SELECT COUNT(*) FROM workout_session").fetchone()[0]
            if wcount == 0:
                from clinic.hevy import seed_mock_workouts
                for aid in ["patient-001", "patient-002", "patient-003"]:
                    seed_mock_workouts(conn, aid)
                conn.commit()
        except Exception as e:
            print(f"[startup] Workout seeder error: {e}")
    conn.close()
    yield


app = FastAPI(title="Clinic Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3847"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Clinician Roster ──

@app.get("/api/clinician/{clinician_id}/roster")
def get_roster(clinician_id: str):
    conn = get_db()
    try:
        patients = conn.execute("""
            SELECT a.id, a.name, a.email, a.avatar_color, ca.added_at
            FROM patient a JOIN clinician_patient ca ON a.id = ca.patient_id
            WHERE ca.clinician_id = ? AND ca.status = 'active'
        """, (clinician_id,)).fetchall()

        roster = []

        for pt in patients:
            aid = pt["id"]

            integrations = [r["provider"] for r in conn.execute(
                "SELECT provider FROM integration_status WHERE patient_id = ? AND status = 'connected'", (aid,)
            ).fetchall()]

            last_sync = conn.execute(
                "SELECT MAX(last_sync) as ls FROM integration_status WHERE patient_id = ?", (aid,)
            ).fetchone()

            status_row = conn.execute(
                "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1", (aid,)
            ).fetchone()

            treatment_status = status_row["phase"] if status_row else "unknown"
            treatment_days = _treatment_duration(status_row["started_at"] if status_row else None)

            roster.append({
                "patient": {
                    "id": aid, "name": pt["name"], "email": pt["email"],
                    "avatar_color": pt["avatar_color"], "connected_at": pt["added_at"],
                    "last_sync": last_sync["ls"] if last_sync else None, "integrations": integrations,
                },
                "treatment_status": treatment_status,
                "treatment_days": treatment_days,
            })

        roster.sort(key=lambda r: (r["patient"]["name"] or "").lower())
        return {"roster": roster, "clinician_id": clinician_id}
    finally:
        conn.close()


# ── Client Detail ──

@app.get("/api/clinician/{clinician_id}/patient/{patient_id}")
def get_client_detail(clinician_id: str, patient_id: str):
    conn = get_db()
    try:
        rel = conn.execute(
            "SELECT 1 FROM clinician_patient WHERE clinician_id = ? AND patient_id = ? AND status = 'active'",
            (clinician_id, patient_id)).fetchone()
        if not rel:
            raise HTTPException(status_code=403, detail="Not your client")

        pt = conn.execute("SELECT * FROM patient WHERE id = ?", (patient_id,)).fetchone()
        if not pt:
            raise HTTPException(status_code=404, detail="Patient not found")

        status_row = conn.execute(
            "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (patient_id,)).fetchone()
        treatment_status = status_row["phase"] if status_row else "unknown"
        treatment_days = _treatment_duration(status_row["started_at"] if status_row else None)

        integrations = [r["provider"] for r in conn.execute(
            "SELECT provider FROM integration_status WHERE patient_id = ? AND status = 'connected'", (patient_id,)
        ).fetchall()]
        last_sync = conn.execute(
            "SELECT MAX(last_sync) as ls FROM integration_status WHERE patient_id = ?", (patient_id,)
        ).fetchone()

        # Wearables (CDE table — user_id)
        wearables = [dict(w) for w in conn.execute("""
            SELECT metric, observation_date, value_mean, unit, source, methodology
            FROM wearable_observation WHERE user_id = ?
            ORDER BY observation_date DESC LIMIT 200
        """, (patient_id,)).fetchall()]

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
        """, (patient_id,)).fetchall():
            labs.append(dict(l))

        # Medication events (CDE table — user_id, compound_id). Join compound_definition for names.
        substance_events = []
        for s in conn.execute("""
            SELECT COALESCE(cd.canonical_name, ce.compound_id) as compound_name,
                   COALESCE(cd.compound_class, 'unknown') as compound_class,
                   ce.event_type, ce.dose_mg, ce.frequency, ce.route, ce.timestamp
            FROM compound_event ce
            LEFT JOIN compound_definition cd ON ce.compound_id = cd.id
            WHERE ce.user_id = ?
            ORDER BY ce.timestamp DESC
        """, (patient_id,)).fetchall():
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
        """, (patient_id,)).fetchall():
            drug_levels.append(dict(d))

        # Training (Clinic Platform table — patient_id)
        training = [dict(t) for t in conn.execute("""
            SELECT id, name, block_type, start_date, end_date, notes, status
            FROM training_block WHERE patient_id = ? ORDER BY start_date DESC
        """, (patient_id,)).fetchall()]

        # Nutrition (Clinic Platform table — patient_id)
        nutrition = [dict(n) for n in conn.execute("""
            SELECT id, calories, protein_g, carbs_g, fat_g, notes, effective_date
            FROM nutrition_target WHERE patient_id = ? ORDER BY effective_date DESC
        """, (patient_id,)).fetchall()]

        # Recovery (Clinic Platform table — patient_id)
        recovery = [dict(r) for r in conn.execute("""
            SELECT id, note_type, content, created_at
            FROM recovery_note WHERE patient_id = ? ORDER BY created_at DESC
        """, (patient_id,)).fetchall()]

        return {
            "patient": {
                "id": pt["id"], "name": pt["name"], "email": pt["email"],
                "avatar_color": pt["avatar_color"],
                "last_sync": last_sync["ls"] if last_sync else None, "integrations": integrations,
            },
            "treatment_status": treatment_status, "treatment_days": treatment_days,
            "treatment_started_at": status_row["started_at"] if status_row else None,
            "wearables": wearables, "labs": labs,
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


@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/training")
def set_training_block(clinician_id: str, patient_id: str, req: TrainingBlockRequest):
    conn = get_db()
    try:
        op = SetTrainingBlock(patient_id=patient_id, name=req.name, block_type=req.block_type,
                              start_date=req.start_date, end_date=req.end_date, notes=req.notes)
        result = commit_operation(conn, clinician_id, "clinician", op)
        from clinic.hevy import create_notification
        create_notification(conn, patient_id, clinician_id, "clinician", "training_updated",
                            f"Your clinician set a new training block: {req.name}", result["rendered"], None)
        return {"status": "committed", **result}
    finally:
        conn.close()

@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/training/end")
def end_training_block(clinician_id: str, patient_id: str, req: EndTrainingBlockRequest):
    conn = get_db()
    try:
        op = EndTrainingBlock(patient_id=patient_id, block_id=req.block_id, end_date=req.end_date)
        result = commit_operation(conn, clinician_id, "clinician", op)
        return {"status": "committed", **result}
    finally:
        conn.close()

@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/nutrition")
def set_nutrition_target(clinician_id: str, patient_id: str, req: NutritionTargetRequest):
    conn = get_db()
    try:
        op = SetNutritionTarget(patient_id=patient_id, calories=req.calories, protein_g=req.protein_g,
                                carbs_g=req.carbs_g, fat_g=req.fat_g, effective_date=req.effective_date, notes=req.notes)
        result = commit_operation(conn, clinician_id, "clinician", op)
        from clinic.hevy import create_notification
        create_notification(conn, patient_id, clinician_id, "clinician", "nutrition_updated",
                            f"Your clinician updated your nutrition targets", result["rendered"], None)
        return {"status": "committed", **result}
    finally:
        conn.close()

@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/recovery")
def add_recovery_note(clinician_id: str, patient_id: str, req: RecoveryNoteRequest):
    conn = get_db()
    try:
        op = AddRecoveryNote(patient_id=patient_id, note_type=req.note_type, content=req.content)
        result = commit_operation(conn, clinician_id, "clinician", op)
        from clinic.hevy import create_notification
        create_notification(conn, patient_id, clinician_id, "clinician", "recovery_note",
                            f"Your clinician added a note: {req.content[:50]}", result["rendered"], None)
        return {"status": "committed", **result}
    finally:
        conn.close()


# ── Patient endpoints ──

@app.get("/api/patient/{patient_id}/dashboard")
def get_patient_dashboard(patient_id: str):
    conn = get_db()
    try:
        pt = conn.execute("SELECT * FROM patient WHERE id = ?", (patient_id,)).fetchone()
        if not pt:
            raise HTTPException(status_code=404, detail="Patient not found")

        status_row = conn.execute(
            "SELECT phase, started_at FROM cycle_phase WHERE user_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (patient_id,)).fetchone()
        treatment_status = status_row["phase"] if status_row else "unknown"
        treatment_days = _treatment_duration(status_row["started_at"] if status_row else None)

        wearables = [dict(w) for w in conn.execute("""
            SELECT metric, observation_date, value_mean, unit, source
            FROM wearable_observation WHERE user_id = ? ORDER BY observation_date DESC LIMIT 60
        """, (patient_id,)).fetchall()]

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
        """, (patient_id, patient_id)).fetchall()
        drug_levels = [{**dict(d), "at_steady_state": bool(d["at_steady_state"])} for d in drug_levels_raw]

        integrations = [dict(i) for i in conn.execute(
            "SELECT provider, status, last_sync FROM integration_status WHERE patient_id = ?",
            (patient_id,)).fetchall()]

        # Clinician-managed data visible to patient
        training = [dict(t) for t in conn.execute("""
            SELECT id, name, block_type, start_date, end_date, notes, status
            FROM training_block WHERE patient_id = ? ORDER BY start_date DESC
        """, (patient_id,)).fetchall()]

        nutrition = [dict(n) for n in conn.execute("""
            SELECT id, calories, protein_g, carbs_g, fat_g, notes, effective_date
            FROM nutrition_target WHERE patient_id = ? ORDER BY effective_date DESC
        """, (patient_id,)).fetchall()]

        recovery = [dict(r) for r in conn.execute("""
            SELECT id, note_type, content, created_at
            FROM recovery_note WHERE patient_id = ? ORDER BY created_at DESC
        """, (patient_id,)).fetchall()]

        return {
            "patient": {"id": pt["id"], "name": pt["name"], "avatar_color": pt["avatar_color"]},
            "treatment_status": treatment_status, "treatment_days": treatment_days,
            "wearables": wearables, "drug_levels": drug_levels,
            "integrations": integrations,
            "training": training, "nutrition": nutrition, "recovery": recovery,
        }
    finally:
        conn.close()


@app.post("/api/patient/{patient_id}/substance")
def log_substance_event(patient_id: str, req: SubstanceEventRequest):
    """User self-logs a substance event. PATIENT-ONLY, clinician cannot invoke."""
    conn = get_db()
    try:
        op = UserLogSubstanceEvent(
            patient_id=patient_id, compound_name=req.compound_name,
            compound_class=req.compound_class, event_type=req.event_type,
            dose_mg=req.dose_mg, frequency=req.frequency, route=req.route,
        )
        result = commit_operation(conn, patient_id, "patient", op)
        # Trigger PK regeneration
        try:
            from clinic.ingest import regenerate_drug_levels
            regenerate_drug_levels(conn, patient_id)
        except Exception:
            pass
        return {"status": "committed", **result}
    finally:
        conn.close()


# Clinician CAN modify substances. Patient gets notified and must confirm.
@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/substance")
def clinician_modify_substance(clinician_id: str, patient_id: str, req: SubstanceEventRequest):
    """Clinician prescribes or modifies patient's medication protocol."""
    conn = get_db()
    try:
        # Look up compound_id
        cid_row = conn.execute(
            "SELECT id FROM compound_definition WHERE canonical_name = ? OR id = ? OR LOWER(canonical_name) = LOWER(?)",
            (req.compound_name, req.compound_name.lower().replace(" ", "_"), req.compound_name)
        ).fetchone()
        if not cid_row:
            try:
                from clinic.compound_db import COMPOUNDS
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
            (patient_id, compound_id, req.event_type, req.dose_mg, req.frequency, req.route, dt.now().isoformat())
        )

        # Log operation
        rendered = f"Clinician {req.event_type.lower()} {req.compound_name}"
        if req.dose_mg:
            rendered += f" {req.dose_mg}mg"
        if req.frequency:
            rendered += f" {req.frequency}"
        conn.execute(
            "INSERT INTO operation_log (actor_id, actor_role, operation_type, payload_json, rendered_text) VALUES (?, 'clinician', 'ClinicianSubstanceModification', ?, ?)",
            (clinician_id, json.dumps({"compound": req.compound_name, "event_type": req.event_type, "dose_mg": req.dose_mg, "frequency": req.frequency, "route": req.route}), rendered)
        )

        # Notify patient
        from clinic.hevy import create_notification
        create_notification(conn, patient_id, clinician_id, "clinician",
                            "substance_modified",
                            f"Protocol updated: {rendered}",
                            f"{rendered}.",
                            json.dumps({"compound": req.compound_name, "event_type": req.event_type, "dose_mg": req.dose_mg}))

        conn.commit()

        # Trigger PK regeneration
        try:
            from clinic.ingest import regenerate_drug_levels
            regenerate_drug_levels(conn, patient_id)
        except Exception:
            pass

        return {"status": "committed", "rendered": rendered}
    finally:
        conn.close()


# ── Ingestion endpoints ──

@app.post("/api/patient/{patient_id}/upload")
async def upload_bloodwork(patient_id: str, file: UploadFile = File(...)):
    """Upload bloodwork PDF/image. Extract, validate, load, store PDF."""
    conn = get_db()
    try:
        suffix = os.path.splitext(file.filename or "upload.pdf")[1]
        content = await file.read()

        # Store PDF persistently
        from clinic.storage import store_pdf
        stored_path = store_pdf(patient_id, content, file.filename or f"upload{suffix}")

        # Write temp file for extraction
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            from clinic.extraction.extractor import extract_bloodwork
            from clinic.extraction.validator import validate_extraction
            from clinic.loaders import load_bloodwork

            extraction = extract_bloodwork(tmp_path)
            if extraction.document_rejected:
                return {"status": "rejected", "reason": extraction.rejection_reason}

            validated = validate_extraction(extraction)
            count, source_doc_id = load_bloodwork(conn, validated, user_id=patient_id, raw_storage_path=stored_path)

            return {
                "status": "success",
                "results_count": count,
                "draw_date": extraction.draw_date,
                "source_document_id": source_doc_id,
            }
        finally:
            os.unlink(tmp_path)
    finally:
        conn.close()


@app.post("/api/patient/{patient_id}/import/apple-health")
async def import_apple_health(patient_id: str, file: UploadFile = File(...)):
    """Import Apple Health export (ZIP or XML)."""
    conn = get_db()
    try:
        suffix = os.path.splitext(file.filename or "export.zip")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            from clinic.apple_health import parse_apple_health_xml
            from clinic.loaders import load_apple_health
            from clinic.ingest import regenerate_drug_levels

            xml_path = tmp_path
            if tmp_path.endswith(".zip"):
                with zipfile.ZipFile(tmp_path) as zf:
                    xml_name = next((n for n in zf.namelist() if n.endswith("export.xml")), None)
                    if not xml_name:
                        return {"status": "error", "reason": "No export.xml found in ZIP"}
                    xml_path = zf.extract(xml_name, os.path.dirname(tmp_path))

            export = parse_apple_health_xml(xml_path)
            count = load_apple_health(conn, export, user_id=patient_id)
            regenerate_drug_levels(conn, patient_id)

            return {
                "status": "success",
                "records": count,
                "days": len(set(d.date.isoformat() for d in export.daily)),
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

@app.post("/api/patient/{patient_id}/daily")
def submit_daily_entry(patient_id: str, req: DailyEntryRequest):
    """Submit a daily health entry (weight, BP, blood glucose)."""
    conn = get_db()
    try:
        target_date = req.entry_date or date.today().isoformat()

        if req.metric == "weight":
            conn.execute(
                "INSERT OR REPLACE INTO wearable_observation (user_id, metric, observation_date, value_mean, unit, source) VALUES (?, 'weight_kg', ?, ?, 'kg', 'manual')",
                (patient_id, target_date, req.value))
            conn.commit()
        elif req.metric == "bp" and req.value2:
            from clinic.bp_entry import BPReading, validate_bp, classify_bp
            reading = BPReading(systolic=int(req.value), diastolic=int(req.value2))
            issues = validate_bp(reading)
            if issues:
                return {"status": "error", "issues": issues}
            classification = classify_bp(int(req.value), int(req.value2))
            conn.execute(
                "INSERT INTO bp_reading (user_id, systolic, diastolic, timestamp, classification) VALUES (?, ?, ?, ?, ?)",
                (patient_id, int(req.value), int(req.value2), datetime.now().isoformat(), classification))
            conn.commit()
            return {"status": "ok", "date": target_date, "classification": classification}
        elif req.metric == "blood_glucose":
            flag = "high" if req.value > 125 else "normal"
            conn.execute(
                "INSERT INTO metric_observation (user_id, metric_loinc, value_canonical, unit_canonical, observation_date, flag) VALUES (?, '2345-7', ?, 'mg/dL', ?, ?)",
                (patient_id, req.value, target_date, flag))
            conn.commit()
            return {"status": "ok", "date": target_date, "flag": flag}
        else:
            return {"status": "error", "reason": f"Unknown metric: {req.metric}"}

        return {"status": "ok", "date": target_date}
    finally:
        conn.close()


# ── Chat endpoints ──

class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = None

@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/chat")
def clinician_chat(clinician_id: str, patient_id: str, req: ChatRequest):
    """Clinician investigates patient data through LLM chat."""
    conn = get_db()
    try:
        from clinic.chat import chat_clinician
        response = chat_clinician(
            conn, clinician_id, patient_id,
            message=req.message,
            history=req.history,
        )
        return {"response": response}
    except Exception as e:
        return {"response": f"Chat error: {str(e)}", "error": True}
    finally:
        conn.close()

@app.post("/api/patient/{patient_id}/chat")
def patient_chat(patient_id: str, req: ChatRequest):
    """Patient interacts with their own data through LLM chat."""
    conn = get_db()
    try:
        from clinic.chat import chat_patient
        response = chat_patient(
            conn, patient_id,
            message=req.message,
            history=req.history,
        )
        return {"response": response}
    except Exception as e:
        return {"response": f"Chat error: {str(e)}", "error": True}
    finally:
        conn.close()


# ── Calendar endpoints ──

@app.get("/api/patient/{patient_id}/calendar/{target_date}")
def patient_calendar_day(patient_id: str, target_date: str):
    conn = get_db()
    try:
        from clinic.calendar import get_calendar_day
        return get_calendar_day(conn, patient_id, target_date)
    finally:
        conn.close()

@app.get("/api/patient/{patient_id}/calendar/range/{start}/{end}")
def patient_calendar_range(patient_id: str, start: str, end: str):
    conn = get_db()
    try:
        from clinic.calendar import get_calendar_range
        return get_calendar_range(conn, patient_id, start, end)
    finally:
        conn.close()

@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/calendar/{target_date}")
def clinician_patient_calendar(clinician_id: str, patient_id: str, target_date: str):
    conn = get_db()
    try:
        rel = conn.execute("SELECT 1 FROM clinician_patient WHERE clinician_id = ? AND patient_id = ?", (clinician_id, patient_id)).fetchone()
        if not rel:
            raise HTTPException(status_code=403, detail="Not your client")
        from clinic.calendar import get_calendar_day
        return get_calendar_day(conn, patient_id, target_date)
    finally:
        conn.close()


# ── Hevy / Workout endpoints ──

@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/workouts")
def get_client_workouts(clinician_id: str, patient_id: str, days: int = 14):
    """Clinician views patient's recent workouts — structured JSON."""
    conn = get_db()
    try:
        from clinic.hevy import get_workout_history, get_training_summary
        from datetime import timedelta
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        sessions = conn.execute("""
            SELECT id, title, started_at, duration_seconds FROM workout_session
            WHERE user_id = ? AND started_at >= ? ORDER BY started_at DESC
        """, (patient_id, cutoff)).fetchall()

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
            "text_summary": get_training_summary(conn, patient_id, days),
        }
    finally:
        conn.close()


@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/lifts")
def get_client_lifts(clinician_id: str, patient_id: str, days: int = 28):
    """Structured lift progression data for frontend charts."""
    conn = get_db()
    try:
        from clinic.hevy import get_structured_lifts
        return get_structured_lifts(conn, patient_id, days)
    finally:
        conn.close()


@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/lift/{exercise_name}")
def get_client_lift(clinician_id: str, patient_id: str, exercise_name: str, days: int = 28):
    """Clinician views per-exercise progression."""
    conn = get_db()
    try:
        from clinic.hevy import get_lift_progression
        return {"progression": get_lift_progression(conn, patient_id, exercise_name, days)}
    finally:
        conn.close()


@app.get("/api/patient/{patient_id}/workouts")
def get_patient_workouts(patient_id: str, days: int = 14):
    """Patient views their own workouts."""
    conn = get_db()
    try:
        from clinic.hevy import get_workout_history, get_training_summary
        return {
            "workouts": get_workout_history(conn, patient_id, days),
            "summary": get_training_summary(conn, patient_id, days),
        }
    finally:
        conn.close()


class RoutinePushRequest(BaseModel):
    title: str
    exercises: list

@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/routine")
def push_routine(clinician_id: str, patient_id: str, req: RoutinePushRequest):
    """Clinician pushes a routine to patient's Hevy."""
    conn = get_db()
    try:
        from clinic.hevy import push_routine_to_hevy
        result = push_routine_to_hevy(conn, clinician_id, patient_id, req.title, req.exercises)
        return {"status": "pushed", **result}
    finally:
        conn.close()


class RoutineUpdateRequest(BaseModel):
    routine_push_id: int
    title: str
    exercises: list

@app.put("/api/clinician/{clinician_id}/patient/{patient_id}/routine")
def update_routine(clinician_id: str, patient_id: str, req: RoutineUpdateRequest):
    """Clinician updates an existing routine in patient's Hevy."""
    conn = get_db()
    try:
        from clinic.hevy import update_routine_in_hevy
        result = update_routine_in_hevy(conn, clinician_id, patient_id, req.routine_push_id, req.title, req.exercises)
        return {"status": "updated", **result}
    finally:
        conn.close()


@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/routines")
def get_routines(clinician_id: str, patient_id: str):
    """List all routines pushed for this patient."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, title, routine_json, pushed_at, status FROM routine_push WHERE patient_id = ? ORDER BY pushed_at DESC",
            (patient_id,),
        ).fetchall()
        routines = []
        for r in rows:
            import json
            exercises = []
            try:
                exercises = json.loads(r["routine_json"]) if r["routine_json"] else []
            except Exception:
                pass
            routines.append({
                "id": r["id"],
                "title": r["title"],
                "exercises": exercises,
                "pushed_at": r["pushed_at"],
                "status": r["status"],
            })
        return {"routines": routines}
    finally:
        conn.close()


# ── Notifications ──

@app.get("/api/patient/{patient_id}/notifications")
def get_patient_notifications(patient_id: str, unread_only: bool = False):
    conn = get_db()
    try:
        from clinic.hevy import get_notifications
        notifs = get_notifications(conn, patient_id, unread_only=unread_only)
        unread = conn.execute("SELECT COUNT(*) as c FROM notification WHERE user_id = ? AND read = 0", (patient_id,)).fetchone()["c"]
        return {"notifications": notifs, "unread_count": unread}
    finally:
        conn.close()


class MarkReadRequest(BaseModel):
    notification_ids: list[int] | None = None

@app.post("/api/patient/{patient_id}/notifications/read")
def mark_read(patient_id: str, req: MarkReadRequest):
    conn = get_db()
    try:
        from clinic.hevy import mark_notifications_read
        mark_notifications_read(conn, patient_id, req.notification_ids)
        return {"status": "ok"}
    finally:
        conn.close()


# ── Change log ──

@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/changelog")
def get_changelog(clinician_id: str, patient_id: str, limit: int = 50):
    """Universal change log for a client — all modifications."""
    conn = get_db()
    try:
        # Operation log for this patient
        ops = conn.execute("""
            SELECT operation_type, actor_role, rendered_text, committed_at
            FROM operation_log
            WHERE payload_json LIKE ? OR payload_json LIKE ?
            ORDER BY committed_at DESC LIMIT ?
        """, (f'%{patient_id}%', f'%"patient_id": "{patient_id}"%', limit)).fetchall()

        # Also include notifications (which capture clinician actions even outside operation_log)
        notifs = conn.execute("""
            SELECT type as operation_type, actor_role, title as rendered_text, created_at as committed_at
            FROM notification
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (patient_id, limit)).fetchall()

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


# ── Document endpoints (bloodwork PDFs) ──

@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/documents")
def get_client_documents(clinician_id: str, patient_id: str):
    conn = get_db()
    try:
        docs = conn.execute("""
            SELECT id, source_type, uploaded_at, raw_storage_path, metadata_json
            FROM source_document WHERE user_id = ? ORDER BY uploaded_at DESC
        """, (patient_id,)).fetchall()
        result = []
        for d in docs:
            meta = json.loads(d["metadata_json"]) if d["metadata_json"] else {}
            result.append({
                "id": d["id"], "source_type": d["source_type"],
                "uploaded_at": d["uploaded_at"],
                "draw_date": meta.get("draw_date"),
                "has_file": bool(d["raw_storage_path"]),
            })
        return {"documents": result}
    finally:
        conn.close()

@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/documents/{doc_id}")
def serve_client_document(clinician_id: str, patient_id: str, doc_id: int):
    conn = get_db()
    try:
        doc = conn.execute("SELECT raw_storage_path, user_id FROM source_document WHERE id = ?", (doc_id,)).fetchone()
        if not doc or doc["user_id"] != patient_id:
            raise HTTPException(status_code=404, detail="Document not found")
        if not doc["raw_storage_path"]:
            raise HTTPException(status_code=404, detail="No file stored")
        from clinic.storage import get_pdf_path
        path = get_pdf_path(doc["raw_storage_path"])
        if not path.exists():
            raise HTTPException(status_code=404, detail="File missing")
        from fastapi.responses import FileResponse
        return FileResponse(str(path), media_type="application/pdf", headers={"Content-Disposition": "inline"})
    finally:
        conn.close()


# ── Check-in scheduling ──

class CheckInRequest(BaseModel):
    date: str
    time: str = "12:00"
    description: Optional[str] = None

class CheckInNoteRequest(BaseModel):
    notes_text: str

@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/schedule/checkin")
def schedule_checkin(clinician_id: str, patient_id: str, req: CheckInRequest):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO scheduled_event (user_id, event_type, scheduled_date, scheduled_time, description, clinician_id, status, created_by)
            VALUES (?, 'check_in', ?, ?, ?, ?, 'upcoming', ?)
        """, (patient_id, req.date, req.time, req.description, clinician_id, clinician_id))
        event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Google Calendar sync (if configured)
        gcal_id = None
        try:
            from clinic.integrations.google_calendar import create_calendar_event, get_google_calendar_service
            service = get_google_calendar_service(clinician_id)
            if service:
                patient_row = conn.execute("SELECT name, email FROM patient WHERE id = ?", (patient_id,)).fetchone()
                summary = f"Check-in: {patient_row['name'] if patient_row else patient_id}"
                gcal_id = create_calendar_event(service, summary, req.description or "", f"{req.date}T{req.time}:00", f"{req.date}T{req.time}:00")
                if gcal_id:
                    conn.execute("UPDATE scheduled_event SET google_calendar_event_id = ? WHERE id = ?", (gcal_id, event_id))
        except Exception:
            pass  # Google Calendar not configured — that's fine

        from clinic.hevy import create_notification
        create_notification(conn, patient_id, clinician_id, "clinician", "checkin_scheduled",
                            f"Check-in scheduled for {req.date} at {req.time}", req.description, None)
        conn.commit()
        return {"status": "scheduled", "event_id": event_id, "google_calendar_id": gcal_id}
    finally:
        conn.close()

@app.get("/api/clinician/{clinician_id}/patient/{patient_id}/checkins")
def get_checkins(clinician_id: str, patient_id: str):
    conn = get_db()
    try:
        events = conn.execute("""
            SELECT se.id, se.scheduled_date, se.scheduled_time, se.description, se.status, se.google_calendar_event_id
            FROM scheduled_event se WHERE se.user_id = ? AND se.event_type = 'check_in'
            ORDER BY se.scheduled_date DESC
        """, (patient_id,)).fetchall()
        checkins = []
        for e in events:
            notes = conn.execute("SELECT id, notes_text, created_at FROM check_in_note WHERE scheduled_event_id = ? ORDER BY created_at", (e["id"],)).fetchall()
            checkins.append({**dict(e), "notes": [dict(n) for n in notes]})
        return {"checkins": checkins}
    finally:
        conn.close()

@app.post("/api/clinician/{clinician_id}/patient/{patient_id}/checkin/{event_id}/notes")
def add_checkin_notes(clinician_id: str, patient_id: str, event_id: int, req: CheckInNoteRequest):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO check_in_note (scheduled_event_id, clinician_id, patient_id, notes_text) VALUES (?, ?, ?, ?)
        """, (event_id, clinician_id, patient_id, req.notes_text))
        conn.execute("UPDATE scheduled_event SET status = 'completed' WHERE id = ?", (event_id,))
        conn.commit()
        return {"status": "notes_added"}
    finally:
        conn.close()


# ── Clinician cross-roster calendar ──

@app.get("/api/clinician/{clinician_id}/calendar")
def get_clinician_calendar(clinician_id: str, start: str = "", end: str = ""):
    conn = get_db()
    try:
        if not start:
            start = date.today().isoformat()
        if not end:
            end = (date.today() + __import__("datetime").timedelta(days=14)).isoformat()
        events = conn.execute("""
            SELECT se.id, se.user_id as patient_id, a.name as patient_name,
                   se.event_type, se.scheduled_date, se.scheduled_time, se.description, se.status
            FROM scheduled_event se
            JOIN patient a ON se.user_id = a.id
            WHERE se.clinician_id = ? AND se.scheduled_date BETWEEN ? AND ?
            ORDER BY se.scheduled_date, se.scheduled_time
        """, (clinician_id, start, end)).fetchall()
        return {"events": [dict(e) for e in events], "start": start, "end": end}
    finally:
        conn.close()


# ── Onboarding ──

@app.post("/api/clinician/{clinician_id}/onboard/start")
def onboard_start(clinician_id: str, req: dict = {}):
    """Start a new onboarding session."""
    import uuid
    conn = get_db()
    try:
        session_id = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO onboarding_session (id, clinician_id, patient_name, patient_email, status) VALUES (?, ?, ?, ?, 'uploading')",
            (session_id, clinician_id, req.get("patient_name", ""), req.get("patient_email", "")),
        )
        conn.commit()
        return {"session_id": session_id, "status": "uploading"}
    finally:
        conn.close()


@app.post("/api/clinician/{clinician_id}/onboard/{session_id}/upload")
async def onboard_upload(clinician_id: str, session_id: str, file: UploadFile = File(...)):
    """Upload a spreadsheet for analysis."""
    from clinic.onboarding import read_spreadsheet, analyze_with_llm, store_onboard_file

    content = await file.read()
    filename = file.filename or "upload.xlsx"
    stored_path = store_onboard_file(session_id, content, filename)

    try:
        headers, sample_rows, row_count = read_spreadsheet(stored_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # LLM analysis
    try:
        mapping = analyze_with_llm(headers, sample_rows, filename)
    except Exception as e:
        mapping = {"data_type": "unknown", "confidence": 0, "column_mappings": {}, "conflicts": [{"column": "*", "issue": "analysis_failed", "description": str(e)}]}

    conn = get_db()
    try:
        file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
        conn.execute(
            """INSERT INTO onboarding_file (session_id, filename, file_type, storage_path, detected_data_type, mapping_json, mapping_status, row_count)
               VALUES (?, ?, ?, ?, ?, ?, 'proposed', ?)""",
            (session_id, filename, file_type, stored_path, mapping.get("data_type"), json.dumps(mapping), row_count),
        )
        file_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Store conflicts
        for conflict in mapping.get("conflicts", []):
            conn.execute(
                "INSERT INTO onboarding_conflict (file_id, column_name, issue_type, description) VALUES (?, ?, ?, ?)",
                (file_id, conflict.get("column", ""), conflict.get("issue", "unknown"), conflict.get("description", "")),
            )

        conn.execute("UPDATE onboarding_session SET status = 'mapping', updated_at = datetime('now') WHERE id = ?", (session_id,))
        conn.commit()

        return {
            "file_id": file_id,
            "filename": filename,
            "row_count": row_count,
            "headers": headers,
            "sample_rows": sample_rows[:3],
            "detected_data_type": mapping.get("data_type"),
            "confidence": mapping.get("confidence"),
            "column_mappings": mapping.get("column_mappings", {}),
            "conflicts": mapping.get("conflicts", []),
        }
    finally:
        conn.close()


@app.get("/api/clinician/{clinician_id}/onboard/{session_id}/status")
def onboard_status(clinician_id: str, session_id: str):
    """Get onboarding session status with files and conflicts."""
    conn = get_db()
    try:
        session = conn.execute("SELECT * FROM onboarding_session WHERE id = ? AND clinician_id = ?", (session_id, clinician_id)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        files = conn.execute("SELECT * FROM onboarding_file WHERE session_id = ? ORDER BY uploaded_at", (session_id,)).fetchall()
        file_list = []
        for f in files:
            conflicts = conn.execute("SELECT * FROM onboarding_conflict WHERE file_id = ?", (f["id"],)).fetchall()
            file_list.append({
                **dict(f),
                "mapping": json.loads(f["mapping_json"]) if f["mapping_json"] else None,
                "conflicts": [dict(c) for c in conflicts],
            })

        return {
            "session": dict(session),
            "files": file_list,
        }
    finally:
        conn.close()


class ResolveRequest(BaseModel):
    resolutions: dict  # {conflict_id: resolution_text}


@app.post("/api/clinician/{clinician_id}/onboard/{session_id}/resolve")
def onboard_resolve(clinician_id: str, session_id: str, req: ResolveRequest):
    """Resolve onboarding conflicts."""
    conn = get_db()
    try:
        for conflict_id, resolution in req.resolutions.items():
            conn.execute(
                "UPDATE onboarding_conflict SET resolution = ?, status = 'resolved' WHERE id = ?",
                (resolution, int(conflict_id)),
            )
        conn.execute("UPDATE onboarding_session SET status = 'reviewing', updated_at = datetime('now') WHERE id = ?", (session_id,))
        conn.commit()
        return {"status": "resolved", "count": len(req.resolutions)}
    finally:
        conn.close()


class ConfirmImportRequest(BaseModel):
    patient_name: str
    patient_email: Optional[str] = None
    file_mappings: Optional[dict] = None  # {file_id: {col: {target: "table.col"}}} for overrides


@app.post("/api/clinician/{clinician_id}/onboard/{session_id}/confirm")
def onboard_confirm(clinician_id: str, session_id: str, req: ConfirmImportRequest):
    """Confirm and execute the import."""
    import uuid as _uuid
    from clinic.onboarding import execute_import

    conn = get_db()
    try:
        session = conn.execute("SELECT * FROM onboarding_session WHERE id = ? AND clinician_id = ?", (session_id, clinician_id)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Create or find patient
        patient_id = session["patient_id"]
        if not patient_id:
            patient_id = f"patient-{_uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT OR IGNORE INTO patient (id, name, email) VALUES (?, ?, ?)",
                (patient_id, req.patient_name, req.patient_email or ""),
            )
            conn.execute(
                "INSERT OR IGNORE INTO clinician_patient (clinician_id, patient_id) VALUES (?, ?)",
                (clinician_id, patient_id),
            )
            conn.execute(
                "UPDATE onboarding_session SET patient_id = ?, patient_name = ?, updated_at = datetime('now') WHERE id = ?",
                (patient_id, req.patient_name, session_id),
            )

        # Apply any mapping overrides
        if req.file_mappings:
            for file_id_str, overrides in req.file_mappings.items():
                file_row = conn.execute("SELECT mapping_json FROM onboarding_file WHERE id = ?", (int(file_id_str),)).fetchone()
                if file_row and file_row["mapping_json"]:
                    mapping = json.loads(file_row["mapping_json"])
                    mapping["column_mappings"].update(overrides)
                    conn.execute("UPDATE onboarding_file SET mapping_json = ? WHERE id = ?", (json.dumps(mapping), int(file_id_str)))

        conn.commit()

        # Execute import for each file
        files = conn.execute("SELECT id FROM onboarding_file WHERE session_id = ?", (session_id,)).fetchall()
        results = []
        for f in files:
            result = execute_import(conn, session_id, f["id"], patient_id, clinician_id)
            results.append({"file_id": f["id"], **result})

        conn.execute("UPDATE onboarding_session SET status = 'complete', updated_at = datetime('now') WHERE id = ?", (session_id,))
        conn.commit()

        return {"status": "complete", "patient_id": patient_id, "results": results}
    finally:
        conn.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "clinic-platform"}
