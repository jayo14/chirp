import json
import re
from typing import Any, Dict


def parse_clean_json(text: str) -> Dict[str, Any]:
    """
    Cleans and parses a JSON string from LLM responses:
    - Strips markdown code fences (```json ... ``` or ``` ... ```)
    - Extracts the outermost JSON object if surrounding commentary exists
    - Handles leading/trailing whitespace
    - Raises ValueError if no valid JSON object can be extracted
    """
    if not text or not text.strip():
        raise ValueError("Empty response string received from model")

    cleaned = text.strip()

    # 1. Strip markdown code fences
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(fence_pattern, cleaned, re.MULTILINE)
    if match:
        cleaned = match.group(1).strip()

    # 2. Extract outermost { ... } if preamble or postamble exists
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        cleaned = cleaned[start_idx : end_idx + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse model output as valid JSON: {str(e)}") from e
