# SPRAV Scripts

Systematic Pre-Release Acceptance Validation framework scripts.

## Overview

SPRAV provides a comprehensive framework for conducting exhaustive local testing before each release, ensuring functional, non-functional, architectural, and business-requirement validation.

## Scripts

| Script | Purpose |
|--------|---------|
| `run_validation.py` | Main orchestrator - runs all validations |
| `generate_report.py` | Generates markdown/HTML reports from results |
| `defect_tracker.py` | Manages defect logging and tracking |
| `risk_assessment.py` | Manages risk identification and mitigation |

## Quick Start

```bash
# Run full validation
python scripts/sprav/run_validation.py --release v1.0.0

# Quick validation (skip slow checks)
python scripts/sprav/run_validation.py --quick --release v1.0.0

# Run specific roles only
python scripts/sprav/run_validation.py --roles qa,architect --release v1.0.0

# Output as JSON
python scripts/sprav/run_validation.py --json --output results.json

# Generate HTML report
python scripts/sprav/generate_report.py --input results.json --output report.html
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All validations passed (GO) |
| 1 | Some validations failed or warnings (CONDITIONAL) |
| 2 | Critical blockers found (NO-GO) |

## Agent Roles

| Role | Focus |
|------|-------|
| `team-lead` | Orchestration, final report |
| `architect` | Code quality, patterns, API contracts |
| `qa` | Test coverage, functional testing |
| `analyst` | Requirements validation, user journeys |
| `automation` | CI/CD, security scans, Docker |
| `frontend` | UI/UX, accessibility, cross-browser |
| `backend` | API, performance, database |

## Output Formats

### Markdown
```bash
python scripts/sprav/run_validation.py --output sprav-report.md
```

### HTML
```bash
python scripts/sprav/run_validation.py --json --output results.json
python scripts/sprav/generate_report.py --input results.json --output report.html
```

### JSON
```bash
python scripts/sprav/run_validation.py --json --output results.json
```

## Integration with CI

Add to `.github/workflows/sprav.yml`:

```yaml
name: SPRAV Validation

on:
  workflow_dispatch:
    inputs:
      release:
        description: 'Release version'
        required: true

jobs:
  sprav:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run SPRAV
        run: python scripts/sprav/run_validation.py --release ${{ inputs.release }} --output sprav-report.md
      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: sprav-report
          path: sprav-report.md
```

## Templates

Located in `docs/templates/`:

| Template | Purpose |
|----------|---------|
| `sprav_report.md` | Full SPRAV report template |
| `defect_log.csv` | Defect tracking spreadsheet |
| `risk_matrix.md` | Risk assessment matrix |

## Agent Instructions

Located in `.claude/agents/`:

| File | Role |
|------|------|
| `sprav-team-lead.md` | Team Lead |
| `sprav-architect.md` | Architect |
| `sprav-qa.md` | QA Engineer |
| `sprav-analyst.md` | Business Analyst |
| `sprav-automation.md` | Automation Engineer |
| `sprav-frontend.md` | Frontend Developer |
| `sprav-backend.md` | Backend Developer |

## Example Workflow

```bash
# 1. Initialize SPRAV session
python scripts/sprav/run_validation.py --release v1.2.0 --output results.json --json

# 2. Review results
cat results.json | jq '.overall_status'

# 3. Generate HTML report for stakeholders
python scripts/sprav/generate_report.py --input results.json --output sprav-v1.2.0.html

# 4. Track any defects found
python scripts/sprav/defect_tracker.py --load defects.json --markdown

# 5. Complete risk assessment
python scripts/sprav/risk_assessment.py --load risks.json --markdown
```

## Related Documentation

- [CI Workflow](../../.github/workflows/ci.yml)
- [Makefile](../../Makefile)
