"""Data ingestion wrappers — PK model regeneration.

Detectors are disconnected. The finding table remains in the schema but is not populated.
To re-enable detectors, restore the on_data_changed calls from clinic.triggers.
"""
import sqlite3
from datetime import date, timedelta

from clinic.pk_model import generate_drug_levels


def after_data_write(conn: sqlite3.Connection, data_type: str, user_id: str) -> list[dict]:
    """No-op stub. Detectors disconnected — returns empty list."""
    return []


def regenerate_drug_levels(conn: sqlite3.Connection, user_id: str, days_back: int = 120) -> int:
    """Regenerate PK drug levels for a patient."""
    start = date.today() - timedelta(days=days_back)
    end = date.today()
    return generate_drug_levels(conn, user_id=user_id, start_date=start, end_date=end)


def after_compound_change(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    """Run after compound event logged. Regenerate PK levels only."""
    regenerate_drug_levels(conn, user_id)
    return []
