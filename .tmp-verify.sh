#!/usr/bin/env bash
# The live check of the release: what the public domain answers with.
set -uo pipefail

BASE=https://realty.kittray.com

echo "=== build ==="
curl -s -m 40 "$BASE/api/v1/capabilities" | python -c "
import json,sys
d=json.load(sys.stdin)
b=d.get('build',{})
print('sha       ', b.get('sha'))
print('built_at  ', b.get('built_at'))
print('deploy_run', b.get('deploy_run_id'))
"

echo
echo "=== the catalogue endpoint ==="
curl -s -m 40 "$BASE/api/v1/properties?limit=3" | python -c "
import json,sys
d=json.load(sys.stdin)
print('count', d.get('count'), 'has_more', d.get('has_more'))
for p in (d.get('properties') or [])[:3]:
    print(' -', p.get('id'), '|', p.get('title'), '|', p.get('city'))
"

echo
echo "=== the per-route metadata ==="
python - <<'PY'
import re, urllib.request

BASE = "https://realty.kittray.com"
ROUTES = ["/en", "/en/search", "/en/chat", "/en/market-trends", "/en/city-overview",
          "/en/agents", "/en/tools", "/en/knowledge", "/en/valuation", "/en/showcase",
          "/en/property/prop-0166"]


def fetch(path):
    request = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


for route in ROUTES:
    html = fetch(route)
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    description = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.S)
    canonical = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']', html, re.S)
    h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    types = sorted(set(re.findall(r'"@type"\s*:\s*"([^"]+)"', html)))
    alternates = sorted(set(re.findall(r'hrefLang="([^"]+)" href="([^"]+)"', html)))
    print(f"{route}")
    print(f"   title      {title.group(1).strip()[:70] if title else 'NONE'}")
    print(f"   description {(description.group(1).strip()[:60] if description else 'NONE')}")
    print(f"   canonical  {canonical.group(1) if canonical else 'NONE'}")
    print(f"   h1         {[h.strip()[:50] for h in h1][:2]}")
    print(f"   json-ld    {types}")
    if route.endswith("prop-0166"):
        print(f"   alternates {alternates[:3]}")
PY

echo
echo "=== the hreflang header (must not name the internal origin) ==="
curl -s -m 30 -D - -o /dev/null "$BASE/en" | grep -i "^link:" | head -c 400; echo

echo
echo "=== the sitemap ==="
curl -s -m 60 "$BASE/sitemap.xml" | python -c "
import re,sys
xml=sys.stdin.read()
urls=re.findall(r'<loc>([^<]*)</loc>', xml)
print('urls', len(urls))
print('with the catalogue:', sum(1 for u in urls if '/property/' in u))
print('sample:', urls[:3])
print('a listing:', [u for u in urls if '/property/' in u][:2])
"

echo
echo "=== llms.txt ==="
curl -s -m 40 "$BASE/llms.txt" | grep -E "^## |^- \[|listings" | head -20

echo
echo "=== the search ==="
curl -s -m 120 -X POST "$BASE/api/v1/search" -H "Content-Type: application/json" \
  -d '{"query":"two room flat in Krakow with a lift"}' | python -c "
import json,sys
d=json.load(sys.stdin)
print('results', d.get('count'))
if d.get('results'):
    print('first', d['results'][0]['property'].get('title'))
"
