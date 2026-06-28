"""Test name → LOINC mapping via deterministic synonym lookup.

The LLM extracts the raw test name; this module maps it to a LOINC code.
Fuzzy matching is intentionally absent — we'd rather flag an unmapped test
than silently map it wrong.
"""

from __future__ import annotations

import re

from clinic.extraction.reference_data import ALIAS_INDEX, TestDefinition

# Pattern matching embedded numeric values + units that labs sometimes concatenate
_VALUE_UNIT_PATTERN = re.compile(
    r"\s*\d+\.?\d*\s*"
    r"(mL/min/1\.73m2|mL/min/1\.73|mL/min|ng/dL|mg/dL|U/L|g/dL|"
    r"mmol/L|mEq/L|x10E3/uL|M/uL|%|pg|fL|ratio)"
    r".*$",
    re.IGNORECASE,
)


def map_test_name(raw_name: str) -> TestDefinition | None:
    """Look up a test definition by raw name. Returns None if no match."""
    # Exact case-insensitive match first
    normalized = raw_name.strip().lower()
    if normalized in ALIAS_INDEX:
        return ALIAS_INDEX[normalized]

    # Try stripping common suffixes/prefixes labs add
    for suffix in [", serum", ", s", ", plasma", ", blood", " serum", " plasma"]:
        trimmed = normalized.removesuffix(suffix)
        if trimmed != normalized and trimmed in ALIAS_INDEX:
            return ALIAS_INDEX[trimmed]

    # Try stripping parenthetical qualifiers: "ALT (SGPT)" → "ALT"
    if "(" in normalized:
        base = normalized.split("(")[0].strip()
        if base in ALIAS_INDEX:
            return ALIAS_INDEX[base]

    # Try stripping embedded numeric values + units:
    # e.g., "eGFR Non-African American 59 mL/min/1.73m2" → "eGFR Non-African American"
    stripped = _VALUE_UNIT_PATTERN.sub("", normalized).strip()
    if stripped and stripped != normalized and stripped in ALIAS_INDEX:
        return ALIAS_INDEX[stripped]

    return None
