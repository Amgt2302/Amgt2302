#!/usr/bin/env python3
"""Génère profile-card.svg : art ASCII coloré + terminal animé (langages, stats)."""
import os, json, datetime, urllib.request
from html import escape
from PIL import Image

USER  = os.environ.get("GH_USER", "Amgt2302")
TOKEN = os.environ.get("GH_TOKEN", "")
IMAGE = "profile.jpg"

COLS = 80                    # largeur de l'art en caractères
RAMP = " .:-=+*#%@"
CW, CH = 7.2, 14.0           # taille d'une cellule ASCII
FONT_SIZE = 13
PAD = 24
PANEL_W = 580
BAR_W = 240

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "HTML": "#e34c26", "CSS": "#563d7c", "Java": "#b07219", "C": "#555555",
    "C++": "#f34b7d", "C#": "#178600", "Go": "#00ADD8", "Rust": "#dea584",
    "Shell": "#89e051", "PHP": "#4F5D95", "Ruby": "#701516", "Kotlin": "#A97BFF",
    "Swift": "#F05138", "Dart": "#00B4AB", "Vue": "#41b883",
    "Jupyter Notebook": "#DA5B0B", "Dockerfile": "#384d54",
}


def api(url, data=None):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "profile-card",
        "Accept": "application/vnd.github+json",
    })
    if data is not None:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def get_stats():
    user = api(f"https://api.github.com/users/{USER}")
    now = datetime.datetime.utcnow()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
        }
      }
    }"""
    res = api("https://api.github.com/graphql", {
        "query": query,
        "variables": {"login": USER,
                      "from": start.isoformat() + "Z",
                      "to": now.isoformat() + "Z"},
    })
    month = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return {"repos": user["public_repos"], "followers": user["followers"], "month": month}


def get_languages(top=6):
    """Additionne les octets par langage sur tous tes dépôts non-forkés."""
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        for lang, size in api(repo["languages_url"]).items():
            totals[lang] = totals.get(lang, 0) + size
    total = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top]
    return [(name, size * 100 / total) for name, size in ranked]


def ascii_art():
    img = Image.open(IMAGE).convert("RGB")
    w, h = img.size
    rows = max(1, round(COLS * h / w * 0.5))
    small = img.resize((COLS, rows), Image.LANCZOS)
    grid = []
    for y in range(rows):
        line = []
        for x in range(COLS):
            r, g, b = small.getpixel((x, y))
            lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
            ch = RAMP[min(int(lum * len(RAMP)), len(RAMP) - 1)]
            line.append((ch, (r, g, b)))
        grid.append(line)
    return grid


STYLE = """
<style>
  .l    { opacity: 0; animation: fade 0.5s ease forwards; }
  .bar  { transform-origin: left center; transform: scaleX(0);
          animation: grow 1.2s cubic-bezier(.2,.8,.2,1) forwards; }
  .cur  { animation: blink 1s steps(1) infinite; }
  @keyframes fade  { to { opacity: 1; } }
  @keyframes grow  { to { transform: scaleX(1); } }
  @keyframes blink { 50% { opacity: 0; } }
</style>"""


def build_svg(stats, langs):
    art = ascii_art()
    art_w = COLS * CW
    art_h = len(art) * CH

    px = PAD + art_w + 30          # x du panneau
    panel_content_h = 80 + 3 * 30 + 50 + len(langs) * 40 + 60
    H = int(max(art_h, panel_content_h) + 2 * PAD)
    W = int(px + PANEL_W + PAD)
    mono = "font-family=\"Menlo,Consolas,'Courier New',monospace\""

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" {mono} font-size="{FONT_SIZE}">',
           STYLE,
           f'<rect width="{W}" height="{H}" rx="12" fill="#0d1117"/>']

    # --- Art ASCII, révélé ligne par ligne ---
    for j, row in enumerate(art):
        y = PAD + (j + 1) * CH - 3
        out.append(f'<g class="l" style="animation-delay:{0.1 + j * 0.035:.2f}s">')
        for i, (ch, (r, g, b)) in enumerate(row):
            if ch == " ":
                continue
            out.append(f'<text x="{PAD + i * CW:.1f}" y="{y:.1f}" '
                       f'fill="#{r:02x}{g:02x}{b:02x}">{escape(ch)}</text>')
        out.append("</g>")

    # --- Panneau terminal ---
    out.append(f'<rect x="{px}" y="{PAD}" width="{PANEL_W}" height="{H - 2 * PAD}" '
               f'rx="10" fill="#161b22" stroke="#30363d"/>')
    for k, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        out.append(f'<circle cx="{px + 20 + k * 20}" cy="{PAD + 20}" r="6" fill="{c}"/>')

    delay = 1.0
    y = PAD + 75
    out.append(f'<text x="{px + 24}" y="{y}" font-size="16" fill="#7ee787" class="l" '
               f'style="animation-delay:{delay}s">$ whoami --stats</text>')
    y += 34

    entries = [
        ("Dépôts publics", str(stats["repos"])),
        ("Contributions",  f"{stats['month']} ce mois-ci"),
        ("Followers",      str(stats["followers"])),
    ]
    for label, value in entries:
        delay += 0.2
        out.append(f'<g class="l" style="animation-delay:{delay:.2f}s">'
                   f'<text x="{px + 24}" y="{y}" font-size="15" fill="#79c0ff">{escape(label)}</text>'
                   f'<text x="{px + 230}" y="{y}" font-size="15" fill="#e6edf3">{escape(value)}</text>'
                   f'</g>')
        y += 30

    y += 14
    delay += 0.3
    out.append(f'<text x="{px + 24}" y="{y}" font-size="16" fill="#7ee787" class="l" '
               f'style="animation-delay:{delay:.2f}s">$ languages --top</text>')
    y += 34

    max_pct = max((p for _, p in langs), default=1)
    for name, pct in langs:
        delay += 0.2
        color = LANG_COLORS.get(name, "#8b949e")
        width = BAR_W * pct / max_pct
        out.append(
            f'<g class="l" style="animation-delay:{delay:.2f}s">'
            f'<text x="{px + 24}" y="{y + 4}" font-size="14" fill="#e6edf3">{escape(name)}</text>'
            f'<rect x="{px + 170}" y="{y - 8}" width="{BAR_W}" height="12" rx="6" fill="#21262d"/>'
            f'</g>'
            f'<rect class="bar" style="animation-delay:{delay + 0.2:.2f}s" '
            f'x="{px + 170}" y="{y - 8}" width="{width:.1f}" height="12" rx="6" fill="{color}"/>'
            f'<text class="l" style="animation-delay:{delay + 0.4:.2f}s" '
            f'x="{px + 170 + BAR_W + 14}" y="{y + 4}" font-size="14" fill="#8b949e">{pct:.1f}%</text>'
        )
        y += 36

    y += 10
    out.append(f'<text x="{px + 24}" y="{y}" font-size="18" fill="#7ee787" class="cur">▌</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if TOKEN:
        stats = get_stats()
        langs = get_languages()
    else:
        stats = {"repos": 0, "followers": 0, "month": 0}
        langs = [("Python", 50.0), ("JavaScript", 30.0), ("HTML", 20.0)]
    with open("profile-card.svg", "w", encoding="utf-8") as f:
        f.write(build_svg(stats, langs))
    print("profile-card.svg généré")
