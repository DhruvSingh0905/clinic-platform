"""Typed operation set for Clinic Platform.

The closed, enumerated set of operations any actor can perform.
CRITICAL: No clinician-side substance-write operation exists in this set.
The clinician can view substance data read-only; the user self-logs.
This boundary is enforced by what's representable, not by a prompt.
"""
from dataclasses import dataclass
from typing import Optional
import json
import uuid
from datetime import datetime


# --- Clinician operations (the lawful clinical surface) ---

@dataclass
class SetTrainingBlock:
    """Clinician sets a training block for a patient."""
    patient_id: str
    name: str
    block_type: str  # exercise, rehab, maintenance, custom
    start_date: str
    end_date: Optional[str] = None
    notes: Optional[str] = None

    def render(self) -> str:
        parts = [f"Set training block: {self.name} ({self.block_type})"]
        parts.append(f"Starting {self.start_date}")
        if self.end_date:
            parts.append(f"through {self.end_date}")
        if self.notes:
            parts.append(f"Notes: {self.notes}")
        return ". ".join(parts) + "."


@dataclass
class EndTrainingBlock:
    """Clinician ends an active training block."""
    patient_id: str
    block_id: str
    end_date: str

    def render(self) -> str:
        return f"End training block {self.block_id} as of {self.end_date}."


@dataclass
class SetNutritionTarget:
    """Clinician sets macro/calorie targets."""
    patient_id: str
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    effective_date: str
    notes: Optional[str] = None

    def render(self) -> str:
        text = (f"Set nutrition targets effective {self.effective_date}: "
                f"{self.calories} kcal — {self.protein_g}g protein, "
                f"{self.carbs_g}g carbs, {self.fat_g}g fat.")
        if self.notes:
            text += f" Notes: {self.notes}."
        return text


@dataclass
class AddRecoveryNote:
    """Clinician adds a recovery note/directive."""
    patient_id: str
    note_type: str  # assessment, plan, subjective, objective, follow_up, general
    content: str

    def render(self) -> str:
        return f"Recovery note ({self.note_type}): {self.content}"


@dataclass
class NudgeSensitivity:
    """Clinician adjusts detector sensitivity for a patient (within guardrails)."""
    patient_id: str
    detector_id: str
    direction: str  # more, less

    def render(self) -> str:
        return f"Nudge {self.detector_id} sensitivity {self.direction} for this client."


# --- User operations (user self-logs, never clinician) ---

@dataclass
class UserLogSubstanceEvent:
    """Patient logs their own substance event. Clinician uses separate pathway."""
    patient_id: str
    compound_name: str
    compound_class: str
    event_type: str  # START, DOSE_CHANGE, STOP, MISSED_DOSE
    dose_mg: Optional[float] = None
    frequency: Optional[str] = None
    route: Optional[str] = None

    def render(self) -> str:
        if self.event_type == "START":
            return (f"Start {self.compound_name}: {self.dose_mg}mg "
                    f"{self.frequency} ({self.route}).")
        elif self.event_type == "STOP":
            return f"Stop {self.compound_name}."
        elif self.event_type == "DOSE_CHANGE":
            return (f"Change {self.compound_name} dose to {self.dose_mg}mg "
                    f"{self.frequency}.")
        elif self.event_type == "MISSED_DOSE":
            return f"Missed dose: {self.compound_name}."
        return f"{self.event_type}: {self.compound_name}"


# The complete operation set — clinician operations + user operations
CLINICIAN_OPERATIONS = {
    "SET_TRAINING_BLOCK": SetTrainingBlock,
    "END_TRAINING_BLOCK": EndTrainingBlock,
    "SET_NUTRITION_TARGET": SetNutritionTarget,
    "ADD_RECOVERY_NOTE": AddRecoveryNote,
    "NUDGE_SENSITIVITY": NudgeSensitivity,
}

USER_OPERATIONS = {
    "USER_LOG_SUBSTANCE_EVENT": UserLogSubstanceEvent,
}

# ALL operations — note: no overlap, no clinician substance ops
ALL_OPERATIONS = {**CLINICIAN_OPERATIONS, **USER_OPERATIONS}


def commit_operation(conn, actor_id: str, actor_role: str, operation) -> dict:
    """Commit a typed operation to the database.

    Validates actor role against operation type.
    Clinician uses a separate pathway for substance modifications.
    """
    op_type = type(operation).__name__

    # Enforce the substance boundary
    if actor_role == "clinician" and isinstance(operation, UserLogSubstanceEvent):
        raise PermissionError(
            "Clinician cannot use this pathway for substance events. "
            "Substance logging is user-only. "
            "This boundary is enforced structurally."
        )

    rendered = operation.render()
    op_id = str(uuid.uuid4())

    conn.execute(
        "INSERT INTO operation_log (actor_id, actor_role, operation_type, payload_json, rendered_text) VALUES (?, ?, ?, ?, ?)",
        (actor_id, actor_role, op_type, json.dumps(operation.__dict__), rendered)
    )

    # Execute the operation
    if isinstance(operation, SetTrainingBlock):
        block_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO training_block (id, patient_id, clinician_id, name, block_type, start_date, end_date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (block_id, operation.patient_id, actor_id, operation.name, operation.block_type, operation.start_date, operation.end_date, operation.notes)
        )
    elif isinstance(operation, EndTrainingBlock):
        conn.execute(
            "UPDATE training_block SET end_date = ?, status = 'completed' WHERE id = ? AND patient_id = ?",
            (operation.end_date, operation.block_id, operation.patient_id)
        )
    elif isinstance(operation, SetNutritionTarget):
        target_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO nutrition_target (id, patient_id, clinician_id, calories, protein_g, carbs_g, fat_g, notes, effective_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (target_id, operation.patient_id, actor_id, operation.calories, operation.protein_g, operation.carbs_g, operation.fat_g, operation.notes, operation.effective_date)
        )
    elif isinstance(operation, AddRecoveryNote):
        note_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO recovery_note (id, patient_id, clinician_id, note_type, content) VALUES (?, ?, ?, ?, ?)",
            (note_id, operation.patient_id, actor_id, operation.note_type, operation.content)
        )
    elif isinstance(operation, UserLogSubstanceEvent):
        # Look up compound_id: try canonical_name, id, then aliases from compound_db
        name = operation.compound_name
        cid_row = conn.execute(
            "SELECT id FROM compound_definition WHERE canonical_name = ? OR id = ? OR LOWER(canonical_name) = LOWER(?)",
            (name, name.lower().replace(" ", "_"), name)
        ).fetchone()
        if not cid_row:
            # Search compound_db aliases (in-memory)
            try:
                from clinic.compound_db import COMPOUNDS
                for cid, comp in COMPOUNDS.items():
                    if name.lower() in [a.lower() for a in comp.aliases] or name.lower() == comp.canonical_name.lower():
                        cid_row = {"id": cid}
                        break
            except ImportError:
                pass
        compound_id = cid_row["id"] if cid_row else name.lower().replace(" ", "_")
        conn.execute(
            "INSERT INTO compound_event (user_id, compound_id, event_type, dose_mg, frequency, route, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (operation.patient_id, compound_id, operation.event_type, operation.dose_mg, operation.frequency, operation.route, datetime.now().isoformat())
        )

    conn.commit()
    return {"id": op_id, "rendered": rendered, "type": op_type}
