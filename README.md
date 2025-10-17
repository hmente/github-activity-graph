# GitHub Activity Graph

This repository generates a GitHub‑style **SVG heatmap** of my contributions every day using GitHub Actions.

## Output
- The SVG is saved as `github_activity.svg` and committed to this repo.
- **Monthly snapshots**: On the first day of each month (UTC), a file like `activity-YYYY-MM.svg` is also saved, preserving a historical archive.

### Preview
![activity graph](./github_activity.svg)

## How it works
- A workflow calls `scripts/generate_contributions_svg.py` which queries the GitHub GraphQL API using the repository token and draws the last 52 weeks.
- The workflow also creates a monthly snapshot when the calendar day is 1 (UTC).

## Manual run
- Trigger from **Actions** → *Update Activity Graph* → **Run workflow**.