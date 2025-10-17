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

# Seviye (GitHub benzeri 5 ton)
def level(v):
    if v <= 0: return 0
    if maxv <= 4: return min(v, 4)
    b1 = max(1, math.ceil(maxv*0.10))
    b2 = max(2, math.ceil(maxv*0.30))
    b3 = max(3, math.ceil(maxv*0.60))
    b4 = max(4, math.ceil(maxv*0.85))
    return 1 if v <= b1 else 2 if v <= b2 else 3 if v <= b3 else 4

PALETTE = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]

cell = 12
gap = 2
pad_top = 24
pad_left = 40
pad_right = 16
pad_bottom = 24
cols = 52
rows = 7
width = pad_left + cols*(cell+gap)-gap + pad_right
height = pad_top + rows*(cell+gap)-gap + pad_bottom

week_starts = [datetime.fromisoformat(w["firstDay"].replace("Z", "+00:00")) for w in weeks]
labels = []
seen = set()
for i, d in enumerate(week_starts):
    key = (d.year, d.month)
    if key not in seen:
        seen.add(key)
        labels.append((i, d.strftime("%b")))

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">')
svg.append('<style>.lbl{font:10px -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif; fill:#57606a}</style>')
svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="white"/>')
svg.append(f'<text class="lbl" x="{pad_left}" y="16">GitHub Activity — last 52 weeks ({USERNAME})</text>')

for col, txt in labels:
    x = pad_left + col*(cell+gap)
    svg.append(f'<text class="lbl" x="{x}" y="{pad_top-6}">{txt}</text>')

days_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
for r, name in enumerate(days_names):
    y = pad_top + r*(cell+gap) + 9
    svg.append(f'<text class="lbl" x="8" y="{y}">{name}</text>')

for c in range(cols):
    week = days_by_week[c]
    for r, d in enumerate(week):
        v = d["contributionCount"]
        lvl = level(v)
        color = PALETTE[lvl]
        x = pad_left + c*(cell+gap)
        y = pad_top + r*(cell+gap)
        date = d["date"][:10]
        svg.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" ry="2" fill="{color}"><title>{date}: {v} contributions</title></rect>')

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