"""LLM-based bloodwork PDF extraction using Claude's multimodal API.

Sends the PDF to Claude Sonnet, requests structured JSON extraction with
per-field confidence scores. If the document is unreadable or not a lab
report, the model rejects it rather than guessing.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import anthropic

from coach.config import ANTHROPIC_API_KEY, CDE_MODEL
from coach.extraction.schema import ExtractionResponse, ExtractedResult, Flag


EXTRACTION_SYSTEM_PROMPT = """\
You are a medical lab report data extractor. Your job is to extract structured \
lab results from bloodwork PDF documents.

RULES:
1. Extract every individual test result you can identify in the document.
2. For each result, extract: test name (exactly as printed), numeric value, \
unit, reference range (low and high bounds), and flag (high/low/normal).
3. Extract the draw date (date the blood was drawn / specimen collected).
4. Identify the lab source (Quest, LabCorp, Marek, Ulta, etc.) if visible.
5. Assign a confidence score (0.0 to 1.0) to EACH extracted result reflecting \
how certain you are that the extraction is correct.
6. If you CANNOT make sense of the document — it's not a lab report, it's \
severely corrupted, it's unreadable, or the data is too ambiguous to extract \
reliably — you MUST reject the document. Set "document_rejected" to true and \
explain why. Do NOT output partial garbage. Rejecting a bad document is always \
better than outputting wrong data.
7. For values reported as "<X" or ">X", use the boundary value and note the \
qualifier in the notes field.
8. If a test has no numeric value (e.g., "Non-Reactive", "Negative"), set \
value to null and put the text result in value_string.
9. Do NOT invent, infer, or estimate any values. Only extract what is \
explicitly on the document.

OUTPUT FORMAT (strict JSON):
{
  "document_rejected": false,
  "rejection_reason": null,
  "lab_source": "Lab Name or null",
  "draw_date": "YYYY-MM-DD or null",
  "results": [
    {
      "test_name_raw": "exact name from document",
      "value": 123.4,
      "value_string": "123.4",
      "unit": "ng/dL",
      "reference_range_low": 264.0,
      "reference_range_high": 916.0,
      "flag": "normal",
      "confidence": 0.95,
      "notes": null
    }
  ]
}

Flag must be one of: "high", "low", "normal", "unknown".
Confidence: 0.95+ = very sure, 0.8-0.95 = confident, 0.6-0.8 = uncertain, <0.6 = guessing.
If guessing, flag it — do not silently output low-confidence data as if it were certain.
"""


def _detect_media_type(file_path: Path) -> tuple[str, str]:
    """Detect file type and return (content_type, media_type) for Claude API."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return "document", "application/pdf"
    elif suffix in (".png",):
        return "image", "image/png"
    elif suffix in (".jpg", ".jpeg"):
        return "image", "image/jpeg"
    elif suffix in (".gif",):
        return "image", "image/gif"
    elif suffix in (".webp",):
        return "image", "image/webp"
    elif suffix in (".heic", ".heif"):
        # HEIC needs conversion — Claude doesn't support it directly
        # For now, treat as JPEG (most HEIC from iOS are photos)
        return "image", "image/jpeg"
    else:
        return "document", "application/pdf"  # default to PDF


def extract_bloodwork(file_path: str | Path) -> ExtractionResponse:
    """Extract lab results from a bloodwork file (PDF, PNG, JPG, etc.).

    Args:
        file_path: Path to the file (PDF or image).

    Returns:
        ExtractionResponse with extracted results or rejection.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_bytes = file_path.read_bytes()
    file_b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
    content_type, media_type = _detect_media_type(file_path)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=CDE_MODEL,
        max_tokens=8192,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": content_type,
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": file_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract all lab results from this bloodwork document/image. "
                        "Return the structured JSON as specified. "
                        "If this is not a lab report or you cannot reliably extract the data, reject it.",
                    },
                ],
            }
        ],
    )

    # Parse the response — Claude returns text content
    raw_text = ""
    for block in message.content:
        if block.type == "text":
            raw_text += block.text

    return _parse_response(raw_text)


# Backward compatibility alias
extract_pdf = extract_bloodwork


def _parse_response(raw_text: str) -> ExtractionResponse:
    """Parse Claude's raw text response into an ExtractionResponse."""
    # Strip markdown code fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        # Remove first line (```json) and last line (```)
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return ExtractionResponse(
            document_rejected=True,
            rejection_reason=f"Failed to parse LLM response as JSON: {e}",
        )

    # Build ExtractionResponse from parsed data
    if data.get("document_rejected", False):
        return ExtractionResponse(
            document_rejected=True,
            rejection_reason=data.get("rejection_reason"),
            lab_source=data.get("lab_source"),
        )

    results = []
    for r in data.get("results", []):
        flag_str = r.get("flag", "unknown").lower()
        try:
            flag = Flag(flag_str)
        except ValueError:
            flag = Flag.UNKNOWN

        results.append(
            ExtractedResult(
                test_name_raw=r.get("test_name_raw", ""),
                value=r.get("value"),
                value_string=str(r.get("value_string", r.get("value", ""))),
                unit=r.get("unit") or "",
                reference_range_low=r.get("reference_range_low"),
                reference_range_high=r.get("reference_range_high"),
                flag=flag,
                confidence=float(r.get("confidence", 0.0)),
                notes=r.get("notes"),
            )
        )

    return ExtractionResponse(
        document_rejected=False,
        lab_source=data.get("lab_source"),
        draw_date=data.get("draw_date"),
        results=results,
    )
