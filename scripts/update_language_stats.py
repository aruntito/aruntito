import os
import json
import urllib.request
import urllib.error
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

# Fetch all repositories the token can access where the authenticated user is an owner.
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
    languages_url = repo.get("languages_url")
    if not languages_url:
        continue
    for language, byte_count in get_json(languages_url).items():
        totals[language] += byte_count

total_bytes = sum(totals.values())
if not total_bytes:
    raise SystemExit("No language data returned; refusing to overwrite the existing card.")

items = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:8]
palette = ["#3178c6", "#f1e05a", "#3572A5", "#4F5D95", "#e34c26", "#89e051", "#563d7c", "#b07219"]
width, bar_y, bar_h = 640, 88, 18
x = 0
segments = []
for index, (language, count) in enumerate(items):
    segment_width = width * count / total_bytes
    segments.append(
        f'<rect x="{x:.2f}" y="{bar_y}" width="{segment_width:.2f}" height="{bar_h}" fill="{palette[index % len(palette)]}"/>'
    )
    x += segment_width

legend = []
for index, (language, count) in enumerate(items):
    col = index % 2
    row = index // 2
    lx = 0 if col == 0 else 340
    ly = 150 + row * 42
    pct = count / total_bytes * 100
    legend.append(
        f'<circle cx="{lx + 10}" cy="{ly - 5}" r="8" fill="{palette[index % len(palette)]}"/>'
        f'<text x="{lx + 28}" y="{ly}" class="label">{escape(language)} {pct:.2f}%</text>'
    )

height = 180 + ((len(items) + 1) // 2) * 42
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="680" height="{height}" viewBox="0 0 680 {height}" role="img" aria-labelledby="title">
<title id="title">Most used languages across accessible repositories</title>
<style>
  .title {{ font: 600 27px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #539bf5; }}
  .label {{ font: 16px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #8b949e; }}
</style>
<rect width="680" height="{height}" rx="12" fill="#0d1117"/>
<text x="28" y="48" class="title">Most Used Languages</text>
<clipPath id="barClip"><rect x="28" y="{bar_y}" width="{width}" height="{bar_h}" rx="9"/></clipPath>
<g transform="translate(28 0)" clip-path="url(#barClip)">{''.join(segments)}</g>
{''.join(legend)}
</svg>
"""

Path("assets").mkdir(exist_ok=True)
Path("assets/most-used-languages.svg").write_text(svg, encoding="utf-8")
print(f"Updated language card from {len(repos)} accessible owned repositories.")
