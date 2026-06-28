"""File storage utility for uploaded documents (bloodwork PDFs, etc.)."""
import os
import uuid
from pathlib import Path
from clinic.config import UPLOADS_DIR


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def store_pdf(patient_id: str, content: bytes, original_filename: str, draw_date: str | None = None) -> str:
    """Store a PDF file persistently. Returns the relative path for DB storage."""
    patient_dir = Path(UPLOADS_DIR) / patient_id
    _ensure_dir(patient_dir)

    safe_name = original_filename.replace("/", "_").replace("\\", "_")
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = patient_dir / stored_name
    file_path.write_bytes(content)

    return str(file_path.relative_to(Path(UPLOADS_DIR).parent)) if UPLOADS_DIR != "uploads" else f"uploads/{patient_id}/{stored_name}"


def get_pdf_path(relative_path: str) -> Path:
    """Resolve a stored PDF path to an absolute path."""
    base = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return base / relative_path
