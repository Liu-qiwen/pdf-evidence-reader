#!/usr/bin/env python3
"""Check structural completeness of a bilingual alignment JSON sidecar.

This checker does not evaluate translation quality or replace a case output contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["top-level JSON value must be an object"]

    segments = data.get("segments")
    if not isinstance(segments, list):
        return ["segments must be an array"]
    if not segments:
        errors.append("segments must contain at least one source unit")

    seen: set[str] = set()
    for index, segment in enumerate(segments):
        where = f"segments[{index}]"
        if not isinstance(segment, dict):
            errors.append(f"{where} must be an object")
            continue

        unit_id = segment.get("id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            errors.append(f"{where}.id must be a non-empty string")
        elif unit_id in seen:
            errors.append(f"duplicate segment id: {unit_id}")
        else:
            seen.add(unit_id)

        source = segment.get("source_text")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"{where}.source_text must be a non-empty string")

        status = segment.get("status")
        target = segment.get("target_text")
        if status == "untranslated":
            reason = segment.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"{where}.reason is required when status is untranslated")
        elif not isinstance(target, str) or not target.strip():
            errors.append(f"{where}.target_text must be a non-empty string")

        locator = segment.get("locator")
        if not isinstance(locator, dict):
            errors.append(f"{where}.locator must be an object")
        else:
            filename = locator.get("file")
            anchors = [key for key, value in locator.items()
                       if key != "file" and value not in (None, "", [], {})]
            if not isinstance(filename, str) or not filename.strip():
                errors.append(f"{where}.locator.file must be a non-empty string")
            if not anchors:
                errors.append(f"{where}.locator needs at least one source anchor")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alignment_json", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.alignment_json.read_text(encoding="utf-8"))
    except OSError as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, ensure_ascii=False))
        return 2
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "error", "errors": [f"invalid JSON: {exc}"]}, ensure_ascii=False))
        return 2

    errors = validate(data)
    result = {
        "status": "invalid" if errors else "valid",
        "segment_count": len(data.get("segments", [])) if isinstance(data, dict) and isinstance(data.get("segments"), list) else 0,
        "errors": errors,
        "scope_note": "Structural checks only; semantic translation review is still required.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
