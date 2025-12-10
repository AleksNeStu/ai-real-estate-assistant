#!/usr/bin/env bash
set -euo pipefail

paths=(
  'artifacts/**'
  'node_modules/**'
  'chroma_db/**'
  '.preferences/**'
  'coverage_html/**'
  'playwright-report/**'
  'server.log'
  'resp.html'
  'package-lock.json'
)

args=()
for p in "${paths[@]}"; do
  args+=("--path-glob=$p")
done

git filter-repo --force --invert-paths "${args[@]}"

echo "Run: git push origin --force --all"
echo "Run: git push origin --force --tags"

