# Community Health Metrics

## Overview

This document defines the community health metrics tracked for the AI Real Estate Assistant Community Edition (CE). These metrics align with the project roadmap goals and help measure project growth and engagement.

## Target Metrics (Roadmap Goals)

| Metric | Target | Timeline |
|--------|--------|----------|
| GitHub Stars | >= 100 | 6 months post-launch |
| First External PR Merged | >= 1 | 3 months post-launch |
| Doc Site Visits Growth | Month-over-month increase | Ongoing |
| GitHub Issues (good first issue) | >= 5 open at any time | Ongoing |
| Fork Count | >= 20 | 6 months post-launch |
| Contributors (external) | >= 3 | 6 months post-launch |

## Weekly Tracking

### GitHub Repository Metrics

Collected weekly (every Monday) from GitHub Insights:

| Metric | Source | Collection Method |
|--------|--------|-------------------|
| Stars | `github.com/AleksNeStu/ai-real-estate-assistant` | Manual or GitHub API |
| Forks | GitHub Insights | Manual or GitHub API |
| Open Issues | GitHub Issues tab | Manual |
| Closed Issues (weekly) | GitHub Insights | Manual |
| Open PRs | GitHub PRs tab | Manual |
| Merged PRs (weekly) | GitHub Insights | Manual |
| Unique Contributors | GitHub Contributors graph | Manual |

### Collection via GitHub CLI

```bash
# Stars and forks
gh repo view AleksNeStu/ai-real-estate-assistant --json stargazerCount,forkCount

# Open issues with "good first issue" label
gh issue list --repo AleksNeStu/ai-real-estate-assistant --label "good first issue" --state open

# Recent PRs
gh pr list --repo AleksNeStu/ai-real-estate-assistant --state all --limit 10

# Contributors
gh api repos/AleksNeStu/ai-real-estate-assistant/contributors --jq '.[].login'
```

## External PR Tracking

Track every community pull request:

| Data Point | Description |
|------------|-------------|
| PR Number | GitHub PR # |
| Author | GitHub username |
| Opened Date | When the PR was submitted |
| Merged Date | When it was merged (or "Open"/"Closed") |
| Time to Merge | Days from open to merge |
| Issue Link | Associated issue number |
| Category | Connector / UI / Docs / Bug fix |

### Time-to-First-Review SLA

- External PRs should receive initial review within **48 hours**
- Follow-up review within **24 hours** after author response
- Target merge within **7 days** for "good first issue" PRs

## Monthly Community Health Report

A monthly report is generated using the template at `docs/community/monthly-report-template.md`.

Reports are stored at: `docs/community/reports/YYYY-MM.md`

### Key Monthly Indicators

1. **Star Growth Rate**: New stars this month / total stars
2. **PR Velocity**: Average time from PR open to merge
3. **Issue Resolution Rate**: Issues closed / issues opened
4. **Community Engagement**: Unique commenters on issues/PRs
5. **Documentation Visits**: (if analytics enabled) Page views on docs

## Data Storage

- Weekly snapshots stored in this repo at `docs/community/data/weekly-snapshots.json`
- Monthly reports at `docs/community/reports/YYYY-MM.md`
- No external analytics services required (GitHub-native)

## Automated Star-Growth Metrics

The `README.md` star-history chart is rendered live by the hosted `api.star-history.com` SVG endpoint (no workflow, no PAT, no orphan branch). The previous self-hosted workflow (`.github/workflows/star-history.yml` + `render_star_history.py`) was removed on 2026-08-15 because:

1. The `GH_STAR_TOKEN` fine-grained PAT lacked the `Starring: Read` scope needed for GraphQL `stargazers` (verified empirically — returns `FORBIDDEN: Resource not accessible by personal access token`).
2. The workflow's `git switch --orphan star-history` + `git push --force` pattern created a fresh orphan branch every run, silently destroying previously-pushed SVGs.

### Data Location

| File | Description |
|------|-------------|
| `https://api.star-history.com/svg?repos=AleksNeStu/ai-real-estate-assistant&type=Date` | Live hosted star-history chart (rendered by `star-history.com` on demand) |
| `docs/community/metrics/latest.json` | **Immutable legacy snapshot** from 2026-05-04 — historical reference only |

### growth-metrics.json Schema

```json
{
  "collected_at": "2026-07-20T12:00:00+00:00",
  "repository": "AleksNeStu/ai-real-estate-assistant",
  "total_stars": 284,
  "new_stars_1d": 2,
  "new_stars_7d": 5,
  "new_stars_30d": 23,
  "traffic_available": true,
  "traffic_error": null,
  "views_14d": 1200,
  "unique_visitors_14d": 450,
  "referrers": [
    { "referrer": "github.com", "count": 800, "uniques": 300 }
  ]
}
```

### GitHub Traffic Data Limitations

**Important:** GitHub traffic endpoints (`/traffic/views`, `/traffic/popular/referrers`) have specific constraints:

1. **Rolling 14-day window**: Traffic data covers only the last 14 days. Historical trends cannot be reconstructed from a single snapshot.
2. **Domain-level attribution**: Referrer data identifies source domains only (e.g., `github.com`, `google.com`). Individual pages or UTM parameters are not exposed.
3. **Campaign correlation**: GitHub does not provide campaign attribution. Correlating traffic spikes to specific posts, shares, or events requires external tracking (e.g., UTM parameters on outgoing links).
4. **Traffic errors**: 403/404/429 responses are expected for some configurations and are handled gracefully — `traffic_available` will be `false` and `traffic_error` will contain the error message.


## Automation Opportunities

Future improvements (contributions welcome):

- [ ] GitHub Action to collect weekly metrics automatically
- [ ] Dashboard generation from snapshot data
- [ ] Slack/Discord notification on milestones
- [ ] Badge integration (stars, contributors) in README
