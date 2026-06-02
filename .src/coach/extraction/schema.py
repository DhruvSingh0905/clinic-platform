"""Pydantic models for bloodwork extraction I/O."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Flag(str, Enum):
    HIGH = "high"
    LOW = "low"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    VALID = "valid"
    IMPLAUSIBLE_VALUE = "implausible_value"
    UNKNOWN_UNIT = "unknown_unit"
    UNMAPPED_TEST = "unmapped_test"
    MISSING_RANGE = "missing_range"
    SUSPICIOUS_DATE = "suspicious_date"
    FLAG_INCONSISTENT = "flag_inconsistent"


class ExtractedResult(BaseModel):
    """A single lab result as extracted by the LLM, before validation."""
    test_name_raw: str
    value: float | None = None
    value_string: str = ""
    unit: str = ""
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    flag: Flag = Flag.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str | None = None


class ExtractionResponse(BaseModel):
    """Full LLM extraction output for one PDF."""
    document_rejected: bool = False
    rejection_reason: str | None = None
    lab_source: str | None = None
    draw_date: str | None = None
    results: list[ExtractedResult] = Field(default_factory=list)


class ValidatedResult(BaseModel):
    """A single lab result after validation."""
    test_name_raw: str
    loinc_code: str | None = None
    canonical_name: str | None = None
    value: float | None = None
    value_string: str = ""
    unit_raw: str = ""
    unit_canonical: str | None = None
    reference_range_low: float | None = None
    reference_range_high: float | None = None
    flag: Flag = Flag.UNKNOWN
    confidence: float = 0.0
    validation_issues: list[ValidationStatus] = Field(default_factory=list)
    notes: str | None = None


class ValidatedExtraction(BaseModel):
    """Full validated extraction output for one PDF."""
    source_file: str = ""
    document_rejected: bool = False
    rejection_reason: str | None = None
    lab_source: str | None = None
    draw_date: str | None = None
    draw_date_valid: bool = True
    results: list[ValidatedResult] = Field(default_factory=list)
    document_confidence: float = 0.0
