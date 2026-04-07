from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Set
from defusedxml import ElementTree


@dataclass(frozen=True)
class FileCoverage:
    covered_lines: Set[int]
    all_lines: Set[int]

    def covered_count(self, lines: Iterable[int]) -> int:
        return sum(1 for ln in lines if ln in self.covered_lines)


def load_coverage_xml(path: Path) -> Dict[str, FileCoverage]:
    tree = ElementTree.parse(path)
    root = tree.getroot()

    files: Dict[str, Set[int]] = {}
    covered: Dict[str, Set[int]] = {}

    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename")
        if not filename:
            continue
        normalized = filename.replace("\\", "/")
        lines_el = cls.find("lines")
        if lines_el is None:
            continue
        for ln in lines_el.findall("line"):
            number_str = ln.attrib.get("number")
            hits_str = ln.attrib.get("hits")
            if not number_str:
                continue
            number = int(number_str)
            files.setdefault(normalized, set()).add(number)
            if hits_str is not None and int(hits_str) > 0:
                covered.setdefault(normalized, set()).add(number)

    result: Dict[str, FileCoverage] = {}
    for filename, all_lines in files.items():
        result[filename] = FileCoverage(
            covered_lines=covered.get(filename, set()), all_lines=all_lines
        )
    return result


def run_git_diff(base_ref: str | None) -> str:
    if base_ref:
        cmd = ["git", "diff", "--unified=0", f"{base_ref}...HEAD"]
    else:
        if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
            cmd = ["git", "diff", "--unified=0", "--ignore-all-space", "HEAD~1...HEAD"]
        else:
            cmd = ["git", "diff", "--unified=0", "--ignore-all-space", "HEAD"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout or ""


def parse_changed_lines_from_diff(diff_text: str) -> Dict[str, Set[int]]:
    changed: Dict[str, Set[int]] = {}
    current_file: str | None = None
    current_line = 0
    active = False

    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            if raw.startswith("+++ b/"):
                current_file = raw[len("+++ b/") :].strip()
            else:
                current_file = None
            active = False
            continue

        if raw.startswith("@@ "):
            if current_file is None:
                continue
            header = raw
            try:
                plus_part = header.split("+", 1)[1]
                plus_range = plus_part.split(" ", 1)[0]
                if "," in plus_range:
                    start_str, _count_str = plus_range.split(",", 1)
                else:
                    start_str = plus_range
                current_line = int(start_str)
                active = True
            except Exception:
                active = False
            continue

        if not active or current_file is None:
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            changed.setdefault(current_file, set()).add(current_line)
            current_line += 1
            continue
        if raw.startswith("-") and not raw.startswith("---"):
            continue
        current_line += 1

    return changed


def diff_coverage_percent(
    coverage_by_file: Mapping[str, FileCoverage],
    changed_lines: Mapping[str, Set[int]],
) -> tuple[int, int, float]:
    total = 0
    covered = 0
    prefixes = ("apps/api/",)
    for file_path, lines in changed_lines.items():
        normalized = file_path.replace("\\", "/")
        candidates = [normalized]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                candidates.append(normalized[len(prefix) :])
        fc = None
        for candidate in candidates:
            if candidate in coverage_by_file:
                fc = coverage_by_file[candidate]
                break
        if fc is None:
            total += len(lines)
            continue
        relevant_lines = set(ln for ln in lines if ln in fc.all_lines)
        if not relevant_lines:
            continue
        total += len(relevant_lines)
        covered += fc.covered_count(relevant_lines)
    percent = 100.0 if total == 0 else (covered / total) * 100.0
    return covered, total, percent


def critical_coverage_percent(
    coverage_by_file: Mapping[str, FileCoverage],
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
) -> tuple[int, int, float]:
    def _matches_any(value: str, patterns: Sequence[str]) -> bool:
        return any(fnmatch.fnmatch(value, pat) for pat in patterns)

    total = 0
    covered = 0
    for filename, fc in coverage_by_file.items():
        if include_globs and not _matches_any(filename, include_globs):
            continue
        if exclude_globs and _matches_any(filename, exclude_globs):
            continue
        total += len(fc.all_lines)
        covered += len(fc.covered_lines & fc.all_lines)

    percent = 100.0 if total == 0 else (covered / total) * 100.0
    return covered, total, percent


def _print_summary(label: str, covered: int, total: int, percent: float) -> None:
    print(f"{label}: {covered}/{total} lines covered ({percent:.2f}%)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Coverage gates for changed lines and critical paths."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    diff_parser = sub.add_parser(
        "diff", help="Enforce minimum coverage on changed lines."
    )
    diff_parser.add_argument("--coverage-xml", type=Path, default=Path("coverage.xml"))
    diff_parser.add_argument("--base-ref", type=str, default=None)
    diff_parser.add_argument("--include", action="append", default=[])
    diff_parser.add_argument("--exclude", action="append", default=[])
    diff_parser.add_argument("--min-coverage", type=float, default=90.0)

    crit_parser = sub.add_parser(
        "critical", help="Enforce minimum coverage on a critical path subset."
    )
    crit_parser.add_argument("--coverage-xml", type=Path, default=Path("coverage.xml"))
    crit_parser.add_argument("--include", action="append", default=[])
    crit_parser.add_argument("--exclude", action="append", default=[])
    crit_parser.add_argument("--min-coverage", type=float, default=90.0)

    args = parser.parse_args(list(argv) if argv is not None else None)

    coverage_by_file = load_coverage_xml(args.coverage_xml)

    if args.cmd == "diff":
        diff_text = run_git_diff(args.base_ref)
        changed_lines = parse_changed_lines_from_diff(diff_text)
        changed_lines = {k: v for k, v in changed_lines.items() if k.endswith(".py")}

        include_globs = list(args.include)
        exclude_globs = list(args.exclude)
        if include_globs or exclude_globs:
            prefixes = ("apps/api/",)

            def _candidates(value: str) -> list[str]:
                normalized = value.replace("\\", "/")
                items = [normalized]
                for prefix in prefixes:
                    if normalized.startswith(prefix):
                        items.append(normalized[len(prefix) :])
                return items

            filtered: Dict[str, Set[int]] = {}
            for filename, lines in changed_lines.items():
                candidates = _candidates(filename)
                if include_globs and not any(
                    fnmatch.fnmatch(candidate, pat)
                    for candidate in candidates
                    for pat in include_globs
                ):
                    continue
                if exclude_globs and any(
                    fnmatch.fnmatch(candidate, pat)
                    for candidate in candidates
                    for pat in exclude_globs
                ):
                    continue
                filtered[filename] = lines
            changed_lines = filtered

        covered, total, percent = diff_coverage_percent(coverage_by_file, changed_lines)
        _print_summary("Diff coverage", covered, total, percent)
        if percent + 1e-9 < float(args.min_coverage):
            print(
                f"FAIL: Diff coverage {percent:.2f}% < {float(args.min_coverage):.2f}%"
            )
            return 2
        return 0

    covered, total, percent = critical_coverage_percent(
        coverage_by_file=coverage_by_file,
        include_globs=list(args.include),
        exclude_globs=list(args.exclude),
    )
    _print_summary("Critical coverage", covered, total, percent)
    if total == 0:
        print("FAIL: Critical coverage set is empty.")
        return 2
    if percent + 1e-9 < float(args.min_coverage):
        print(
            f"FAIL: Critical coverage {percent:.2f}% < {float(args.min_coverage):.2f}%"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
