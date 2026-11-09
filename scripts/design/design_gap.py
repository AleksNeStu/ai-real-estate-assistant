"""
Design-artifact analyser for ai-real-estate-assistant.

Usage:
    python scripts/design/design_gap.py <path-to-artifact>      # file or directory
    python scripts/design/design_gap.py <path> --json           # machine-readable

The artifact the acceptance compares is the v2 prototype:

    python scripts/design/design_gap.py tmp/design/realt2/v2

The artifact format is not known in advance, so nothing here assumes one:
the analyser extracts what is actually present in the text and compares it
against the repository's current surface.

It answers four questions:
  1. Tokens - which theme tokens does the artifact define, and how do they
     map onto the tokens the repo has today? A token is read in all three
     forms the prototypes use: `--name: value`, `var(--name, #value)` and
     `'--name': '#value'`. A token the repo does not carry by name is
     matched by its colour, and only a token that has no counterpart in
     either sense is reported as new.
  2. Palette - are the artifact's colours a re-skin of the current theme or
     a new colour system? Every literal is compared with the repository's
     palette and measured against PALETTE_THRESHOLD; the literals outside
     it are listed with their distance and the file they come from.
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

# How close two colours have to be to count as the same colour. The unit is
# the squared distance in HSL: the hue counts double, so a colour that is a
# few percent off in lightness lands well inside this number and a different
# colour family lands an order of magnitude outside it.
PALETTE_THRESHOLD = 100.0

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
# The prototypes declare a token as a fallback of a var() call: var(--bg,#fff)
VAR_FALLBACK_RE = re.compile(r"var\(\s*--([A-Za-z0-9_-]+)\s*,\s*([^)]+?)\s*\)")
# ...and as a quoted property of a theme object: {'--bg':'#09090b'}
VAR_QUOTED_RE = re.compile(r"['\"]--([A-Za-z0-9_-]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]")
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


def token_color(value):
    """The (h, s, l) a token value carries, or None when it is not a colour."""
    value = value.strip()
    triplet = TRIPLET_RE.match(value)
    if triplet:
        return (
            float(triplet.group(1)) % 360,
            float(triplet.group(2)),
            float(triplet.group(3)),
        )
    if value.startswith("#"):
        rgba = hex_to_rgb(value)
        if rgba:
            return rgb_to_hsl(*rgba[:3])
    return None


def artifact_token_definitions(text):
    """Every token the artifact declares, in the three forms it uses.

    A var() fallback and a quoted theme property are definitions too: the
    prototypes never declare a token the way a stylesheet does, and reading
    only the stylesheet form leaves the comparison empty.
    """
    found = {}
    for pattern in (VAR_RE, VAR_FALLBACK_RE, VAR_QUOTED_RE):
        for m in pattern.finditer(text):
            found.setdefault(m.group(1), m.group(2).strip())
    return found


# ---------------------------------------------------------------- repo side
def repo_tokens():
    css = GLOBALS_CSS.read_text(encoding="utf-8")
    tokens = {}
    for m in VAR_RE.finditer(css):
        tokens.setdefault(m.group(1), m.group(2).strip())
    return tokens


def repo_token_colors():
    """The colours the repository's own tokens carry, per theme.

    A token is declared twice - once per theme - so a name maps to a list of
    colours, and a token is a match for whichever theme is closest.
    """
    css = GLOBALS_CSS.read_text(encoding="utf-8")
    colors = {}
    for m in VAR_RE.finditer(css):
        color = token_color(m.group(2).strip())
        if color is not None:
            colors.setdefault(m.group(1), []).append(color)
    return colors


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
    ap = argparse.ArgumentParser(
        description=(
            "Compare a design artifact with the application's current surface. "
            "The artifact the acceptance reads is the v2 prototype: "
            "python scripts/design/design_gap.py tmp/design/realt2/v2"
        )
    )
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

    def source_of(path):
        """Where a literal came from, relative to the artifact's own root."""
        try:
            return path.relative_to(target).as_posix()
        except ValueError:
            return path.name

    artifact_tokens, token_sources = {}, {}
    for p, text in text_by_file.items():
        for name, value in artifact_token_definitions(text).items():
            if name not in artifact_tokens:
                artifact_tokens[name] = value
                token_sources[name] = source_of(p)

    used_vars = set()
    for text in text_by_file.values():
        used_vars.update(VAR_USE_RE.findall(text))

    artifact_colors = []
    for p, text in text_by_file.items():
        for literal, hsl in collect_colors(text):
            artifact_colors.append((literal, hsl, source_of(p)))

    r_tokens = repo_tokens()
    r_token_colors = repo_token_colors()
    r_colors = repo_colors()
    r_components = repo_components()
    r_keys = repo_message_keys()
    r_namespaces = repo_namespaces()

    # 1. token mapping. A token the repo does not carry by name is matched by
    #    its colour; only a token with no counterpart in either sense is new.
    exact = sorted(set(artifact_tokens) & set(r_tokens))
    aliases, unmatched = [], []
    for name in sorted(artifact_tokens):
        if name in r_tokens:
            continue
        color = token_color(artifact_tokens[name])
        if color is None:
            # Not a colour - a filter, a radius, a size. There is no colour
            # to match, so it is reported on its own, not as palette drift.
            unmatched.append(
                {"token": name, "value": artifact_tokens[name], "colour": False}
            )
            continue
        best_distance = None
        candidates = []
        for repo_name, colors in r_token_colors.items():
            distance = min(color_distance(color, c) for c in colors)
            if best_distance is None or distance < best_distance:
                best_distance, candidates = distance, [repo_name]
            elif distance <= best_distance + 1e-6:
                candidates.append(repo_name)
        if best_distance is not None and best_distance <= PALETTE_THRESHOLD:
            aliases.append(
                {
                    "token": name,
                    "repo_tokens": sorted(candidates),
                    "distance": round(best_distance, 3),
                }
            )
        else:
            unmatched.append(
                {"token": name, "value": artifact_tokens[name], "colour": True}
            )

    claimed = {name for alias in aliases for name in alias["repo_tokens"]}
    only_repo = sorted(
        name for name in r_tokens if name not in exact and name not in claimed
    )

    # 2. palette similarity. Every literal is measured against the repository's
    #    palette, and the ones outside the threshold are named.
    nearest = {}
    for literal, hsl, src in artifact_colors:
        if not r_colors:
            nearest[literal] = (None, None, src)
            continue
        best = min(r_colors, key=lambda c: color_distance(hsl, c[1]))
        distance = color_distance(hsl, best[1])
        known = nearest.get(literal)
        if known is None or (known[1] is not None and distance < known[1]):
            nearest[literal] = (best, distance, src)
    matched = sum(1 for n in nearest.values() if n[0])
    outside = sorted(
        (
            {
                "literal": literal,
                "distance": round(distance, 2),
                "nearest_repo": best[0],
                "source": src,
            }
            for literal, (best, distance, src) in nearest.items()
            if distance is None or distance > PALETTE_THRESHOLD
        ),
        key=lambda row: -row["distance"],
    )
    within = len(nearest) - len(outside)

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
            "aliases_to_repo_token": aliases,
            "new_in_artifact": unmatched,
            "repo_tokens_without_counterpart": only_repo,
            "exact_matches": exact,
        },
        "palette": {
            "color_literals": len(artifact_colors),
            "distinct_literals": len(nearest),
            "closest_repo_match_available": matched,
            "threshold": PALETTE_THRESHOLD,
            "within_threshold": within,
            "outside_threshold": outside,
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
        f"match repo token by name: {t['matches_repo_token']}   "
        f"match repo token by colour: {len(t['aliases_to_repo_token'])}   "
        f"new: {len(t['new_in_artifact'])}"
    )
    for alias in t["aliases_to_repo_token"]:
        print(
            f"    --{alias['token']:<10} -> {', '.join('--' + n for n in alias['repo_tokens'])}"
            f"   distance {alias['distance']}"
        )
    for row in t["new_in_artifact"]:
        kind = "colour" if row["colour"] else "not a colour"
        print(f"    --{row['token']:<10} no counterpart ({kind}): {row['value'][:60]}")
    print(
        f"  repo tokens with no counterpart in the artifact: {len(t['repo_tokens_without_counterpart'])}"
    )
    print()
    p = report["palette"]
    print(
        f"PALETTE  literals: {p['color_literals']} ({p['distinct_literals']} distinct), "
        f"within the threshold: {p['within_threshold']}, "
        f"outside: {len(p['outside_threshold'])}"
    )
    print(f"  threshold: {p['threshold']} (squared HSL distance)")
    for row in p["outside_threshold"]:
        print(
            f"    {row['literal']:<26} distance {row['distance']:>9}   "
            f"nearest repo {row['nearest_repo']:<28} ({row['source']})"
        )
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
