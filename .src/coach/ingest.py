"""Data ingestion wrappers — call copied CDE loaders and trigger detectors."""
import sqlite3
from datetime import date, timedelta

from coach.triggers import on_data_changed
from coach.pk_model import generate_drug_levels


def after_data_write(conn: sqlite3.Connection, data_type: str, user_id: str) -> list[dict]:
    """Run after any data write. Triggers detectors and returns new findings."""
    return on_data_changed(conn, data_type, user_id=user_id)


def regenerate_drug_levels(conn: sqlite3.Connection, user_id: str, days_back: int = 120) -> int:
    """Regenerate PK drug levels for an athlete."""
    start = date.today() - timedelta(days=days_back)
    end = date.today()
    return generate_drug_levels(conn, user_id=user_id, start_date=start, end_date=end)


def after_compound_change(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    """Run after compound event logged. Regenerate PK levels, then run detectors."""
    regenerate_drug_levels(conn, user_id)
    return after_data_write(conn, "compound", user_id)
