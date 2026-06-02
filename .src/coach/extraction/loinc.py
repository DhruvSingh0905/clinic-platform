"""Test name → LOINC mapping via deterministic synonym lookup.

The LLM extracts the raw test name; this module maps it to a LOINC code.
Fuzzy matching is intentionally absent — we'd rather flag an unmapped test
than silently map it wrong.
"""

from __future__ import annotations

from coach.extraction.reference_data import ALIAS_INDEX, TestDefinition


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

    return None
