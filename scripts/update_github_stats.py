import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

LOGIN = os.environ.get('GITHUB_USERNAME', 'Rahbir1518')
TOKEN = os.environ.get('GH_STATS_TOKEN') or os.environ.get('GITHUB_TOKEN')
OUT = Path('assets/06-github-stats.svg')

if not TOKEN:
    raise SystemExit('No GitHub token available')

query = '''
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
'''

now = datetime.now(timezone.utc)
to_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)
from_dt = (now - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)

payload = json.dumps({
    'query': query,
    'variables': {
        'login': LOGIN,
        'from': from_dt.isoformat().replace('+00:00', 'Z'),
        'to': to_dt.isoformat().replace('+00:00', 'Z'),
    },
}).encode()

req = Request(
    'https://api.github.com/graphql',
    data=payload,
    headers={
        'Authorization': f'bearer {TOKEN}',
        'Content-Type': 'application/json',
        'User-Agent': 'rahbir-profile-stats',
    },
    method='POST',
)

with urlopen(req, timeout=30) as response:
    data = json.load(response)

if data.get('errors'):
    raise SystemExit(json.dumps(data['errors']))

calendar = data['data']['user']['contributionsCollection']['contributionCalendar']
days = [d for w in calendar['weeks'] for d in w['contributionDays']]
days.sort(key=lambda x: x['date'])
counts = {d['date']: d['contributionCount'] for d in days}

total = int(calendar['totalContributions'])

# GitHub-style streak: if today is empty, start from yesterday; otherwise include today.
today = now.date()
start = today if counts.get(today.isoformat(), 0) > 0 else today - timedelta(days=1)
current = 0
cursor = start
while counts.get(cursor.isoformat(), 0) > 0:
    current += 1
    cursor -= timedelta(days=1)

longest = 0
run = 0
for d in days:
    if d['contributionCount'] > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0

# Compact SVG matching the portfolio's document aesthetic.
def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="300" viewBox="0 0 1100 300">
<defs>
<style>
.m{{font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace}}
.tiny{{font-size:10px;letter-spacing:2.4px}} .small{{font-size:12px;letter-spacing:.5px}}
.ink{{fill:#111}} .muted{{fill:#666}} .rule{{stroke:#111;stroke-width:1}} .soft{{stroke:#aaa;stroke-width:1}}
@keyframes pulse{{0%,100%{{opacity:.35}}50%{{opacity:1}}}} .pulse{{animation:pulse 1.8s ease-in-out infinite}}
</style></defs>
<rect width="100%" height="100%" fill="#fff"/>
<text x="24" y="34" class="m tiny ink">06&#160;&#160; GITHUB STATS</text>
<line x1="185" y1="28" x2="930" y2="28" class="rule"/>
<text x="965" y="33" class="m tiny muted">/06-STATUS</text>
<text x="24" y="64" class="m tiny muted">LIVE SIGNAL — UPDATED AUTOMATICALLY FROM GITHUB</text>

<g transform="translate(35,92)">
  <rect x="0" y="0" width="1030" height="135" fill="#fff" stroke="#aaa"/>
  <line x1="343" y1="0" x2="343" y2="135" class="soft"/>
  <line x1="686" y1="0" x2="686" y2="135" class="soft"/>

  <text x="171" y="48" text-anchor="middle" class="m" font-size="34" font-weight="600" fill="#111">{total}</text>
  <text x="171" y="78" text-anchor="middle" class="m small muted">TOTAL CONTRIBUTIONS</text>
  <text x="171" y="101" text-anchor="middle" class="m tiny muted">LAST 365 DAYS</text>

  <text x="514" y="48" text-anchor="middle" class="m" font-size="34" font-weight="600" fill="#111">{current}</text>
  <text x="514" y="78" text-anchor="middle" class="m small muted">CURRENT STREAK</text>
  <text x="514" y="101" text-anchor="middle" class="m tiny muted">CONSECUTIVE DAYS</text>

  <text x="857" y="48" text-anchor="middle" class="m" font-size="34" font-weight="600" fill="#111">{longest}</text>
  <text x="857" y="78" text-anchor="middle" class="m small muted">LONGEST STREAK</text>
  <text x="857" y="101" text-anchor="middle" class="m tiny muted">CONSECUTIVE DAYS</text>
</g>

<text x="24" y="260" class="m tiny muted">SOURCE: GITHUB CONTRIBUTION CALENDAR</text>
<circle cx="1048" cy="256" r="3" fill="#111" class="pulse"/>
</svg>'''

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(svg, encoding='utf-8')
print(f'Updated {OUT}: total={total}, current={current}, longest={longest}')
