# Troubleshooting (Windows & Cross‑platform)

## Windows: NumPy Import Error
```
ImportError: Unable to import required dependencies:
numpy: Error importing numpy: you should not try to import numpy from
        its source directory
```
**Fix**
```powershell
deactivate
Remove-Item -Recurse -Force .\.venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install --no-deps -e .
python -c "import numpy; print('NumPy OK')"
```

## Windows: Pandas C Extension Error
```
ModuleNotFoundError: No module named 'pandas._libs.pandas_parser'
```
**Fix**
```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-cache-dir --force-reinstall "pandas>=2.2.0,<2.3.0"
```

## Windows: Pydantic-core Error
```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```
**Fix Order**
```powershell
python -m pip install "numpy>=1.24.0,<2.0.0"
python -m pip install --no-cache-dir "pydantic-core>=2.14.0,<3.0.0"
python -m pip install --no-cache-dir "pandas>=2.2.0,<2.3.0"
python -m pip install -r requirements.txt
```

## Common Issues

**Port already in use**
```powershell
# Backend (8000)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Frontend (3000)
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**API Key not recognized**
- Ensure `.env` exists and is in project root
- Restart the app after editing `.env`
- Ensure `API_ACCESS_KEY` is set for the backend; the web app injects `X-API-Key` server-side via its `/api/v1/*` proxy

**ChromaDB persistence issues**
```powershell
Remove-Item -Recurse -Force .\chroma_db
# Restart app — database will be recreated
```

**CORS errors in the browser**
- In production, set `ENVIRONMENT=production` and pin `CORS_ALLOW_ORIGINS` to your frontend URL(s).
- For local dev, keep `ENVIRONMENT` not `production` (backend allows `*`).

**Local Ollama not detected**
- Ensure Ollama is running and reachable from the backend container/host (`OLLAMA_API_BASE`).
- The Settings > Models view shows `runtime_available=false` when the API cannot connect.

## CI Pipeline Failures

**Identify failing jobs**
```powershell
gh run list -R AleksNeStu/ai-real-estate-assistant --limit 10
gh run view -R AleksNeStu/ai-real-estate-assistant <run_id> --json jobs
```

**Fetch failed step logs**
```powershell
gh run view -R AleksNeStu/ai-real-estate-assistant <run_id> --log-failed
```

**Common failure patterns**
- Integration test flake: async indexing can race with shared in-memory Chroma state across tests.
- Coverage gates: missing diff/critical coverage on changed modules.
- Compose smoke: transient Docker startup or health check delays.

**Immediate actions**
- Re-run the workflow from the failed run if the error is clearly transient.
- Re-run locally using the CI commands in TESTING_GUIDE.md to confirm determinism.

## CI Rollback Procedure

**Rollback a bad CI change**
```powershell
git log -n 5
git revert <commit_sha>
git push origin dev
```

**Rollback a bad vector-store change**
```powershell
git log -n 5 -- vector_store/chroma_store.py
git revert <commit_sha>
git push origin dev
```
### ChromaDB metadata errors

Symptoms:
- Messages like "Error adding batch: Expected metadata value of type 'string', 'number', 'boolean' or 'null'".

Cause:
- Non‑primitive values (lists, dicts, complex objects, raw numpy types) in document metadata.

Fix:
- Ensure only primitives go into metadata (str/int/float/bool/None). Convert datetimes to ISO 8601 strings. Avoid nesting dicts/lists.
- The vector store layer sanitizes metadata before insertion.

## Analytics: Pandas RuntimeWarning in YoY calculation

```
RuntimeWarning: '<' not supported between instances of 'Timestamp' and 'int', sort order is undefined for incomparable objects.
```

Cause:
- YoY percentage was computed without guarding for missing or zero previous values, which could trigger invalid operations during series calculations.

Fix:
- Ensure `avg_price` is numeric and compute YoY safely with guards for missing and zero previous values.
- This is implemented in `analytics/market_insights.py` and avoids invalid comparisons during calculation.
