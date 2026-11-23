import os
import json
import urllib.request
from collections import defaultdict
from pathlib import Path
from html import escape

TOKEN = os.environ.get("GH_STATS_TOKEN")
if not TOKEN:
    raise SystemExit("Missing GH_STATS_TOKEN repository secret.")

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "aruntito-language-stats",
}

def get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

repos = []
page = 1
while True:
    url = f"{API}/user/repos?visibility=all&affiliation=owner&per_page=100&page={page}&sort=updated"
    batch = get_json(url)
    if not batch:
        break
    repos.extend(batch)
    if len(batch) < 100:
        break
    page += 1

totals = defaultdict(int)
for repo in repos:
    if repo.get("fork") or repo.get("archived"):
        continue
    for language, byte_count in get_json(repo["languages_url"]).items():
        totals[language] += byte_count

total_bytes = sum(totals.values())
if not total_bytes:
    raise SystemExit("No language data returned; refusing to overwrite the existing card.")

ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
top = ranked[:5]
other_bytes = sum(count for _, count in ranked[5:])
items = top + ([("Other", other_bytes)] if other_bytes else [])

# Restrained palette: five muted accents, with neutral gray for the remainder.
palette = ["#3977B8", "#D6B94C", "#4D8A83", "#8176B5", "#C87958", "#9AA1AA"]
bar_x, bar_y, bar_w, bar_h = 12, 12, 656, 8
segments = []
x = bar_x
for index, (language, count) in enumerate(items):
    segment_width = bar_w * count / total_bytes
    segments.append(
        f'<rect x="{x:.2f}" y="{bar_y}" width="{segment_width:.2f}" height="{bar_h}" fill="{palette[index]}"/>'
    )
    x += segment_width

legend = []
for index, (language, count) in enumerate(items):
    col = index % 3
    row = index // 3
    lx = 12 + col * 220
    ly = 52 + row * 30
    pct = count / total_bytes * 100
    legend.append(
        f'<circle cx="{lx + 4}" cy="{ly - 5}" r="3.5" fill="{palette[index]}"/>'
        f'<text x="{lx + 14}" y="{ly}" class="label">{escape(language)} '
        f'<tspan class="percentage">{pct:.1f}%</tspan></text>'
    )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="680" height="86" viewBox="0 0 680 86" role="img" aria-labelledby="title">
<title id="title">Most used languages across public and private repositories</title>
<style>
  .label {{ font: 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #42464D; }}
  .percentage {{ fill: #777D86; }}
  @media (prefers-color-scheme: dark) {{
    .label {{ fill: #D0D4DA; }}
    .percentage {{ fill: #9299A3; }}
  }}
</style>
<defs>
  <clipPath id="barClip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="4"/></clipPath>
</defs>
<g clip-path="url(#barClip)">{''.join(segments)}</g>
{''.join(legend)}
</svg>
"""

Path("assets").mkdir(exist_ok=True)
Path("assets/most-used-languages.svg").write_text(svg, encoding="utf-8")
print(f"Updated compact language card from {len(repos)} accessible owned repositories.")
