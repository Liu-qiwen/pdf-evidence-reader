#!/usr/bin/env python3
"""Check the saved result against field names from the actual case contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def reject_constant(value: str):
    raise ValueError(f"{value} is not a valid JSON value")


def load(path: Path):
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream, parse_constant=reject_constant)


def names(entries) -> set[str] | None:
    if isinstance(entries, dict) and all(isinstance(k, str) for k in entries):
        return set(entries)
    if not isinstance(entries, list):
        return None
    fields = []
    for entry in entries:
        value = entry if isinstance(entry, str) else (
            entry.get("name") or entry.get("field") if isinstance(entry, dict) else None
        )
        if not isinstance(value, str) or not value:
            return None
        fields.append(value)
    return set(fields)


def contract_fields(contract):
    if isinstance(contract, list):
        return names(contract), None
    if not isinstance(contract, dict):
        return None, None
    if isinstance(contract.get("result.json"), (list, dict)):
        return contract_fields(contract["result.json"])
    schema = contract.get("schema", contract)
    if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
        fields = names(schema.get("required", schema["properties"]))
        return fields, schema
    for key in ("required_fields", "required", "fields"):
        if key in contract:
            return names(contract[key]), None
    # A field-keyed mapping of descriptors is also supported.
    reserved = {"format", "path", "filename", "description", "schema", "example", "examples", "notes"}
    if contract and not reserved.intersection(contract) and all(isinstance(v, dict) for v in contract.values()):
        return names(contract), None
    return None, None


def external_ref(value) -> bool:
    if isinstance(value, list):
        return any(external_ref(item) for item in value)
    if not isinstance(value, dict):
        return False
    return any(
        (key in {"$ref", "$dynamicRef", "$recursiveRef"} and isinstance(item, str) and not item.startswith("#"))
        or external_ref(item) for key, item in value.items()
    )


def check(case: dict, result: dict) -> dict:
    if not isinstance(case, dict) or not isinstance(result, dict):
        raise ValueError("Both files must contain JSON objects")
    errors, notes = [], []
    if "case_id" not in case:
        errors.append("case.json has no case_id")
    elif (type(case["case_id"]) is not type(result.get("case_id"))
          or "case_id" not in result or case["case_id"] != result["case_id"]):
        errors.append("result.json does not preserve the case_id")
    required, schema = contract_fields(case.get("output_contract"))
    if required is None:
        notes.append("Contract format needs manual field and type validation")
    else:
        errors.extend(f"Missing result key: {name}" for name in sorted(required - set(result)))
    if schema and external_ref(schema):
        notes.append("Schema has external references; validate with the supplied schema resources")
    elif schema:
        try:
            import jsonschema
        except ImportError:
            notes.append("JSON Schema validator unavailable; check types, allowed values and nesting manually")
        else:
            try:
                validator = jsonschema.validators.validator_for(schema)
                validator.check_schema(schema)
                for issue in validator(schema).iter_errors(result):
                    position = ".".join(map(str, issue.path)) or "$"
                    errors.append(f"{position}: {issue.message}")
            except jsonschema.exceptions.SchemaError as exc:
                notes.append(f"Provided schema needs manual review: {exc.message}")
    return {"status": "invalid" if errors else "manual_review" if notes else "valid",
            "errors": errors, "notes": notes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        report = check(load(args.case), load(args.result))
    except (OSError, ValueError) as exc:
        report = {"status": "invalid", "errors": [str(exc)], "notes": []}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(2 if report["status"] == "invalid" else 0)
