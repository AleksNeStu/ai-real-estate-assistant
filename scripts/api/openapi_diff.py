"""The public API contract gate (Task #97 wrote the check, Task #100 made it a gate).

The script exports the OpenAPI schema of the application and compares it with
the committed baseline - `docs/api-v1-baseline.json` - and tells the caller
whether the contract of the API broke.

Two kinds of difference:

* **Breaking** - a consumer of the API would notice. A field was removed or
  renamed, a field changed its type, a field changed whether it is required, a
  new field appeared and is required, an endpoint, a method or a response
  disappeared, a parameter changed.
* **Compatible** - a consumer would not notice. A new endpoint, a new optional
  field, a new response field, a new optional parameter.

The baseline is the contract that was published. Changing it is a deliberate
act, done with the command the failure message names:

    python scripts/api/openapi_diff.py --update-baseline

Usage:
    python scripts/api/openapi_diff.py [--baseline PATH] [--current PATH] [--strict]
    python scripts/api/openapi_diff.py --update-baseline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The version of the API contract the baseline describes. The versioning
# middleware announces the same number on every /api/ response.
CONTRACT_VERSION = "1.0.0"

BREAKING = "breaking"
COMPATIBLE = "compatible"

# Where a schema sits in the conversation. A request is what a consumer
# sends, a response is what it reads. The two break in different ways, so
# the comparison needs to know which side it is on.
CONTEXT_REQUEST = "request"
CONTEXT_RESPONSE = "response"
CONTEXT_UNKNOWN = "unknown"

# How deep the comparison walks into nested schemas. A schema that points at
# itself would otherwise walk forever.
MAX_DEPTH = 25


@dataclass
class Change:
    """One difference between the baseline and the current schema."""

    severity: str
    kind: str
    context: str
    endpoint: str
    field_path: str
    message: str
    impact: str
    status: str = ""
    endpoints: list[str] = field(default_factory=list)

    @property
    def location(self) -> str:
        where = self.endpoint
        if self.status:
            where = f"{where} ({self.status})"
        if self.field_path:
            where = f"{where} -> {self.field_path}"
        return where

    def render(self) -> str:
        lines = [f"  [{self.severity.upper()}] {self.location}", f"    {self.message}"]
        if self.endpoints:
            lines.append(f"    used by: {', '.join(self.endpoints)}")
        lines.append(f"    consumer impact: {self.impact}")
        return "\n".join(lines)

    def annotation(self) -> str:
        """The change as a GitHub Actions error annotation."""
        title = self.location.replace("%", "%25").replace("\n", " ")
        body = self.message
        if self.endpoints:
            body += f" (used by: {', '.join(self.endpoints)})"
        body += f" - consumer impact: {self.impact}"
        return f"::error title=Breaking API change: {title}::{body}"


def load_schema(path: str) -> dict[str, Any]:
    """Load an OpenAPI schema from a JSON file."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def resolve_ref(spec: dict[str, Any], node: Any) -> Any:
    """Follow a local `$ref` until it reaches a schema that is written out.

    A reference that cannot be followed (or that loops) is returned as it is:
    the comparison then sees the reference itself, which is still a stable
    thing to compare.
    """
    seen: set[str] = set()
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            return node
        seen.add(ref)
        target: Any = spec
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or part not in target:
                return node
            target = target[part]
        node = target
    return node


def _split_null(node: Any) -> tuple[Any, bool]:
    """The schema without its null member, and whether it accepts null.

    A field that stops accepting null is a change of its own; the type of
    the field underneath it did not move.
    """
    if not isinstance(node, dict):
        return node, False
    for key in ("anyOf", "oneOf"):
        members = node.get(key)
        if not isinstance(members, list):
            continue
        without_null = [
            member
            for member in members
            if not (isinstance(member, dict) and member.get("type") == "null")
        ]
        has_null = len(without_null) != len(members)
        if len(without_null) == 1:
            return without_null[0], has_null
        if without_null:
            return {key: without_null}, has_null
    return node, False


def type_signature(node: Any) -> str:
    """The shape of a value, in a form two schemas can be compared by.

    Two schemas describe the same type when this string is equal. Nullability
    and enum values are not part of it - they are compared separately,
    because a value that leaves an enum is a different kind of change from a
    type that changes.
    """
    node, _ = _split_null(node)
    if not isinstance(node, dict):
        return "?"
    if "$ref" in node:
        return str(node["$ref"])
    if "anyOf" in node:
        members = sorted(type_signature(member) for member in node["anyOf"])
        return "anyOf[" + ", ".join(members) + "]"
    if "oneOf" in node:
        members = sorted(type_signature(member) for member in node["oneOf"])
        return "oneOf[" + ", ".join(members) + "]"
    if "allOf" in node:
        members = sorted(type_signature(member) for member in node["allOf"])
        return "allOf[" + ", ".join(members) + "]"
    if "type" not in node:
        if "properties" in node:
            return "object"
        if "enum" in node:
            return "enum"
        return "any"
    kind = str(node["type"])
    if kind == "array":
        return "array<" + type_signature(node.get("items", {})) + ">"
    if node.get("format"):
        return f"{kind}/{node['format']}"
    return kind


def accepts_null(node: Any) -> bool:
    """Whether a schema accepts null."""
    _, nullable = _split_null(node)
    return nullable


def enum_values(node: Any) -> list[Any] | None:
    """The values an enum allows, when the schema is an enum."""
    if not isinstance(node, dict):
        return None
    values = node.get("enum")
    if isinstance(values, list):
        return list(values)
    return None


def _is_object_schema(node: Any) -> bool:
    return isinstance(node, dict) and "properties" in node


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------


def _request_schemas(operation: dict[str, Any]) -> list[Any]:
    """The schemas an operation accepts."""
    body = operation.get("requestBody")
    schemas: list[Any] = []
    if isinstance(body, dict):
        for content in (body.get("content") or {}).values():
            if isinstance(content, dict) and "schema" in content:
                schemas.append(content["schema"])
    return schemas


def _response_schemas(operation: dict[str, Any]) -> dict[str, Any]:
    """The schemas an operation returns, by status code."""
    schemas: dict[str, Any] = {}
    for status, response in (operation.get("responses") or {}).items():
        if not isinstance(response, dict):
            continue
        for content in (response.get("content") or {}).values():
            if isinstance(content, dict) and "schema" in content:
                schemas[status] = content["schema"]
                break
    return schemas


def _usage_index(spec: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    """Which endpoints use which named schema, and in which role.

    The message of a change says where it is felt, so a schema that five
    endpoints use is reported once and names all five. The role matters too:
    a schema that is only ever returned does not break a consumer that does
    not send it.
    """
    usage: dict[str, dict[str, list[str]]] = {}

    def note(ref: str, endpoint: str, context: str) -> None:
        name = ref.rsplit("/", 1)[-1]
        bucket = usage.setdefault(name, {}).setdefault(context, [])
        if endpoint not in bucket:
            bucket.append(endpoint)

    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            endpoint = f"{method.upper()} {path}"
            for schema in _request_schemas(operation):
                if isinstance(schema, dict) and "$ref" in schema:
                    note(str(schema["$ref"]), endpoint, CONTEXT_REQUEST)
            for schema in _response_schemas(operation).values():
                if isinstance(schema, dict) and "$ref" in schema:
                    note(str(schema["$ref"]), endpoint, CONTEXT_RESPONSE)

    return usage


def _join(prefix: str, name: str) -> str:
    return f"{prefix}.{name}" if prefix else name


def _contexts_label(contexts: set[str]) -> str:
    return "/".join(sorted(contexts))


def _required_impact(contexts: set[str], now_required: bool) -> str:
    """How a consumer breaks when a field changed its required-ness.

    A request the consumer sends and a response it reads break in opposite
    ways, so the side of the conversation decides the sentence.
    """
    if now_required:
        if CONTEXT_REQUEST in contexts:
            return "a consumer that does not send it is rejected"
        return "the field is guaranteed now; a consumer that treated it as absent has to follow"
    if CONTEXT_RESPONSE in contexts:
        return "a consumer that reads it can now get nothing"
    return "a consumer that omits it is no longer rejected"


def _compare_object(
    baseline: dict[str, Any],
    current: dict[str, Any],
    endpoint: str,
    contexts: set[str],
    prefix: str,
    changes: list[Change],
    status: str = "",
    endpoints: list[str] | None = None,
    depth: int = 0,
    seen: frozenset[tuple[int, int]] = frozenset(),
) -> None:
    """Compare the properties of two object schemas.

    `contexts` says which side of the conversation the schema sits on: a
    request is what a consumer sends, a response is what it reads. A schema
    used in both carries both.

    Only the properties written out here are compared. A property that points
    at another named schema is compared where that schema is written down -
    the components section - so the same difference is not reported twice.
    """
    if depth > MAX_DEPTH:
        return
    pair = (id(baseline), id(current))
    if pair in seen:
        # The schema points at itself. It was already compared.
        return
    seen = seen | {pair}

    base_props: dict[str, Any] = baseline.get("properties") or {}
    cur_props: dict[str, Any] = current.get("properties") or {}
    base_required = set(baseline.get("required") or [])
    cur_required = set(current.get("required") or [])

    label = _contexts_label(contexts)
    used_by = endpoints or []
    removed = [name for name in base_props if name not in cur_props]
    added = [name for name in cur_props if name not in base_props]

    # A rename shows up as one field gone and one field new. When that is
    # what happened, it is reported as the rename it is - the consumer has to
    # change the name it reads, which is a different thing from a field that
    # simply disappeared.
    if len(removed) == 1 and len(added) == 1:
        old, new = removed[0], added[0]
        changes.append(
            Change(
                severity=BREAKING,
                kind="field-renamed",
                context=label,
                endpoint=endpoint,
                status=status,
                field_path=_join(prefix, old),
                message=f"the field '{old}' was renamed to '{new}'",
                impact=(
                    f"a consumer that reads or sends '{old}' has to switch to '{new}'"
                ),
                endpoints=used_by,
            )
        )
        if type_signature(base_props[old]) != type_signature(cur_props[new]):
            changes.append(
                Change(
                    severity=BREAKING,
                    kind="type-changed",
                    context=label,
                    endpoint=endpoint,
                    status=status,
                    field_path=_join(prefix, new),
                    message=(
                        f"the field '{new}' changed its type: "
                        f"{type_signature(base_props[old])} -> "
                        f"{type_signature(cur_props[new])}"
                    ),
                    impact=(
                        "a consumer that sends the old type is rejected, "
                        "a consumer that reads the old type misreads the new one"
                    ),
                    endpoints=used_by,
                )
            )
        if (old in base_required) != (new in cur_required):
            changes.append(
                Change(
                    severity=BREAKING,
                    kind="required-changed",
                    context=label,
                    endpoint=endpoint,
                    status=status,
                    field_path=_join(prefix, new),
                    message=(
                        f"the field '{new}' changed from "
                        f"{'required' if old in base_required else 'optional'} to "
                        f"{'required' if new in cur_required else 'optional'}"
                    ),
                    impact=_required_impact(contexts, new in cur_required),
                    endpoints=used_by,
                )
            )
        removed = []
        added = []

    for name in removed:
        was_required = name in base_required
        changes.append(
            Change(
                severity=BREAKING,
                kind="field-removed",
                context=label,
                endpoint=endpoint,
                status=status,
                field_path=_join(prefix, name),
                message=f"the field '{name}' was removed from the contract",
                impact=(
                    "a consumer that reads it gets nothing"
                    if CONTEXT_RESPONSE in contexts
                    else "a consumer that sends it has it ignored or rejected"
                )
                + ("" if was_required else " (the field was optional)"),
                endpoints=used_by,
            )
        )

    for name in added:
        now_required = name in cur_required
        changes.append(
            Change(
                # A field that appeared and is required is a change of the
                # contract: a consumer that does not send it is rejected.
                severity=BREAKING if now_required else COMPATIBLE,
                kind="field-added-required" if now_required else "field-added",
                context=label,
                endpoint=endpoint,
                status=status,
                field_path=_join(prefix, name),
                message=(
                    f"the field '{name}' was added"
                    + (" and is required" if now_required else "")
                ),
                impact=(
                    "a consumer that does not send it is rejected"
                    if now_required and CONTEXT_REQUEST in contexts
                    else (
                        "the contract now guarantees the field; a consumer that "
                        "treated its absence as fixed has to follow"
                        if now_required
                        else "a consumer that does not know the field ignores it"
                    )
                ),
                endpoints=used_by,
            )
        )

    for name, base_prop in base_props.items():
        if name not in cur_props:
            continue
        cur_prop = cur_props[name]
        path = _join(prefix, name)

        was_required = name in base_required
        now_required = name in cur_required
        if was_required != now_required:
            changes.append(
                Change(
                    severity=BREAKING,
                    kind="required-changed",
                    context=label,
                    endpoint=endpoint,
                    status=status,
                    field_path=path,
                    message=(
                        f"the field '{name}' changed from "
                        f"{'required' if was_required else 'optional'} to "
                        f"{'required' if now_required else 'optional'}"
                    ),
                    impact=_required_impact(contexts, now_required),
                    endpoints=used_by,
                )
            )

        base_sig = type_signature(base_prop)
        cur_sig = type_signature(cur_prop)
        if base_sig != cur_sig:
            changes.append(
                Change(
                    severity=BREAKING,
                    kind="type-changed",
                    context=label,
                    endpoint=endpoint,
                    status=status,
                    field_path=path,
                    message=(
                        f"the field '{name}' changed its type: {base_sig} -> {cur_sig}"
                    ),
                    impact=(
                        "a consumer that sends the old type is rejected, "
                        "a consumer that reads the old type misreads the new one"
                    ),
                    endpoints=used_by,
                )
            )

        # Nullability is compared only when the required-ness did not already
        # report the change - the two usually move together.
        base_nullable = accepts_null(base_prop)
        cur_nullable = accepts_null(cur_prop)
        if base_nullable != cur_nullable:
            breaks = (CONTEXT_RESPONSE in contexts and cur_nullable) or (
                CONTEXT_REQUEST in contexts and not cur_nullable
            )
            changes.append(
                Change(
                    severity=BREAKING if breaks else COMPATIBLE,
                    kind="nullable-changed",
                    context=label,
                    endpoint=endpoint,
                    status=status,
                    field_path=path,
                    message=(
                        f"the field '{name}' changed nullability: "
                        f"{'accepts null' if base_nullable else 'never null'} -> "
                        f"{'accepts null' if cur_nullable else 'never null'}"
                    ),
                    impact=(
                        "a consumer that reads it can now get null"
                        if cur_nullable
                        else "a consumer that sends null is now rejected"
                    ),
                    endpoints=used_by,
                )
            )

        base_enum = enum_values(base_prop)
        cur_enum = enum_values(cur_prop)
        if base_enum is not None and cur_enum is not None:
            gone = [value for value in base_enum if value not in cur_enum]
            if gone:
                changes.append(
                    Change(
                        severity=BREAKING,
                        kind="enum-value-removed",
                        context=label,
                        endpoint=endpoint,
                        status=status,
                        field_path=path,
                        message=(
                            f"the field '{name}' no longer accepts "
                            f"{', '.join(repr(value) for value in gone)}"
                        ),
                        impact="a consumer that sends that value is rejected",
                        endpoints=used_by,
                    )
                )

        base_nested = resolve_ref(baseline, base_prop)
        cur_nested = resolve_ref(current, cur_prop)
        if _is_object_schema(base_nested) and _is_object_schema(cur_nested):
            _compare_object(
                base_nested,
                cur_nested,
                endpoint,
                contexts,
                path,
                changes,
                status=status,
                endpoints=used_by,
                depth=depth + 1,
                seen=seen,
            )


def _compare_parameters(
    operation: dict[str, Any],
    current_operation: dict[str, Any],
    endpoint: str,
    changes: list[Change],
) -> None:
    base_params = {
        (param.get("name"), param.get("in")): param
        for param in (operation.get("parameters") or [])
        if isinstance(param, dict)
    }
    cur_params = {
        (param.get("name"), param.get("in")): param
        for param in (current_operation.get("parameters") or [])
        if isinstance(param, dict)
    }

    def key_of(item: tuple[Any, Any]) -> tuple[str, str]:
        return (str(item[0]), str(item[1]))

    for key in sorted(set(base_params) - set(cur_params), key=key_of):
        name, where = key
        was_required = bool(base_params[key].get("required"))
        changes.append(
            Change(
                severity=BREAKING if was_required else COMPATIBLE,
                kind="parameter-removed",
                context=CONTEXT_REQUEST,
                endpoint=endpoint,
                field_path=f"{where} '{name}'",
                message=f"the parameter '{name}' was removed",
                impact=(
                    "a consumer that sends it gets a 422"
                    if was_required
                    else "a consumer that sends it has it ignored"
                ),
            )
        )

    for key in sorted(set(cur_params) - set(base_params), key=key_of):
        name, where = key
        now_required = bool(cur_params[key].get("required"))
        changes.append(
            Change(
                severity=BREAKING if now_required else COMPATIBLE,
                kind="parameter-added",
                context=CONTEXT_REQUEST,
                endpoint=endpoint,
                field_path=f"{where} '{name}'",
                message=(
                    f"the parameter '{name}' was added"
                    + (" and is required" if now_required else "")
                ),
                impact=(
                    "a consumer that does not send it is rejected"
                    if now_required
                    else "a consumer that does not know it is unaffected"
                ),
            )
        )

    for key in sorted(set(base_params) & set(cur_params), key=key_of):
        name, where = key
        base_param = base_params[key]
        cur_param = cur_params[key]
        if bool(base_param.get("required")) != bool(cur_param.get("required")):
            now_required = bool(cur_param.get("required"))
            changes.append(
                Change(
                    severity=BREAKING,
                    kind="parameter-required-changed",
                    context=CONTEXT_REQUEST,
                    endpoint=endpoint,
                    field_path=f"{where} '{name}'",
                    message=(
                        f"the parameter '{name}' changed from "
                        f"{'required' if base_param.get('required') else 'optional'} to "
                        f"{'required' if now_required else 'optional'}"
                    ),
                    impact=(
                        "a consumer that omits it is now rejected"
                        if now_required
                        else "the contract changed and consumers must follow it"
                    ),
                )
            )
        base_sig = type_signature(base_param.get("schema", {}))
        cur_sig = type_signature(cur_param.get("schema", {}))
        if base_sig != cur_sig:
            changes.append(
                Change(
                    severity=BREAKING,
                    kind="parameter-type-changed",
                    context=CONTEXT_REQUEST,
                    endpoint=endpoint,
                    field_path=f"{where} '{name}'",
                    impact="a consumer that sends the old type is rejected",
                    message=f"the parameter '{name}' changed its type: {base_sig} -> {cur_sig}",
                )
            )


def _compare_paths(
    baseline: dict[str, Any],
    current: dict[str, Any],
    changes: list[Change],
) -> None:
    """The endpoints: which ones are gone, and which ones changed."""
    base_paths: dict[str, Any] = baseline.get("paths") or {}
    cur_paths: dict[str, Any] = current.get("paths") or {}

    for path in sorted(set(cur_paths) - set(base_paths)):
        changes.append(
            Change(
                severity=COMPATIBLE,
                kind="endpoint-added",
                context=CONTEXT_UNKNOWN,
                endpoint=path,
                field_path="",
                message=f"the endpoint '{path}' was added",
                impact="a consumer that does not know it is unaffected",
            )
        )

    for path, methods in base_paths.items():
        if path not in cur_paths:
            changes.append(
                Change(
                    severity=BREAKING,
                    kind="endpoint-removed",
                    context=CONTEXT_UNKNOWN,
                    endpoint=path,
                    field_path="",
                    message=f"the endpoint '{path}' was removed",
                    impact="a consumer that calls it gets a 404",
                )
            )
            continue
        cur_methods = cur_paths[path]
        if not isinstance(methods, dict) or not isinstance(cur_methods, dict):
            continue

        for method in sorted(set(cur_methods) - set(methods)):
            changes.append(
                Change(
                    severity=COMPATIBLE,
                    kind="method-added",
                    context=CONTEXT_UNKNOWN,
                    endpoint=f"{method.upper()} {path}",
                    field_path="",
                    message=f"the method '{method.upper()}' was added to '{path}'",
                    impact="a consumer that does not know it is unaffected",
                )
            )

        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            endpoint = f"{method.upper()} {path}"
            if method not in cur_methods:
                changes.append(
                    Change(
                        severity=BREAKING,
                        kind="method-removed",
                        context=CONTEXT_UNKNOWN,
                        endpoint=endpoint,
                        field_path="",
                        message=f"the method '{method.upper()}' was removed from '{path}'",
                        impact="a consumer that calls it gets a 405",
                    )
                )
                continue
            current_operation = cur_methods[method]
            if not isinstance(current_operation, dict):
                continue

            _compare_parameters(operation, current_operation, endpoint, changes)

            base_status = set((operation.get("responses") or {}).keys())
            cur_status = set((current_operation.get("responses") or {}).keys())
            for status in sorted(base_status - cur_status):
                changes.append(
                    Change(
                        severity=BREAKING,
                        kind="response-removed",
                        context=CONTEXT_RESPONSE,
                        endpoint=endpoint,
                        status=status,
                        field_path="",
                        message=f"the response '{status}' was removed",
                        impact="a consumer that handles that status never sees it",
                    )
                )

            base_responses = _response_schemas(operation)
            cur_responses = _response_schemas(current_operation)
            for status in sorted(set(base_responses) & set(cur_responses)):
                base_schema = base_responses[status]
                cur_schema = cur_responses[status]
                if "$ref" in base_schema or "$ref" in cur_schema:
                    # A named schema is compared where it is written down.
                    continue
                base_resolved = resolve_ref(baseline, base_schema)
                cur_resolved = resolve_ref(current, cur_schema)
                if _is_object_schema(base_resolved) and _is_object_schema(cur_resolved):
                    _compare_object(
                        base_resolved,
                        cur_resolved,
                        endpoint,
                        {CONTEXT_RESPONSE},
                        "",
                        changes,
                        status=status,
                    )

            base_requests = _request_schemas(operation)
            cur_requests = _request_schemas(current_operation)
            for base_schema, cur_schema in zip(
                base_requests, cur_requests, strict=False
            ):
                if "$ref" in base_schema or "$ref" in cur_schema:
                    continue
                base_resolved = resolve_ref(baseline, base_schema)
                cur_resolved = resolve_ref(current, cur_schema)
                if _is_object_schema(base_resolved) and _is_object_schema(cur_resolved):
                    _compare_object(
                        base_resolved,
                        cur_resolved,
                        endpoint,
                        {CONTEXT_REQUEST},
                        "",
                        changes,
                    )


def compare_specs(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[Change]:
    """Every difference between the baseline and the current schema."""
    changes: list[Change] = []

    _compare_paths(baseline, current, changes)

    base_schemas: dict[str, Any] = (baseline.get("components") or {}).get(
        "schemas"
    ) or {}
    cur_schemas: dict[str, Any] = (current.get("components") or {}).get("schemas") or {}
    usage = _usage_index(baseline)

    for name in sorted(set(cur_schemas) - set(base_schemas)):
        changes.append(
            Change(
                severity=COMPATIBLE,
                kind="schema-added",
                context=CONTEXT_UNKNOWN,
                endpoint=f"components.schemas.{name}",
                field_path="",
                message=f"the schema '{name}' was added to the contract",
                impact="a consumer that does not know it is unaffected",
            )
        )

    for name in sorted(base_schemas):
        roles = usage.get(name, {})
        endpoints = [endpoint for group in roles.values() for endpoint in group]
        contexts = set(roles) or {CONTEXT_UNKNOWN}
        if name not in cur_schemas:
            changes.append(
                Change(
                    severity=BREAKING if endpoints else COMPATIBLE,
                    kind="schema-removed",
                    context=_contexts_label(contexts),
                    endpoint=f"components.schemas.{name}",
                    field_path="",
                    message=f"the schema '{name}' was removed from the contract",
                    impact=(
                        "the endpoints that used it no longer describe it"
                        if endpoints
                        else "no endpoint used it"
                    ),
                    endpoints=endpoints,
                )
            )
            continue
        base_schema = base_schemas[name]
        cur_schema = cur_schemas[name]
        if not (_is_object_schema(base_schema) and _is_object_schema(cur_schema)):
            continue
        _compare_object(
            base_schema,
            cur_schema,
            f"components.schemas.{name}",
            contexts,
            "",
            changes,
            endpoints=endpoints,
        )

    return changes


# ---------------------------------------------------------------------------
# The legacy entry point
# ---------------------------------------------------------------------------


def diff_paths(
    baseline_paths: dict[str, Any],
    current_paths: dict[str, Any],
) -> list[str]:
    """Compare two sets of paths, in the message shape the repository uses.

    The integration suite calls this with the references already resolved. It
    is kept because it is the documented shape of the comparison; the gate
    itself uses `compare_specs`.
    """
    changes = compare_specs({"paths": baseline_paths}, {"paths": current_paths})

    messages: list[str] = []
    for change in changes:
        if change.severity != BREAKING:
            continue
        kind = change.kind
        name = change.field_path.rsplit(".", 1)[-1]
        if kind == "endpoint-removed":
            messages.append(f"BREAKING: Removed endpoint path: {change.endpoint}")
        elif kind == "method-removed":
            method, _, path = change.endpoint.partition(" ")
            messages.append(f"BREAKING: Removed method: {method} {path}")
        elif kind == "required-changed" and CONTEXT_REQUEST in change.context:
            if "to required" in change.message:
                messages.append(
                    f"BREAKING: Added required request fields in {change.endpoint}: "
                    f"{{'{name}'}}"
                )
            else:
                messages.append(
                    f"BREAKING: Removed required request fields in {change.endpoint}: "
                    f"{{'{name}'}}"
                )
        elif kind == "field-removed" and CONTEXT_REQUEST in change.context:
            messages.append(
                f"BREAKING: Removed required field '{name}' in {change.endpoint}"
            )
        elif kind == "type-changed" and CONTEXT_REQUEST in change.context:
            messages.append(
                f"BREAKING: Changed type of field '{name}' in {change.endpoint}"
            )
        elif kind == "field-removed" and CONTEXT_RESPONSE in change.context:
            messages.append(
                f"BREAKING: Removed response field '{name}' in {change.endpoint} "
                f"({change.status})"
            )
        elif kind == "type-changed" and CONTEXT_RESPONSE in change.context:
            messages.append(
                f"BREAKING: Changed response field type '{name}' in {change.endpoint} "
                f"({change.status})"
            )
    return messages


# ---------------------------------------------------------------------------
# Exporting the current schema
# ---------------------------------------------------------------------------


def export_current_schema(current_path: str | None = None) -> dict[str, Any]:
    """The schema of the application, or the one in a file."""
    if current_path:
        return load_schema(current_path)

    # Add apps/api to Python path for imports
    repo_root = Path(__file__).parent.parent.parent
    api_dir = repo_root / "apps" / "api"
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))

    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("API_ACCESS_KEY", "test-key")
    # Enable JWT auth so ALL conditional routers are included in the schema
    os.environ.setdefault("AUTH_JWT_ENABLED", "true")

    from api.main import app

    return app.openapi()


def _write_baseline(baseline_path: str, current_path: str | None = None) -> int:
    """Write the current schema as the baseline the diff compares against.

    The baseline carries the contract version, so the file says which
    contract it describes.
    """
    try:
        schema = export_current_schema(current_path)
    except Exception as e:  # noqa: BLE001 - importing the app can fail in many ways
        print(f"ERROR: Could not export schema from app: {e}")
        print("Provide --current path to pre-exported schema")
        return 1

    schema["x-api-contract-version"] = CONTRACT_VERSION

    target = Path(baseline_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # The baseline is a machine artifact: it is compared by the tool, not read
    # by a person. Written compact, it stays inside the size the repository
    # allows for an added file.
    target.write_text(
        json.dumps(schema, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"Wrote the baseline to {target} ({len(schema.get('paths', {}))} paths)")
    print("Commit it together with the change that broke the contract.")
    return 0


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


def _write_step_summary(breaking: list[Change]) -> None:
    """The breaking changes as a summary on the pull request."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = ["### API contract", "", f"**{len(breaking)} breaking change(s)**", ""]
    for change in breaking:
        lines.append(f"- `{change.location}` - {change.message}")
        lines.append(f"  - consumer impact: {change.impact}")
    lines.append("")
    lines.append("Accept the change on purpose with:")
    lines.append("")
    lines.append("```")
    lines.append("python scripts/api/openapi_diff.py --update-baseline")
    lines.append("```")
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenAPI schema diff for breaking changes"
    )
    parser.add_argument(
        "--baseline",
        default="docs/api-v1-baseline.json",
        help="Path to baseline schema",
    )
    parser.add_argument(
        "--current",
        default=None,
        help="Path to current schema (default: export from running app)",
    )
    parser.add_argument(
        "--generate-baseline",
        "--update-baseline",
        dest="update_baseline",
        action="store_true",
        help="Write the current schema as the baseline and exit",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat compatible changes as errors as well",
    )
    args = parser.parse_args()

    baseline_path = args.baseline

    if args.update_baseline:
        return _write_baseline(baseline_path, args.current)

    if not Path(baseline_path).exists():
        print(f"ERROR: Baseline schema not found: {baseline_path}")
        print("Run: python scripts/api/openapi_diff.py --update-baseline")
        return 1

    if args.current:
        current_schema = load_schema(args.current)
    else:
        # Try to export from running app
        print("INFO: No --current specified, attempting to export from app...")
        try:
            current_schema = export_current_schema()
        except Exception as e:  # noqa: BLE001 - importing the app can fail in many ways
            print(f"ERROR: Could not export schema from app: {e}")
            print("Provide --current path to pre-exported schema")
            return 1

    baseline_schema = load_schema(baseline_path)

    changes = compare_specs(baseline_schema, current_schema)
    breaking = [change for change in changes if change.severity == BREAKING]
    compatible = [change for change in changes if change.severity == COMPATIBLE]

    if breaking:
        print(f"\n[FAIL] Found {len(breaking)} breaking change(s):\n")
        for change in breaking:
            print(change.render())
            if os.getenv("GITHUB_ACTIONS"):
                print(change.annotation())
        print(
            "\nTo accept these changes intentionally, update the baseline:\n"
            "  python scripts/api/openapi_diff.py --update-baseline"
        )
        _write_step_summary(breaking)
        return 1

    if compatible and args.strict:
        print(f"\n[FAIL] Found {len(compatible)} compatible change(s) (--strict):\n")
        for change in compatible:
            print(change.render())
        return 1

    print("\n[PASS] No breaking changes detected. API contract is stable.")
    if compatible:
        print(f"[INFO] Compatible changes: {len(compatible)}")
        for change in compatible:
            print(f"  + {change.location} - {change.message}")
    else:
        print("[INFO] The contract is identical to the baseline.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
