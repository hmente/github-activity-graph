#!/usr/bin/env python3
import os, sys, math, requests
from pathlib import Path
from datetime import datetime, timezone

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GH_USERNAME") or os.getenv("GITHUB_ACTOR")
OUT = Path(os.getenv("OUT_SVG", "github_activity.svg"))
SNAPSHOT_MONTHLY = os.getenv("SNAPSHOT_MONTHLY", "false").lower() == "true"
OUT_SNAPSHOT = os.getenv("OUT_SNAPSHOT", "").strip()

if not GITHUB_TOKEN:
    print("Missing GITHUB_TOKEN env.", file=sys.stderr); sys.exit(1)
if not USERNAME:
    print("Missing GH_USERNAME or GITHUB_ACTOR env.", file=sys.stderr); sys.exit(1)

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays { date contributionCount }
          firstDay
        }
      }
    }
  }
}
"""

r = requests.post(
    "https://api.github.com/graphql",
    json={"query": QUERY, "variables": {"login": USERNAME}},
    headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    timeout=20,
)
r.raise_for_status()
payload = r.json()
if "errors" in payload:
    print(payload["errors"], file=sys.stderr); sys.exit(1)

weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"][-52:]
days_by_week = [w["contributionDays"] for w in weeks]
flat_counts = [d["contributionCount"] for week in days_by_week for d in week]
maxv = max(flat_counts) if flat_counts else 0

def level(v):
    if v <= 0: return 0
    if maxv <= 4: return min(v, 4)
    b1 = max(1, math.ceil(maxv*0.10))
    b2 = max(2, math.ceil(maxv*0.30))
    b3 = max(3, math.ceil(maxv*0.60))
    b4 = max(4, math.ceil(maxv*0.85))
    return 1 if v <= b1 else 2 if v <= b2 else 3 if v <= b3 else 4

cell = 12
gap = 2
pad_top = 18
pad_left = 20
pad_right = 16
pad_bottom = 12
rows = 7
cols = len(days_by_week)
width  = pad_left + cols*(cell+gap) - gap + pad_right
height = pad_top  + rows*(cell+gap) - gap + pad_bottom

week_starts = [datetime.fromisoformat(w["firstDay"].replace("Z", "+00:00")) for w in weeks]
labels = []
seen = set()
for i, d in enumerate(week_starts):
    key = (d.year, d.month)
    if key not in seen:
        seen.add(key)
        labels.append((i, d.strftime("%b")))

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="GitHub Activity for {USERNAME}">')
svg.append("""<style>
  :root{ --fg:#57606a; --muted:#6e7781; --empty:#ebedf0; --stroke:#ffffff; }
  @media (prefers-color-scheme: dark){
    :root{ --fg:#8b949e; --muted:#8b949e; --empty:#161b22; --stroke:#0d1117; }
  }
  .lbl{ font:10px -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; fill:var(--muted); }
  .l0{ fill:var(--empty); }
  .l1{ fill:#9be9a8 } .l2{ fill:#40c463 } .l3{ fill:#30a14e } .l4{ fill:#216e39 }
  @media (prefers-color-scheme: dark){
    .l1{ fill:#0e4429 } .l2{ fill:#006d32 } .l3{ fill:#26a641 } .l4{ fill:#39d353 }
  }
  .c{ shape-rendering:crispEdges; stroke:var(--stroke); stroke-width:1 }
</style>""")

for col, txt in labels:
    x = pad_left + col*(cell+gap)
    svg.append(f'<text class="lbl" x="{x}" y="{pad_top-4}">{txt}</text>')

for c in range(cols):
    week = days_by_week[c]
    for r, d in enumerate(week):
        v = d["contributionCount"]
        klass = f"l{level(v)}"
        x = pad_left + c*(cell+gap)
        y = pad_top + r*(cell+gap)
        date = d["date"][:10]
        svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" class="c {klass}"><title>{date}: {v} contributions</title></rect>')

svg.append("</svg>")
svg_text = "\n".join(svg)
OUT.write_text(svg_text, encoding="utf-8")
print(f"Wrote {OUT}")

if SNAPSHOT_MONTHLY:
    now = datetime.now(timezone.utc)
    if now.day == 1:
        snap_path = OUT_SNAPSHOT or f"activity-{now.strftime('%Y-%m')}.svg"
        Path(snap_path).write_text(svg_text, encoding="utf-8")
        print(f"Wrote monthly snapshot: {snap_path}")