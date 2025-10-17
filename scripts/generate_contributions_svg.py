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
        totalContributions
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
)
r.raise_for_status()
weeks = r.json()["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
weeks = weeks[-52:]

days_by_week = [w["contributionDays"] for w in weeks]
flat_counts = [d["contributionCount"] for week in days_by_week for d in week]
maxv = max(flat_counts) if flat_counts else 0

# Level calculation (5 bins like GitHub)
def level(v):
    if v <= 0: return 0
    if maxv <= 4: return min(v, 4)
    b1 = max(1, math.ceil(maxv*0.10))
    b2 = max(2, math.ceil(maxv*0.30))
    b3 = max(3, math.ceil(maxv*0.60))
    b4 = max(4, math.ceil(maxv*0.85))
    return 1 if v <= b1 else 2 if v <= b2 else 3 if v <= b3 else 4

# Card layout (GitHub Stats-like)
cell = 11
gap = 2
pad_top = 56   # header area
pad_left = 54  # leave room for weekday labels
pad_right = 24
pad_bottom = 42
cols = 52
rows = 7
width = pad_left + cols*(cell+gap)-gap + pad_right
height = pad_top + rows*(cell+gap)-gap + pad_bottom

# Month labels
week_starts = [datetime.fromisoformat(w["firstDay"].replace("Z", "+00:00")) for w in weeks]
labels = []
seen = set()
for i, d in enumerate(week_starts):
    key = (d.year, d.month)
    if key not in seen:
        seen.add(key)
        labels.append((i, d.strftime("%b")))

# Build SVG with CSS theme and dark-mode palette (no external fonts)
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="GitHub Activity for {USERNAME}">')
svg.append('<defs>
'
           '  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
'
           '    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity="0.15"/>
'
           '  </filter>
'
           '</defs>')
svg.append('<style>
'
           '  :root{ --bg:#ffffff; --fg:#57606a; --muted:#8b949e; --border:#d0d7de; }
'
           '  @media (prefers-color-scheme: dark){ :root{ --bg:#0d1117; --fg:#c9d1d9; --muted:#8b949e; --border:#30363d; } }
'
           '  .card{ fill:var(--bg); stroke:var(--border); }
'
           '  .title{ font:600 14px -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; fill:var(--fg); }
'
           '  .subtitle{ font:400 12px -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; fill:var(--muted);}
'
           '  .lbl{ font:400 10px -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; fill:var(--muted);}
'
           '  .l0{ fill:#ebedf0 } .l1{ fill:#9be9a8 } .l2{ fill:#40c463 } .l3{ fill:#30a14e } .l4{ fill:#216e39 }
'
           '  @media (prefers-color-scheme: dark){ .l0{ fill:#161b22 } .l1{ fill:#0e4429 } .l2{ fill:#006d32 } .l3{ fill:#26a641 } .l4{ fill:#39d353 } }
'
           '</style>')

# Card background with subtle shadow
svg.append(f'<rect x="0.5" y="0.5" rx="8" ry="8" width="{width-1}" height="{height-1}" class="card" filter="url(#shadow)"/>')

# Header
svg.append(f'<text class="title" x="{pad_left}" y="24">GitHub Activity</text>')
svg.append(f'<text class="subtitle" x="{pad_left}" y="40">last 52 weeks — {USERNAME}</text>')

# Month labels (top)
for col, txt in labels:
    x = pad_left + col*(cell+gap)
    svg.append(f'<text class="lbl" x="{x}" y="{pad_top-8}">{txt}</text>')

# Weekday labels (Mon, Wed, Fri only)
days_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
for r, name in enumerate(days_names):
    if name in ("Mon","Wed","Fri"):
        y = pad_top + r*(cell+gap) + 9
        svg.append(f'<text class="lbl" x="14" y="{y}">{name}</text>')

# Cells
for c in range(cols):
    week = days_by_week[c]
    for r, d in enumerate(week):
        v = d["contributionCount"]
        lvl = level(v)
        klass = f"l{lvl}"
        x = pad_left + c*(cell+gap)
        y = pad_top + r*(cell+gap)
        date = d["date"][:10]
        svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" ry="2.5" class="{klass}"><title>{date}: {v} contributions</title></rect>')

# Legend
legend_x = width - pad_right - (5*cell + 4*gap)
legend_y = height - pad_bottom + 16
svg.append(f'<text class="lbl" x="{legend_x-36}" y="{legend_y+8}">Less</text>')
for i in range(5):
    x = legend_x + i*(cell+gap)
    svg.append(f'<rect x="{x}" y="{legend_y}" width="{cell}" height="{cell}" rx="2.5" ry="2.5" class="l{i}"/>')
svg.append(f'<text class="lbl" x="{legend_x + 5*(cell+gap) + 4}" y="{legend_y+8}">More</text>')

svg.append('</svg>')
svg_text = "\n".join(svg)
OUT.write_text(svg_text, encoding="utf-8")
print(f"Wrote {OUT}")

# Monthly snapshot (UTC day == 1)
if SNAPSHOT_MONTHLY:
    now = datetime.now(timezone.utc)
    if now.day == 1:
        snap_path = OUT_SNAPSHOT or f"activity-{now.strftime('%Y-%m')}.svg"
        Path(snap_path).write_text(svg_text, encoding="utf-8")
        print(f"Wrote monthly snapshot: {snap_path}")