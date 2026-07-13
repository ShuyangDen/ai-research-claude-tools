"""Load and validate the deliberately small JSON-Schema contract subset."""

from __future__ import annotations

import json
import os
import sysconfig
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    pass


def schema_root() -> Path:
    configured = os.environ.get("RESEARCH_CORE_SCHEMA_ROOT")
    if configured:
        return Path(configured)
    source_root = Path(__file__).resolve().parents[2] / "schemas" / "v1"
    if source_root.exists():
        return source_root
    installed_root = Path(sysconfig.get_path("data")) / "share" / "research-workflow-core" / "schemas" / "v1"
    if installed_root.exists():
        return installed_root
    raise FileNotFoundError("Set RESEARCH_CORE_SCHEMA_ROOT to the installed schemas/v1 directory")


def available_schemas() -> list[str]:
    return sorted(path.name.removesuffix(".schema.json") for path in schema_root().glob("*.schema.json"))


def load_schema(name: str) -> dict[str, Any]:
    path = schema_root() / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown contract {name!r}; available: {', '.join(available_schemas())}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"Schema {path} is not an object")
    return value


def _resolve_ref(root: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ContractError(f"Only local schema references are supported: {reference}")
    value: Any = root
    for part in reference[2:].split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    if not isinstance(value, dict):
        raise ContractError(f"Reference does not resolve to an object: {reference}")
    return value


def _is_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def _validate(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str, errors: list[str]) -> None:
    if "$ref" in schema:
        _validate(value, _resolve_ref(root, schema["$ref"]), root, path, errors)
        return
    if "anyOf" in schema:
        alternatives: list[list[str]] = []
        for alternative in schema["anyOf"]:
            alternative_errors: list[str] = []
            _validate(value, alternative, root, path, alternative_errors)
            alternatives.append(alternative_errors)
        if alternatives and all(alternative_errors for alternative_errors in alternatives):
            errors.append(f"{path}: did not match any allowed schema alternative")
    expected = schema.get("type")
    if expected:
        expected_types = [expected] if isinstance(expected, str) else expected
        if not any(_is_type(value, item) for item in expected_types):
            errors.append(f"{path}: expected {expected_types}, got {type(value).__name__}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not in {schema['enum']!r}")
    if isinstance(value, str) and len(value) < int(schema.get("minLength", 0)):
        errors.append(f"{path}: string is shorter than minLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum {schema['maximum']}")
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required property {required!r}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                _validate(item, properties[key], root, f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property {key!r}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate(item, schema["items"], root, f"{path}[{index}]", errors)


def validate_contract(name: str, value: Any) -> list[str]:
    schema = load_schema(name)
    errors: list[str] = []
    _validate(value, schema, schema, "$", errors)
    return errors


def assert_contract(name: str, value: Any) -> None:
    errors = validate_contract(name, value)
    if errors:
        raise ContractError("\n".join(errors))
