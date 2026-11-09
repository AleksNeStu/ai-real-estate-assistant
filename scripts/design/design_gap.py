"""
Design-artifact analyser for ai-real-estate-assistant.

Usage:
    python design_gap.py <path-to-artifact>            # file or directory
    python design_gap.py <path> --json                 # machine-readable

The artifact format is not known in advance, so nothing here assumes one:
the analyser extracts what is actually present in the text and compares it
against the repository's current surface.

It answers four questions:
  1. Tokens - which theme tokens does the artifact define, and how do they
     map onto the 83 tokens the repo has today?
  2. Palette - are the artifact's colours a re-skin of the current theme
     (nearest match exists) or a new colour system?
  3. Components - does the artifact mention components the repo does not have?
  4. Copy - does the artifact contain message keys that are not in the
     catalogue (which would need all nine locales)?
"""

import argparse
import json
import pathlib
import re
import sys

# The repository root, derived from where this file lives (scripts/design/),
# so the analyser runs from the root on any machine.
REPO = pathlib.Path(__file__).resolve().parents[2]
GLOBALS_CSS = REPO / "apps" / "web" / "src" / "app" / "globals.css"
COMPONENTS_DIR = REPO / "apps" / "web" / "src" / "components"
MESSAGES_EN = REPO / "apps" / "web" / "messages" / "en.json"

TEXT_SUFFIXES = {
    ".css",
    ".scss",
    ".less",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".mdx",
    ".html",
    ".svg",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
}

VAR_RE = re.compile(r"--([A-Za-z0-9_-]+)\s*:\s*([^;{}\n]+)")
VAR_USE_RE = re.compile(r"var\(\s*--([A-Za-z0-9_-]+)")
HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")
RGB_RE = re.compile(
    r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)"
)
HSL_RE = re.compile(r"hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%")
KEY_RE = re.compile(r"\b([a-z][a-zA-Z0-9]{2,})\.([a-zA-Z][a-zA-Z0-9_]{2,})\b")
# Tailwind-style raw triplets: "240 5.9% 10%" - a colour without a function call
TRIPLET_RE = re.compile(
    r"^\s*(\d{1,3}(?:\.\d+)?)\s+(\d{1,3}(?:\.\d+)?)%\s+(\d{1,3}(?:\.\d+)?)%\s*$"
)
JSX_RE = re.compile(r"</?([A-Z][A-Za-z0-9]{2,})")
IMPORT_RE = re.compile(r"@/components/[^\"']*/([A-Za-z0-9_-]+)")
CSS_CLASS_RE = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]{2,})")
COMPONENT_SUFFIXES = (
    "card",
    "button",
    "badge",
    "header",
    "panel",
    "modal",
    "table",
    "list",
    "tab",
    "input",
    "chart",
    "map",
    "tag",
    "title",
    "icon",
    "avatar",
    "tooltip",
    "dropdown",
    "select",
    "nav",
    "footer",
    "sidebar",
    "grid",
    "tile",
    "stat",
    "price",
    "row",
    "cell",
    "banner",
    "hero",
    "empty",
    "skeleton",
    "spinner",
    "field",
    "form",
    "section",
    "item",
    "group",
)
CSS_UTILITY_PREFIXES = (
    "flex",
    "grid",
    "block",
    "inline",
    "hidden",
    "absolute",
    "relative",
    "fixed",
    "sticky",
    "container",
    "text-",
    "bg-",
    "p-",
    "m-",
    "w-",
    "h-",
    "rounded",
    "border",
    "shadow",
    "gap-",
    "space-",
    "items-",
    "justify-",
    "font-",
    "leading-",
    "tracking-",
    "transition",
    "duration",
    "ease-",
    "hover",
    "focus",
    "group-",
    "peer-",
    "max-",
    "min-",
    "overflow-",
    "cursor-",
    "select-",
    "resize",
    "opacity-",
    "z-",
    "inset-",
    "top-",
    "left-",
    "right-",
    "bottom-",
    "order-",
    "col-",
    "row-",
    "space-x-",
)


# ---------------------------------------------------------------- colours
def hex_to_rgb(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) == 6:
        value += "ff"
    if len(value) != 8:
        return None
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4, 6))


def rgb_to_hsl(r, g, b):
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    lum = (mx + mn) / 2
    if mx == mn:
        h = s = 0.0
    else:
        d = mx - mn
        s = d / (2 - mx - mn) if lum > 0.5 else d / (mx + mn)
        if mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h *= 60
    return h, s * 100, lum * 100


def collect_colors(text):
    """-> list of (source, (h, s, lum)) for every colour literal in the text."""
    out = []
    for m in HEX_RE.finditer(text):
        rgba = hex_to_rgb(m.group(1))
        if rgba:
            r, g, b, _ = rgba
            out.append((m.group(0), rgb_to_hsl(r, g, b)))
    for m in RGB_RE.finditer(text):
        r, g, b = (float(m.group(i)) for i in (1, 2, 3))
        out.append((m.group(0), rgb_to_hsl(r, g, b)))
    for m in HSL_RE.finditer(text):
        h, s, lum = (float(m.group(i)) for i in (1, 2, 3))
        out.append((m.group(0), (h % 360, s, lum)))
    # Raw triplets - the way the current theme itself declares its colours
    for m in VAR_RE.finditer(text):
        t = TRIPLET_RE.match(m.group(2))
        if t:
            h, s, lum = (float(t.group(i)) for i in (1, 2, 3))
            out.append((f"{m.group(1)}: {t.group(0).strip()}", (h % 360, s, lum)))
    return out


def color_distance(a, b):
    dh = abs(a[0] - b[0])
    dh = min(dh, 360 - dh)
    return (dh * 2) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


# ---------------------------------------------------------------- repo side
def repo_tokens():
    css = GLOBALS_CSS.read_text(encoding="utf-8")
    tokens = {}
    for m in VAR_RE.finditer(css):
        tokens.setdefault(m.group(1), m.group(2).strip())
    return tokens


def repo_colors():
    css = GLOBALS_CSS.read_text(encoding="utf-8")
    return collect_colors(css)


def repo_components():
    names = {}
    for p in COMPONENTS_DIR.rglob("*.tsx"):
        if "__tests__" in p.parts:
            continue
        names[p.stem.lower()] = p.relative_to(COMPONENTS_DIR).as_posix()
    return names


def repo_message_keys():
    data = json.loads(MESSAGES_EN.read_text(encoding="utf-8"))

    def walk(node, prefix):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                yield from walk(value, path)
            else:
                yield path

    return set(walk(data, ""))


def repo_namespaces():
    data = json.loads(MESSAGES_EN.read_text(encoding="utf-8"))
    return set(data.keys())


# ---------------------------------------------------------------- artifact
def collect_files(target):
    if target.is_file():
        return [target]
    files = []
    for p in sorted(target.rglob("*")):
        if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
            files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = pathlib.Path(args.artifact)
    if not target.exists():
        print(f"artifact not found: {target}", file=sys.stderr)
        return 2

    files = collect_files(target)
    text_by_file = {}
    for p in files:
        try:
            text_by_file[p] = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

    artifact_tokens, token_sources = {}, {}
    for p, text in text_by_file.items():
        for m in VAR_RE.finditer(text):
            name = m.group(1)
            if name not in artifact_tokens:
                artifact_tokens[name] = m.group(2).strip()
                token_sources[name] = p.name

    used_vars = set()
    for text in text_by_file.values():
        used_vars.update(VAR_USE_RE.findall(text))

    artifact_colors = []
    for p, text in text_by_file.items():
        for literal, hsl in collect_colors(text):
            artifact_colors.append((literal, hsl, p.name))

    r_tokens = repo_tokens()
    r_colors = repo_colors()
    r_components = repo_components()
    r_keys = repo_message_keys()
    r_namespaces = repo_namespaces()

    # 1. token mapping
    exact = sorted(set(artifact_tokens) & set(r_tokens))
    only_artifact = sorted(set(artifact_tokens) - set(r_tokens))
    only_repo = sorted(set(r_tokens) - set(artifact_tokens))

    # 2. palette similarity
    nearest = []
    for literal, hsl, src in artifact_colors:
        if not r_colors:
            nearest.append((literal, None, src))
            continue
        best = min(r_colors, key=lambda c: color_distance(hsl, c[1]))
        nearest.append((literal, best, src))
    matched = sum(1 for n in nearest if n[1])

    # 3. components mentioned in the artifact
    mentioned = set()
    blob = "\n".join(text_by_file.values())
    blob_lower = blob.lower()
    for name in r_components:
        pascal = "".join(part.capitalize() for part in name.split("-"))
        if re.search(r"</?" + re.escape(pascal) + r"[\s/>]", blob) or re.search(
            r"[\s\"']" + re.escape(name) + r"[\s\"'/>]", blob_lower
        ):
            mentioned.add(name)
    unknown_components = set()
    for m in JSX_RE.finditer(blob):
        cand = m.group(1).lower()
        if cand not in r_components:
            unknown_components.add(m.group(1))
    for m in IMPORT_RE.finditer(blob):
        stem = pathlib.Path(m.group(1)).stem.lower()
        if stem not in r_components:
            unknown_components.add(m.group(1))
    for m in CSS_CLASS_RE.finditer(blob):
        raw = m.group(1)
        if raw.startswith(("http", "sm:", "md:", "lg:", "xl:")):
            continue
        if any(raw.startswith(p) for p in CSS_UTILITY_PREFIXES):
            continue
        stem = raw.lower()
        if stem in r_components:
            mentioned.add(stem)
            continue
        suffix_hit = stem.split("-")[-1] if "-" in stem else None
        is_componentish = any(
            raw.endswith(s[0].upper() + s[1:]) for s in COMPONENT_SUFFIXES
        ) or (suffix_hit in COMPONENT_SUFFIXES)
        if is_componentish and raw not in unknown_components:
            unknown_components.add(raw)

    # 4. message keys
    key_candidates = set()
    for m in KEY_RE.finditer(blob):
        ns, leaf = m.group(1), m.group(2)
        if ns in r_namespaces and f"{ns}.{leaf}" not in r_keys:
            key_candidates.add(f"{ns}.{leaf}")

    report = {
        "artifact": str(target),
        "files_scanned": len(text_by_file),
        "tokens": {
            "defined_in_artifact": len(artifact_tokens),
            "matches_repo_token": len(exact),
            "new_in_artifact": only_artifact,
            "repo_tokens_without_counterpart": only_repo,
            "exact_matches": exact,
        },
        "palette": {
            "color_literals": len(artifact_colors),
            "distinct_literals": len({c[0] for c in artifact_colors}),
            "closest_repo_match_available": matched,
        },
        "components": {
            "repo_components_mentioned": sorted(mentioned),
            "possible_new_components": sorted(unknown_components)[:40],
        },
        "copy": {
            "namespaces": len(r_namespaces),
            "missing_message_keys": sorted(key_candidates),
        },
        "token_sources": token_sources,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    t = report["tokens"]
    print(f"ARTIFACT: {target}")
    print(f"files scanned: {report['files_scanned']}")
    print()
    print(
        f"TOKENS  defined in artifact: {t['defined_in_artifact']}   "
        f"match repo token: {t['matches_repo_token']}   new: {len(t['new_in_artifact'])}"
    )
    if t["new_in_artifact"]:
        print("  new tokens:")
        for name in t["new_in_artifact"][:40]:
            print(f"    --{name}: {artifact_tokens[name][:60]}")
    print(
        f"  repo tokens with no counterpart in the artifact: {len(t['repo_tokens_without_counterpart'])}"
    )
    print()
    p = report["palette"]
    print(
        f"PALETTE  literals: {p['color_literals']} ({p['distinct_literals']} distinct), "
        f"with a repo match: {p['closest_repo_match_available']}"
    )
    seen = set()
    for literal, best, src in nearest[:24]:
        if literal in seen:
            continue
        seen.add(literal)
        target_hsl = (
            f"hsl({best[1][0]:.0f} {best[1][1]:.0f}% {best[1][2]:.0f}%)"
            if best
            else "?"
        )
        print(f"    {literal:<26} -> nearest repo {target_hsl}   ({src})")
    print()
    c = report["components"]
    print(
        f"COMPONENTS  repo components mentioned: {len(c['repo_components_mentioned'])}"
    )
    if c["possible_new_components"]:
        print(
            f"  names not in the repo: {', '.join(c['possible_new_components'][:20])}"
        )
    print()
    k = report["copy"]
    print(
        f"COPY  message keys in the artifact that the catalogue does not have: "
        f"{len(k['missing_message_keys'])}"
    )
    for key in k["missing_message_keys"][:30]:
        print(f"    {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
