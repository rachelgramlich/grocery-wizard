"""Load optional regex → replacement rules for OCR ingredient line cleanup."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_OCR_FIXES_FILENAME = "ocr_line_fixes.json"


@lru_cache(maxsize=1)
def _compiled_ocr_line_fixes() -> tuple[tuple[re.Pattern[str], str], ...]:
    path = Path(__file__).resolve().parent / "data" / _OCR_FIXES_FILENAME
    raw = path.read_text(encoding="utf-8")
    data: Any = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError("ocr_line_fixes.json must be a JSON array")

    out: list[tuple[re.Pattern[str], str]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise TypeError(f"ocr_line_fixes.json[{index}] must be an object")
        pattern_s = item.get("match")
        replace_s = item.get("replace")
        if not isinstance(pattern_s, str):
            raise TypeError(f"ocr_line_fixes.json[{index}].match must be a string")
        if not pattern_s.strip():
            raise ValueError(f"ocr_line_fixes.json[{index}].match must not be blank")
        if not isinstance(replace_s, str):
            raise TypeError(f"ocr_line_fixes.json[{index}].replace must be a string")
        out.append((re.compile(pattern_s), replace_s))

    return tuple(out)


def apply_ocr_line_fixes(line: str) -> str:
    stripped = line.strip()
    for pattern, replacement in _compiled_ocr_line_fixes():
        if pattern.match(stripped):
            return replacement
    return line
