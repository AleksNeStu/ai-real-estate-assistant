import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parents[2]
web = root / "apps" / "web" / "src"

# 1. Routes
routes = []
app_dir = web / "app"
for p in app_dir.rglob("page.tsx"):
    rel = p.relative_to(app_dir).as_posix()
    rel = rel.removesuffix("/page.tsx")
    rel = re.sub(r"^\[\.\.\.locale\]", "", rel) or "/"
    routes.append(rel.replace("[locale]", ":locale").replace("[]", ""))
routes.sort()

# 2. Components by category
components = {}
comp_dir = web / "components"
for p in comp_dir.rglob("*.tsx"):
    if "__tests__" in p.parts or p.name.endswith(".test.tsx"):
        continue
    rel = p.relative_to(comp_dir).as_posix()
    category = rel.split("/")[0] if "/" in rel else "(root)"
    components.setdefault(category, []).append(rel)
component_count = sum(len(v) for v in components.values())

# 3. i18n namespaces
messages = json.loads((web.parent / "messages" / "en.json").read_text(encoding="utf-8"))
namespaces = sorted(messages.keys())


def count_leaves(node):
    if isinstance(node, dict):
        return sum(count_leaves(v) for v in node.values())
    return 1


locale_files = sorted((web.parent / "messages").glob("*.json"))
locale_leaf_counts = {}
for f in locale_files:
    data = json.loads(f.read_text(encoding="utf-8"))
    locale_leaf_counts[f.stem] = count_leaves(data)

# 4. Tokens
css = (app_dir / "globals.css").read_text(encoding="utf-8")
tokens = sorted(set(re.findall(r"^\s*(--[a-z0-9-]+):", css, re.MULTILINE)))

# 5. Tests per area
tests = {"jest": 0, "playwright": 0, "pytest": 0}
for p in (web).rglob("*.test.tsx"):
    tests["jest"] += 1
for p in (web).rglob("*.test.ts"):
    tests["jest"] += 1
e2e = root / "e2e"
if e2e.exists():
    for p in e2e.rglob("*.spec.ts"):
        tests["playwright"] += 1
api_tests = root / "apps" / "api" / "tests"
for p in api_tests.rglob("test_*.py"):
    tests["pytest"] += 1

print(f"=== ROUTES ({len(routes)}) ===")
for r in routes:
    print(" ", r)

print()
print(f"=== COMPONENTS ({component_count} files) by category ===")
for cat in sorted(components):
    print(f"  {cat:<22} {len(components[cat])}")

print()
print(f"=== I18N namespaces ({len(namespaces)}) ===")
print(", ".join(namespaces))
print("leaves per locale:")
for k in sorted(locale_leaf_counts):
    print(f"   {k:<4} {locale_leaf_counts[k]}")

print()
print(f"=== THEME TOKENS ({len(tokens)}) ===")
print(", ".join(tokens))

print()
print("=== TEST FILES ===")
print(tests)
