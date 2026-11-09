#!/usr/bin/env python3
"""Génère profile-card.svg : art ASCII coloré + panneau style terminal."""
import os, json, datetime, urllib.request
from html import escape
from PIL import Image

USER  = os.environ.get("GH_USER", "ton-pseudo")
TOKEN = os.environ.get("GH_TOKEN", "")
IMAGE = "profile.jpg"
COLS  = 90                        # plus c'est grand, plus c'est fin
RAMP  = " .:-=+*#%@"              # du plus sombre au plus clair
CW, CH = 6.0, 12.0                # largeur / hauteur d'un caractère (px)
PAD = 20


def api(url, data=None):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "profile-card",
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
        "variables": {
            "login": USER,
            "from": start.isoformat() + "Z",
            "to": now.isoformat() + "Z",
        },
    })
    month = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return {"repos": user["public_repos"], "followers": user["followers"], "month": month}


def ascii_art():
    img = Image.open(IMAGE).convert("RGB")
    w, h = img.size
    rows = max(1, round(COLS * h / w * 0.5))   # un caractère est environ 2x plus haut que large
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


def build_svg(s):
    art = ascii_art()
    art_w = COLS * CW
    art_h = len(art) * CH
    px = art_w + 40                     # x du panneau
    panel_w = 420
    W = int(px + panel_w + PAD)
    H = int(max(art_h, 320) + 2 * PAD)
    py = PAD
    font = "font-family=\"Menlo,Consolas,'Courier New',monospace\" font-size=\"10\""

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" {font}>',
           f'<rect width="{W}" height="{H}" rx="10" fill="#0d1117"/>']

    # Art ASCII coloré
    for j, row in enumerate(art):
        y = PAD + (j + 1) * CH - 2
        for i, (ch, (r, g, b)) in enumerate(row):
            if ch == " ":
                continue
            x = PAD + i * CW
            out.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="#{r:02x}{g:02x}{b:02x}">{escape(ch)}</text>')

    # Panneau terminal
    ph = H - 2 * PAD
    out.append(f'<rect x="{px}" y="{py}" width="{panel_w}" height="{ph}" rx="8" fill="#161b22" stroke="#30363d"/>')
    for k, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        out.append(f'<circle cx="{px + 18 + k * 18}" cy="{py + 16}" r="5" fill="{c}"/>')

    y = py + 58
    out.append(f'<text x="{px + 20}" y="{y}" fill="#7ee787">$ fetch --profile {escape(USER)}</text>')
    y += 28
    entries = [
        ("Dépôts publics", str(s["repos"])),
        ("Contributions",  f"{s['month']} ce mois-ci"),
        ("Followers",      str(s["followers"])),
        ("Stack",          "Python · JavaScript"),   # à personnaliser
        ("Localisation",   "France"),                # à personnaliser
    ]
    for label, value in entries:
        out.append(f'<text x="{px + 20}" y="{y}" fill="#79c0ff">{escape(label)}</text>')
        out.append(f'<text x="{px + 170}" y="{y}" fill="#e6edf3">{escape(value)}</text>')
        y += 22

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    stats = get_stats() if TOKEN else {"repos": 0, "followers": 0, "month": 0}
    with open("profile-card.svg", "w", encoding="utf-8") as f:
        f.write(build_svg(stats))
    print("profile-card.svg généré")