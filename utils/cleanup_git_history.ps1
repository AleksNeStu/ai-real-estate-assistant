$paths = @(
  'artifacts/**',
  'node_modules/**',
  'chroma_db/**',
  '.preferences/**',
  'coverage_html/**',
  'playwright-report/**',
  'server.log',
  'resp.html',
  'package-lock.json'
)

$args = @()
foreach ($p in $paths) { $args += "--path-glob=$p" }

git filter-repo --force --invert-paths $args

Write-Host "Run: git push origin --force --all" -ForegroundColor Yellow
Write-Host "Run: git push origin --force --tags" -ForegroundColor Yellow

