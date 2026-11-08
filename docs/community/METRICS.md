# Community Health Metrics

## Overview

This document defines the community health metrics tracked for the AI Real Estate Assistant Community Edition (CE). These metrics align with the project roadmap goals and help measure project growth and engagement.

## Target Metrics (Roadmap Goals)

| Metric | Target | Timeline | Current (2026-11-08) | Status |
|--------|--------|----------|------------------------|--------|
| GitHub Stars | >= 100 | 6 months post-launch | 321 | Reached |
| First External PR Merged | >= 1 | 3 months post-launch | 0 | Not reached |
| Doc Site Visits Growth | Month-over-month increase | Ongoing | 706 views / 272 uniques (14 days) | Measured, no trend yet |
| GitHub Issues (good first issue) | >= 5 open at any time | Ongoing | 0 open issues in total | Not met — no onboarding funnel |
| Fork Count | >= 20 | 6 months post-launch | 119 | Reached |
| Contributors (external) | >= 3 | 6 months post-launch | 3 | Reached |

The two unmet targets are the same gap seen from two sides: nobody outside the
owner contributes, because there is nothing for them to pick up — the tracker
holds **zero** open issues, so a newcomer finds no entry point. The external
contributors that did exist (`stephenalexbrowne`, `Jwrede`, `KrabbiAI`) came in
with their own pull requests rather than from an issue.

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

> **There is no collection workflow in this repository.** The `community-metrics`
> workflow was removed together with `star-history` on 2026-08-15, and this
> repository is frozen for demo purposes, so adding one back would be new code
> rather than a fix. Until that changes, the weekly snapshot is collected by
> hand and committed — see [Automation Opportunities](#automation-opportunities).

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

- Weekly snapshots: `docs/community/metrics/<ISO-week>.json` and the
  human-readable `<ISO-week>.md` next to it
- Latest snapshot pointer: `docs/community/metrics/latest.json` (a copy of the
  most recent week, not a frozen legacy file)
- Monthly reports: `docs/community/reports/YYYY-MM.md` — the directory is
  created when the first report is written from
  `docs/community/monthly-report-template.md`
- No external analytics services required (GitHub-native)

### Current Snapshots

| File | Week | Note |
|------|------|------|
| `docs/community/metrics/2026-W18.json` / `.md` | 2026-W18 | Superseded — it carried placeholder zeroes from a workflow that could not read the repository |
| `docs/community/metrics/2026-W45.json` / `.md` | 2026-W45 | The first snapshot collected directly from the GitHub API (321 stars, 119 forks, 706 views / 272 uniques over 14 days) |
| `docs/community/metrics/latest.json` | 2026-W45 | Copy of the newest week |

## Star History and Growth-Metrics Data

The `star-history` workflow, its `render_star_history.py` script and the orphan
branch it pushed were removed on 2026-08-15:

1. The `GH_STAR_TOKEN` fine-grained PAT lacked the `Starring: Read` scope needed
   for the GraphQL `stargazers` query (verified empirically — returns
   `FORBIDDEN: Resource not accessible by personal access token`).
2. The workflow's `git switch --orphan star-history` + `git push --force` pattern
   created a fresh orphan branch every run, silently destroying previously-pushed
   SVGs.

The `README.md` no longer embeds a star-history chart, and the `community-metrics`
workflow that wrote `growth-metrics.json` went with it. Star growth is now
recorded in the weekly snapshots described above, and the repository has no
orphan branches (`dev` and `main` only).

### Weekly snapshot schema

`docs/community/metrics/<ISO-week>.json`:

```json
{
  "collected_at": "2026-11-08T17:32:48.536Z",
  "repository": "AleksNeStu/ai-real-estate-assistant",
  "week": "2026-W45",
  "repo_stats": {
    "stars": 321,
    "forks": 119,
    "watchers": 6,
    "open_issues": 0,
    "license": "MIT",
    "default_branch": "dev",
    "language": "Python"
  },
  "issue_stats": {
    "open_by_label": { "bug": 0, "enhancement": 0, "good first issue": 0, "help wanted": 0, "question": 0 },
    "total_open": 0
  },
  "pr_stats": { "open_prs": 0, "total_merged": null },
  "contributors": { "total": 6 },
  "star_growth": {
    "new_stars_1d": 0,
    "new_stars_7d": 1,
    "new_stars_30d": 8,
    "baseline_2026_07_20": 284
  },
  "traffic": {
    "window_days": 14,
    "views": 706,
    "unique_visitors": 272,
    "referrers": [{ "referrer": "github.com", "count": 122, "uniques": 84 }]
  }
}
```

`pr_stats.total_merged` is `null` when the count could not be resolved
reliably — a null is honest, a zero would not be.

### GitHub Traffic Data Limitations

**Important:** GitHub traffic endpoints (`/traffic/views`, `/traffic/popular/referrers`) have specific constraints:

1. **Rolling 14-day window**: Traffic data covers only the last 14 days. Historical trends cannot be reconstructed from a single snapshot.
2. **Domain-level attribution**: Referrer data identifies source domains only (e.g., `github.com`, `google.com`). Individual pages or UTM parameters are not exposed.
3. **Campaign correlation**: GitHub does not provide campaign attribution. Correlating traffic spikes to specific posts, shares, or events requires external tracking (e.g., UTM parameters on outgoing links).
4. **Traffic errors**: 403/404/429 responses are expected for some configurations (the traffic endpoints need push access to the repository). When the endpoints fail, the collector writes the snapshot **without** the `traffic` block rather than writing zeroes — a missing block means "not measured", a zero would mean "measured, nothing came in".

## Automation Opportunities

Future improvements (contributions welcome):

- [ ] GitHub Action to collect weekly metrics automatically — *the collection
      workflow was removed on 2026-08-15; restoring it is new code, which this
      frozen demo repository does not take. Until the repository is unfrozen,
      the snapshot is collected by hand and committed.*
- [ ] Dashboard generation from snapshot data
- [ ] Slack/Discord notification on milestones
- [ ] Badge integration (stars, contributors) in README
