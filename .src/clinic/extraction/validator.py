"""Per-field validation of extracted lab results.

Validates each field independently. Flags problems but never silently
discards data — the raw extraction is always preserved for human review.
"""

from __future__ import annotations

from datetime import date, timedelta

from clinic.extraction.loinc import map_test_name
from clinic.extraction.schema import (
    ExtractedResult,
    ExtractionResponse,
    Flag,
    ValidatedExtraction,
    ValidatedResult,
    ValidationStatus,
)


def validate_extraction(
    extraction: ExtractionResponse,
    source_file: str = "",
) -> ValidatedExtraction:
    """Validate an entire extraction response."""
    if extraction.document_rejected:
        return ValidatedExtraction(
            source_file=source_file,
            document_rejected=True,
            rejection_reason=extraction.rejection_reason,
            lab_source=extraction.lab_source,
        )

    validated_results = [_validate_result(r) for r in extraction.results]

    # Document-level confidence: average of per-result confidence,
    # penalized by proportion of results with validation issues.
    if validated_results:
        avg_conf = sum(r.confidence for r in validated_results) / len(validated_results)
        issue_rate = sum(1 for r in validated_results if r.validation_issues) / len(validated_results)
        doc_confidence = avg_conf * (1 - 0.5 * issue_rate)
    else:
        doc_confidence = 0.0

    draw_date_valid = _validate_draw_date(extraction.draw_date)

    return ValidatedExtraction(
        source_file=source_file,
        document_rejected=False,
        lab_source=extraction.lab_source,
        draw_date=extraction.draw_date,
        draw_date_valid=draw_date_valid,
        results=validated_results,
        document_confidence=round(doc_confidence, 3),
    )


def _validate_result(result: ExtractedResult) -> ValidatedResult:
    """Validate a single extracted lab result."""
    issues: list[ValidationStatus] = []

    # 1. LOINC mapping
    test_def = map_test_name(result.test_name_raw)
    loinc_code = None
    canonical_name = None
    unit_canonical = None

    if test_def is None:
        issues.append(ValidationStatus.UNMAPPED_TEST)
    else:
        loinc_code = test_def.loinc_code
        canonical_name = test_def.canonical_name
        unit_canonical = test_def.canonical_unit

        # 2. Value plausibility
        if result.value is not None:
            if not (test_def.plausibility_min <= result.value <= test_def.plausibility_max):
                issues.append(ValidationStatus.IMPLAUSIBLE_VALUE)

        # 3. Flag consistency — check if flag matches value vs. reference range
        if (
            result.value is not None
            and result.reference_range_low is not None
            and result.reference_range_high is not None
        ):
            expected_flag = _compute_expected_flag(
                result.value, result.reference_range_low, result.reference_range_high
            )
            if result.flag != Flag.UNKNOWN and result.flag != expected_flag:
                issues.append(ValidationStatus.FLAG_INCONSISTENT)

    # 4. Unit validation (basic — is it non-empty?)
    if not result.unit.strip():
        issues.append(ValidationStatus.UNKNOWN_UNIT)

    # 5. Reference range
    if result.reference_range_low is None and result.reference_range_high is None:
        issues.append(ValidationStatus.MISSING_RANGE)
    elif result.reference_range_low is not None and result.reference_range_high is not None:
        if result.reference_range_low >= result.reference_range_high:
            issues.append(ValidationStatus.MISSING_RANGE)

    return ValidatedResult(
        test_name_raw=result.test_name_raw,
        loinc_code=loinc_code,
        canonical_name=canonical_name,
        value=result.value,
        value_string=result.value_string,
        unit_raw=result.unit,
        unit_canonical=unit_canonical,
        reference_range_low=result.reference_range_low,
        reference_range_high=result.reference_range_high,
        flag=result.flag if ValidationStatus.FLAG_INCONSISTENT not in issues else _compute_expected_flag(
            result.value,
            result.reference_range_low,
            result.reference_range_high,
        ),
        confidence=result.confidence,
        validation_issues=issues,
        notes=result.notes,
    )


def _compute_expected_flag(value: float, low: float, high: float) -> Flag:
    """Determine what the flag should be based on value vs. range."""
    if value < low:
        return Flag.LOW
    elif value > high:
        return Flag.HIGH
    else:
        return Flag.NORMAL


def _validate_draw_date(draw_date: str | None) -> bool:
    """Check if draw date is a valid, reasonable date."""
    if not draw_date:
        return False
    try:
        parsed = date.fromisoformat(draw_date)
        today = date.today()
        # Not in the future, not more than 10 years ago
        return parsed <= today and parsed >= today - timedelta(days=3650)
    except (ValueError, TypeError):
        return False
