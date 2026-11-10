from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationError:
    message: str


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    visited: set[str] = set()
    visiting: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in stack:
                idx = stack.index(node)
                cycles.append(stack[idx:] + [node])
            return
        visiting.add(node)
        stack.append(node)
        for dep in sorted(graph.get(node, set())):
            dfs(dep)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(graph.keys()):
        dfs(node)
    return cycles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Task Master tasks.json consistency."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(".taskmaster") / "tasks" / "tasks.json",
    )
    ns = parser.parse_args(list(argv) if argv is not None else None)

    path = ns.path
    if not path.exists():
        print(f"FAIL: missing {path}")
        return 1

    try:
        data = _load_json(path)
    except Exception as exc:
        print(f"FAIL: invalid JSON ({exc})")
        return 1

    if not isinstance(data, dict):
        print("FAIL: expected top-level object")
        return 1

    errors: list[ValidationError] = []

    for tag, payload in data.items():
        if not isinstance(payload, dict) or "tasks" not in payload:
            errors.append(ValidationError(message=f"{tag}: missing tasks list"))
            continue
        tasks = payload.get("tasks")
        if not isinstance(tasks, list):
            errors.append(ValidationError(message=f"{tag}: tasks is not a list"))
            continue

        seen_ids: set[str] = set()
        deps_graph: dict[str, set[str]] = {}

        for task in tasks:
            if not isinstance(task, dict):
                errors.append(ValidationError(message=f"{tag}: task is not an object"))
                continue
            raw_id = task.get("id")
            # The canonical TaskMaster shape writes NUMERIC task ids and STRING
            # dependencies, so an id may be an int or a str. What the validator
            # needs is an id it can compare a dependency against - and a
            # dependency is a string, so both sides are compared as strings.
            if isinstance(raw_id, bool) or not isinstance(raw_id, (int, str)):
                errors.append(
                    ValidationError(message=f"{tag}: task id missing/invalid")
                )
                continue
            task_id = str(raw_id).strip()
            if not task_id:
                errors.append(
                    ValidationError(message=f"{tag}: task id missing/invalid")
                )
                continue
            if task_id in seen_ids:
                errors.append(
                    ValidationError(message=f"{tag}: duplicate task id {task_id}")
                )
                continue
            seen_ids.add(task_id)

            raw_deps = task.get("dependencies", [])
            deps: set[str] = set()
            if raw_deps is None:
                raw_deps = []
            if isinstance(raw_deps, list):
                for dep in raw_deps:
                    if isinstance(dep, str) and dep.strip():
                        deps.add(dep.strip())
                    else:
                        errors.append(
                            ValidationError(
                                message=f"{tag}:{task_id}: invalid dependency {dep!r}"
                            )
                        )
            else:
                errors.append(
                    ValidationError(
                        message=f"{tag}:{task_id}: dependencies is not a list"
                    )
                )
            deps_graph[task_id] = deps

            subtasks = task.get("subtasks", [])
            if subtasks is None:
                subtasks = []
            if not isinstance(subtasks, list):
                errors.append(
                    ValidationError(message=f"{tag}:{task_id}: subtasks is not a list")
                )
                continue
            for sub in subtasks:
                if not isinstance(sub, dict):
                    errors.append(
                        ValidationError(
                            message=f"{tag}:{task_id}: subtask is not an object"
                        )
                    )
                    continue
                parent_id = sub.get("parentId")
                if parent_id is None:
                    # The canonical shape nests a subtask under its task and
                    # does not repeat the parent on the subtask. Nesting IS the
                    # parent, so there is nothing to check.
                    continue
                if isinstance(parent_id, (int, str)) and not isinstance(
                    parent_id, bool
                ):
                    parent_id = str(parent_id).strip()
                if parent_id != task_id:
                    errors.append(
                        ValidationError(
                            message=f"{tag}:{task_id}: subtask parentId mismatch ({parent_id!r})"
                        )
                    )

        for task_id, deps in deps_graph.items():
            for dep in deps:
                if dep not in seen_ids:
                    errors.append(
                        ValidationError(
                            message=f"{tag}:{task_id}: missing dependency {dep}"
                        )
                    )

        cycles = _detect_cycles(deps_graph)
        for cycle in cycles:
            errors.append(
                ValidationError(message=f"{tag}: dependency cycle {' -> '.join(cycle)}")
            )

    if errors:
        for e in errors[:200]:
            print(f"FAIL: {e.message}")
        return 1

    print("PASS: Task Master tasks.json is consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
