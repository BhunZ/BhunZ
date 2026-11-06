"""Ink & Signal — generator for the BhunZ GitHub profile.

Builds every SVG in ./assets from live GitHub data (contribution calendar, repos, languages).
Design rules live in DESIGN.md. Run locally with a token in GH_TOKEN / GITHUB_TOKEN:

    python generate.py

Without a token or network it falls back to the cached JSON in ./data.
"""
import datetime as dt
import math
import random
import json
import os
import urllib.request
from pathlib import Path
from textwrap import wrap
from xml.sax.saxutils import escape

from marks import MARK_B, MARK_CSS, mark_svg

ROOT = Path(__file__).parent
OUT = ROOT / "assets"
DATA = ROOT / "data"
USER = "BhunZ"

# ───────────────────────────── CONTENT ─────────────────────────────
FIRST, LAST = "Bao Hung", "Nguyen"
ROLE = "DATA ENGINEER  ·  ANALYTICS & ML PIPELINES"
SLOGAN = ("Stream of consciousness,", "batch of conscience.")
CITY = "HO CHI MINH CITY"

INTRO = ("Data engineer in Ho Chi Minh City. I build batch and streaming pipelines "
         "from raw source to trusted table, and the models that run on top of them.")
SPEC = [
    ("BASED", "Ho Chi Minh City, VN"),
    ("STUDY", "HCMC Open University"),
    ("FOCUS", "Data engineering"),
    ("ALSO", "Applied ML · MLOps · RAG"),
    ("CORE STACK", "Python · SQL · dbt · Airflow"),
    ("OPEN TO", "Internships & collabs"),
]

PROJECTS = [
    dict(repo="StatStriker", tag="MLOPS",
         desc="Premier League match predictor. A weekly pipeline retrains a three-model ensemble and serves it through FastAPI.",
         tech=["Python", "scikit-learn", "FastAPI", "Docker", "Actions"]),
    dict(repo="Vietnam-Data-Job-Market-Analysis", title="VN Data Job Market", tag="DATA ENG",
         desc="Weekly ETL across six Vietnamese job boards, modelled Bronze → Silver → Gold in DuckDB with CDC.",
         tech=["DuckDB", "Parquet", "CDC", "Docker"]),
    dict(repo="binance-market-pipeline", title="Binance Market Pipeline", tag="STREAMING",
         desc="Batch (Airflow → dbt) and streaming (Kafka) views of one market, reconciled minute by minute.",
         tech=["Airflow", "dbt", "Kafka", "Postgres"]),
    dict(repo="stanford-nlp-tutor", title="Stanford NLP Tutor", tag="RAG",
         desc="Bilingual Q&A over 250+ Stanford NLP lectures, built on hybrid retrieval and reranking.",
         tech=["FastAPI", "React", "FAISS", "BM25"]),
    dict(repo="a8-hbt-datathon-the_gridbreaker", title="The Gridbreaker", tag="FORECAST",
         desc="Datathon 2026. Forecasting 548 days of daily revenue for a fashion retailer with a tree ensemble.",
         tech=["Python", "RF", "ExtraTrees", "HGB"]),
    dict(repo="football-match-prediction-poisson", title="Poisson Football", tag="STATS",
         desc="Premier League scorelines modelled as full probability distributions with a Poisson model.",
         tech=["Python", "Poisson", "pandas", "FBref"]),
]

TOOLKIT = [
    ("LANGUAGES", ["Python", "SQL", "TypeScript", "Bash"]),
    ("ORCHESTRATE", ["Airflow", "GitHub Actions", "systemd", "cron"]),
    ("INGEST", ["Kafka", "REST APIs", "Scrapers", "CDC"]),
    ("STORE", ["DuckDB", "PostgreSQL", "Parquet", "S3"]),
    ("TRANSFORM", ["dbt", "pandas", "Medallion", "Star schema"]),
    ("MODEL", ["scikit-learn", "Dixon-Coles", "RAG", "FAISS"]),
    ("SHIP", ["FastAPI", "React", "Docker", "pytest"]),
]

# ───────────────────────────── PALETTE ─────────────────────────────
INK, CHAR, GRAPH, RULE = "#050505", "#0F0F0F", "#1A1A1A", "#2A2A2A"
ASH, SILVER, PAPER, WHITE = "#6E6E6E", "#A8A8A8", "#EDEDEA", "#FFFFFF"
SERIF = "Georgia,'Times New Roman',Times,serif"
MONO = "'JetBrains Mono','SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "'Segoe UI',-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
W = 900


def e(s):
    return escape(str(s), {'"': "&quot;"})


# ───────────────────────────── DATA ────────────────────────────────
def _token():
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _req(url, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ink-and-signal"}
    if _token():
        headers["Authorization"] = f"Bearer {_token()}"
    data = json.dumps(body).encode() if body else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as r:
        return json.load(r)


def cached(name, fetch):
    path = DATA / f"{name}.json"
    try:
        value = fetch()
        DATA.mkdir(exist_ok=True)
        path.write_text(json.dumps(value, indent=1), encoding="utf-8")
        return value
    except Exception as exc:  # offline / no token -> use last good copy
        print(f"[warn] {name}: {exc}; using cache")
        return json.loads(path.read_text(encoding="utf-8"))


def load():
    q = ('query{user(login:"%s"){followers{totalCount} contributionsCollection{contributionCalendar{'
         'totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}' % USER)
    contrib = cached("contrib", lambda: _req("https://api.github.com/graphql", {"query": q}))
    repos = cached("repos", lambda: [
        {k: r[k] for k in ("name", "stargazers_count", "fork", "language")}
        | {"languages": _req(r["languages_url"])}
        for r in _req(f"https://api.github.com/users/{USER}/repos?per_page=100") if not r["fork"]])
    user = contrib["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    streak = best = 0
    for c in counts:
        streak = streak + 1 if c else 0
        best = max(best, streak)
    peak = max(days, key=lambda d: d["contributionCount"])
    langs = {}
    for r in repos:
        for k, v in r["languages"].items():
            if k not in ("Jupyter Notebook", "HTML", "CSS"):
                langs[k] = langs.get(k, 0) + v
    return dict(
        weeks=cal["weeks"], total=cal["totalContributions"], active=sum(1 for c in counts if c),
        peak=peak["contributionCount"], peak_date=peak["date"], streak=best,
        followers=(user.get("followers") or {}).get("totalCount", 0),
        stars={r["name"]: r["stargazers_count"] for r in repos},
        n_repos=len(repos), langs=sorted(langs.items(), key=lambda kv: -kv[1]),
    )


# ──────────────────────────── PRIMITIVES ───────────────────────────
def doc(w, h, label, body, style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'fill="none" role="img" aria-label="{e(label)}">\n<title>{e(label)}</title>\n'
            f'<style>{style}</style>\n{body}\n</svg>\n')


def paper(w, h, uid, spot=(0.2, 0.1), crop=True, drift=None):
    """Black sheet: spotlight gradient, film grain, hairline frame, crop marks."""
    cx, cy = spot
    marks = ""
    if crop:
        m, L = 10, 14
        for x, y, dx, dy in ((m, m, 1, 1), (w - m, m, -1, 1), (m, h - m, 1, -1), (w - m, h - m, -1, -1)):
            marks += (f'<path d="M{x},{y + dy * L} V{y} H{x + dx * L}" stroke="{ASH}" stroke-opacity=".7" stroke-width="1"/>')
    anim = (f'<animate attributeName="cx" values="{drift[0]};{drift[1]};{drift[0]}" dur="22s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>' if drift else "")
    return f"""<defs>
<radialGradient id="spot-{uid}" cx="{cx}" cy="{cy}" r="0.9">{anim}<stop offset="0" stop-color="#2E2E2E"/><stop offset=".45" stop-color="#121212"/><stop offset="1" stop-color="{INK}"/></radialGradient>
<filter id="grain-{uid}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 .09"/></feComponentTransfer></filter>
<clipPath id="clip-{uid}"><rect width="{w}" height="{h}" rx="14"/></clipPath>
</defs>
<g clip-path="url(#clip-{uid})"><rect width="{w}" height="{h}" fill="url(#spot-{uid})"/><rect width="{w}" height="{h}" filter="url(#grain-{uid})"/></g>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="13.5" stroke="{RULE}"/>
{marks}"""


def hairline(uid, x1, x2, y, reverse=False, opacity=0.55):
    a, b = (0, opacity) if reverse else (opacity, 0)
    return (f'<defs><linearGradient id="hl-{uid}" gradientUnits="userSpaceOnUse" x1="{x1}" y1="0" x2="{x2}" y2="0">'
            f'<stop offset="0" stop-color="{WHITE}" stop-opacity="{a}"/><stop offset="1" stop-color="{WHITE}" stop-opacity="{b}"/></linearGradient></defs>'
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="url(#hl-{uid})"/>')


def caps(x, y, text, size=10.5, fill=ASH, spacing=2.4, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{MONO}" font-size="{size}" '
            f'letter-spacing="{spacing}" fill="{fill}" {extra}>{e(text)}</text>')


def signature(x, y, size, uid, color=WHITE, delay=0.3, dur=2.6):
    """The "bh" artist mark (drawn from scratch, deliberately NOT the legal signature), written stroke by stroke."""
    return mark_svg(MARK_B, x, y, size, uid, color=color, px=2.3, delay=delay, dur=dur)


SIG_CSS = MARK_CSS
INK_CSS = SIG_CSS


def smooth(pts):
    """Catmull-Rom spline through pts -> SVG path segments."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


# ───────────────────────────── HERO ────────────────────────────────
def galaxy(D, cx, cy, R=205, tilt=0.6):
    """Spiral galaxy: one star per day of the year, oldest at the core, brightness = contributions."""
    rnd = random.Random(7)
    days = [d for wk in D["weeks"] for d in wk["contributionDays"]]
    peak = max(D["peak"], 1)
    dust, stars = [], []
    n = len(days)
    for k, d in enumerate(days):
        t = k / max(n - 1, 1)
        arm = k % 2
        theta = arm * math.pi + t * 3.4 * math.pi + rnd.gauss(0, 0.12)
        r = 22 + t * R + rnd.gauss(0, 5)
        x, y = r * math.cos(theta), r * math.sin(theta)
        c = d["contributionCount"]
        if not c:
            dust.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(.6, 1.1):.2f}" fill-opacity="{rnd.uniform(.15, .4):.2f}"/>')
        else:
            q = (c / peak) ** 0.5
            tw = f' class="tw" style="animation-delay:{rnd.uniform(0, 6):.1f}s;animation-duration:{rnd.uniform(3, 7):.1f}s"'
            stars.append(f'<g{tw}><circle cx="{x:.1f}" cy="{y:.1f}" r="{5 + 17 * q:.1f}" fill="url(#glow)" opacity="{.35 + .5 * q:.2f}"/>'
                         f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{1.1 + 2.2 * q:.1f}" fill="{WHITE}"/></g>')
    rings = "".join(f'<circle r="{r}" stroke="{WHITE}" stroke-opacity="{o}" stroke-width="{1 / tilt * .6:.2f}"/>'
                    for r, o in ((70, .08), (128, .06), (196, .05)))
    return f"""<g transform="translate({cx} {cy}) scale(1 {tilt}) rotate(-18)">
<ellipse rx="120" ry="120" fill="url(#core)"/>
{rings}
<g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="240s" repeatCount="indefinite"/>
<g fill="{WHITE}">{''.join(dust)}</g>{''.join(stars)}</g>
<circle r="3" fill="{WHITE}"/><circle r="14" fill="url(#glow)"/>
</g>"""


def starfield(x0, x1, y0, y1, n=150, seed=3):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        cls = f' class="tw" style="animation-delay:{rnd.uniform(0, 8):.1f}s"' if i % 9 == 0 else ""
        out.append(f'<circle{cls} cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(.35, .95):.2f}" fill="{WHITE}" fill-opacity="{rnd.uniform(.1, .55):.2f}"/>')
    return "".join(out)


def hero(D):
    h = 520
    stats = [f"{D['total']} CONTRIBUTIONS", f"{D['active']} ACTIVE DAYS", f"PEAK {D['peak']} / DAY", CITY]
    stat_txt = "".join(caps(x, 498, s, size=10.5, anchor="end" if i == 3 else "start", fill=SILVER if i < 3 else ASH)
                       for i, (x, s) in enumerate(zip([56, 268, 470, 844], stats)))
    style = SIG_CSS + """
.tw{animation:tw 5s ease-in-out infinite}@keyframes tw{0%,100%{opacity:1}50%{opacity:.35}}
.fade{opacity:0;animation:fade 1.1s ease-out forwards}@keyframes fade{to{opacity:1}}"""
    body = f"""{paper(W, h, 'hero', spot=(0.78, 0.5))}
<defs>
<linearGradient id="chrome" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{WHITE}"/><stop offset=".55" stop-color="#C9C9C9"/><stop offset=".56" stop-color="#8E8E8E"/><stop offset="1" stop-color="#EDEDED"/></linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="{WHITE}" stop-opacity=".9"/><stop offset=".25" stop-color="{WHITE}" stop-opacity=".25"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
<radialGradient id="core"><stop offset="0" stop-color="{WHITE}" stop-opacity=".38"/><stop offset=".35" stop-color="#BDBDBD" stop-opacity=".12"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
<linearGradient id="veil" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{INK}"/><stop offset=".42" stop-color="{INK}" stop-opacity=".75"/><stop offset=".62" stop-color="{INK}" stop-opacity="0"/></linearGradient>
</defs>
{starfield(14, W - 14, 90, h - 70)}
{galaxy(D, 664, 276)}
<rect width="{W}" height="{h}" rx="14" fill="url(#veil)"/>
{caps(56, 66, "Nº 01 — PROFILE OF @BHUNZ", size=10.5)}
{caps(844, 66, dt.date.today().strftime("EDITION %Y.%m"), size=10.5, anchor="end")}
{hairline('top', 56, 844, 82)}
<g class="fade">
<text x="52" y="164" font-family="{SERIF}" font-size="62" letter-spacing="-1.5" fill="url(#chrome)">{e(FIRST)}</text>
<text x="52" y="228" font-family="{SERIF}" font-style="italic" font-size="62" letter-spacing="-1.5" fill="url(#chrome)">{e(LAST)}<tspan fill="{SILVER}" font-style="normal">.</tspan></text>
{caps(56, 270, ROLE, size=11, fill=SILVER, spacing=2.2)}
<text font-family="{SERIF}" font-style="italic" font-size="23" fill="{PAPER}"><tspan x="50" y="320"><tspan fill="{ASH}" font-size="34" dy="6">“</tspan><tspan dy="-6">{e(SLOGAN[0])}</tspan></tspan><tspan x="66" y="350">{e(SLOGAN[1])}<tspan fill="{ASH}" font-size="34" dy="6">”</tspan></tspan></text>
</g>
{signature(46, 362, 92, uid='hero', delay=1.2)}
{caps(844, 446, "365 DAYS · ONE STAR EACH · BRIGHTER = MORE COMMITS", size=9.5, anchor="end", spacing=1.6)}
{hairline('bot', 56, 844, 470, opacity=.35)}
{stat_txt}"""
    return doc(W, h, f"{FIRST} {LAST}, {ROLE.title()}. “{' '.join(SLOGAN)}” A galaxy of {D['total']} contributions.", body, style)


# ──────────────────────────── MOTION ───────────────────────────────
TW_CSS = ".tw{animation:tw 5s ease-in-out infinite}@keyframes tw{0%,100%{opacity:1}50%{opacity:.2}}"


def sky(x0, x1, y0, y1, n, seed, every=4, rmax=0.9, omax=0.6):
    """Scattered stars; every n-th one twinkles on its own clock."""
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        cls = (f' class="tw" style="animation-delay:{rnd.uniform(0, 7):.1f}s;animation-duration:{rnd.uniform(3, 8):.1f}s"'
               if i % every == 0 else "")
        out.append(f'<circle{cls} cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(.35, rmax):.2f}" fill="{WHITE}" '
                   f'fill-opacity="{rnd.uniform(.12, omax):.2f}"/>')
    return "".join(out)


def comet(uid, x, y, dx, dy, dur=13, begin=2, length=90):
    """A shooting star that crosses (dx, dy) once every `dur` seconds."""
    d = math.hypot(dx, dy)
    ux, uy = dx / d, dy / d
    tx, ty = x - ux * length, y - uy * length
    return (f'<defs><linearGradient id="cm-{uid}" gradientUnits="userSpaceOnUse" x1="{tx:.0f}" y1="{ty:.0f}" x2="{x}" y2="{y}">'
            f'<stop offset="0" stop-color="{WHITE}" stop-opacity="0"/><stop offset="1" stop-color="{WHITE}"/></linearGradient></defs>'
            f'<g opacity="0"><animate attributeName="opacity" values="0;1;0;0" keyTimes="0;.03;.1;1" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;{dx} {dy};{dx} {dy}" keyTimes="0;.1;1" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<line x1="{tx:.0f}" y1="{ty:.0f}" x2="{x}" y2="{y}" stroke="url(#cm-{uid})" stroke-width="1.3" stroke-linecap="round"/>'
            f'<circle cx="{x}" cy="{y}" r="1.6" fill="{WHITE}"/></g>')


def orbit(cx, cy, r, dur, phase=0):
    """Small orbit glyph: a ring with a moon going round it."""
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{ASH}" stroke-opacity=".7"/>'
            f'<circle cx="{cx}" cy="{cy}" r="1.6" fill="{PAPER}"/>'
            f'<g><animateTransform attributeName="transform" type="rotate" from="{phase} {cx} {cy}" to="{phase + 360} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/>'
            f'<circle cx="{cx + r}" cy="{cy}" r="2" fill="{WHITE}"/></g>')


# ──────────────────────────── HEADERS ──────────────────────────────
def header(num, title, sub):
    h = 96
    tw = len(title) * 30 * 0.47
    lx = 120 + tw + 24
    run = W - 26 - lx
    style = (TW_CSS +
             f".draw{{stroke-dasharray:{W};stroke-dashoffset:{W};animation:d 1.6s .2s cubic-bezier(.6,0,.2,1) forwards}}"
             "@keyframes d{to{stroke-dashoffset:0}}"
             ".num{stroke-dasharray:260;stroke-dashoffset:260;animation:n 2.6s .1s ease-in-out forwards}@keyframes n{to{stroke-dashoffset:0}}"
             f".pkt{{animation:run 7s cubic-bezier(.45,0,.55,1) 1.8s infinite;opacity:0}}"
             f"@keyframes run{{0%{{transform:translateX(0);opacity:0}}8%{{opacity:1}}85%{{opacity:1}}100%{{transform:translateX({run:.0f}px);opacity:0}}}}")
    body = f"""{paper(W, h, f'h{num}', spot=(0.02, 0.5), crop=False)}
{sky(lx, W - 20, 12, h - 12, 26, seed=int(num) * 11, every=3, omax=.45)}
<text class="num" x="14" y="76" font-family="{SERIF}" font-size="74" stroke="{SILVER}" stroke-width=".9" fill="none" letter-spacing="-2">{num}</text>
<text x="120" y="52" font-family="{SERIF}" font-style="italic" font-size="30" fill="{WHITE}">{e(title)}</text>
{caps(122, 76, sub, size=10, fill=ASH)}
<defs><linearGradient id="h{num}" gradientUnits="userSpaceOnUse" x1="{lx:.0f}" y1="0" x2="{W - 26}" y2="0"><stop offset="0" stop-color="{SILVER}" stop-opacity=".9"/><stop offset="1" stop-color="{SILVER}" stop-opacity="0"/></linearGradient>
<radialGradient id="pg{num}"><stop offset="0" stop-color="{WHITE}"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient></defs>
<line class="draw" x1="{lx:.0f}" y1="43" x2="{W - 26}" y2="43" stroke="url(#h{num})"/>
<g class="pkt"><circle cx="{lx:.0f}" cy="43" r="7" fill="url(#pg{num})" opacity=".5"/><circle cx="{lx:.0f}" cy="43" r="1.8" fill="{WHITE}"/></g>
{caps(W - 26, 76, f"§ {num} / 05", size=10, anchor="end")}"""
    return doc(W, h, f"{num} · {title}", body, style)


# ───────────────────────────── ABOUT ───────────────────────────────
def about():
    lines = wrap(INTRO, 62)
    intro = "".join(f'<text x="48" y="{100 + i * 36}" font-family="{SERIF}" font-size="25" letter-spacing="-.2" fill="{WHITE if i == 0 else PAPER}">{e(t)}</text>'
                    for i, t in enumerate(lines))
    gy = 100 + len(lines) * 36 + 10
    h = gy + 34 + 72 + 30 + 34
    cells = []
    for k, (label, value) in enumerate(SPEC):
        col, row = k % 3, k // 3
        x, y = 48 + col * 276, gy + 34 + row * 72
        cells.append(f'<g class="row" style="animation-delay:{0.3 + 0.12 * k:.2f}s">'
                     f'<circle class="tw" style="animation-delay:{k * .8:.1f}s" cx="{x + 3}" cy="{y - 4}" r="1.6" fill="{WHITE}"/>'
                     f'{caps(x + 12, y, label, size=11, fill=ASH)}'
                     f'<text x="{x}" y="{y + 30}" font-family="{SERIF}" font-size="19" fill="{PAPER}">{e(value)}</text></g>')
    style = (TW_CSS + ".row{opacity:0;animation:in .7s ease-out forwards}@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}"
             ".ln{opacity:0;animation:in .9s ease-out forwards}")
    intro = intro.replace('<text x="48"', '<text class="ln" x="48"')
    body = f"""{paper(W, h, 'about', spot=(0.05, 0.0), drift=(0.05, 0.6))}
{sky(620, W - 20, 20, gy - 10, 34, seed=21, every=3)}
{comet('ab', 860, 26, -150, 70, dur=15, begin=4, length=70)}
{caps(48, 50, "IN BRIEF", size=10.5)}
{intro}
<defs><linearGradient id="hl-ab2" gradientUnits="userSpaceOnUse" x1="48" y1="0" x2="852" y2="0"><stop offset="0" stop-color="{WHITE}" stop-opacity=".45"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></linearGradient></defs>
<line x1="48" y1="{gy}" x2="852" y2="{gy}" stroke="url(#hl-ab2)"/>
<line x1="{48 + 276 - 20}" y1="{gy + 18}" x2="{48 + 276 - 20}" y2="{h - 30}" stroke="{RULE}"/>
<line x1="{48 + 552 - 20}" y1="{gy + 18}" x2="{48 + 552 - 20}" y2="{h - 30}" stroke="{RULE}"/>
{''.join(cells)}"""
    return doc(W, h, INTRO + " " + "; ".join(f"{k.title()}: {v}" for k, v in SPEC), body, style)


# ──────────────────────────── PROJECTS ─────────────────────────────
def project(p, idx, stars):
    w, h = 440, 252
    uid = f"p{idx}"
    title = p.get("title", p["repo"])
    desc = wrap(p["desc"], 45)[:3]
    dl = "".join(f'<text x="26" y="{122 + i * 23}" font-family="{SANS}" font-size="15.5" fill="{PAPER}">{e(t)}</text>'
                 for i, t in enumerate(desc))
    tagw = len(p["tag"]) * (10 * 0.6 + 1.6) + 20
    star = caps(w - 26, 225, f"★ {stars}", size=12.5, fill=PAPER, spacing=0, anchor="end") if stars else ""
    style = (TW_CSS +
             ".sweep{animation:sw 9s ease-in-out infinite}@keyframes sw{0%{transform:translateX(-200px)}45%,100%{transform:translateX(640px)}}")
    body = f"""{paper(w, h, uid, spot=(0.0, 0.0), crop=False, drift=(0.0, 0.5))}
<defs><linearGradient id="sw-{uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{WHITE}" stop-opacity="0"/><stop offset=".5" stop-color="{WHITE}" stop-opacity=".05"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></linearGradient>
<clipPath id="cc-{uid}"><rect width="{w}" height="{h}" rx="14"/></clipPath></defs>
<g clip-path="url(#cc-{uid})"><rect class="sweep" style="animation-delay:{idx * 1.3:.1f}s" x="0" y="0" width="160" height="{h}" fill="url(#sw-{uid})" transform="skewX(-20)"/></g>
{sky(250, w - 20, 56, 100, 9, seed=100 + idx, every=2, omax=.5)}
{orbit(33, 37, 7, 5 + idx * 1.7, phase=idx * 60)}
{caps(48, 42, f"P/{idx + 1:02d}", size=11)}
<rect x="{w - 24 - tagw:.0f}" y="27" width="{tagw:.0f}" height="21" rx="2" stroke="{SILVER}" stroke-opacity=".6"/>
{caps(w - 24 - tagw / 2, 42, p["tag"], size=10, fill=PAPER, spacing=1.6, anchor="middle")}
<text x="25" y="86" font-family="{SERIF}" font-size="27" letter-spacing="-.4" fill="{WHITE}">{e(title)}</text>
{dl}
<line x1="26" y1="198" x2="{w - 26}" y2="198" stroke="{RULE}"/>
{caps(26, 225, "  ·  ".join(p["tech"][:4]), size=12, fill=SILVER, spacing=.4)}
{star}"""
    return doc(w, h, f"{title} ({p['repo']}): {p['desc']}" + (f" {stars} stars." if stars else ""), body, style)


# ───────────────────────────── TOOLKIT ─────────────────────────────
def toolkit():
    rh = 44
    h = 64 + rh * len(TOOLKIT) + 12
    rows = []
    for i, (label, items) in enumerate(TOOLKIT):
        y = 72 + i * rh
        rows.append(f'<circle class="tw" style="animation-delay:{i * .7:.1f}s" cx="52" cy="{y + 12}" r="1.6" fill="{WHITE}"/>')
        rows.append(caps(64, y + 16, f"{i + 1:02d}", size=10, fill=ASH))
        rows.append(caps(104, y + 16, label, size=10, fill=SILVER))
        spans = []
        for j, it in enumerate(items):
            if j:
                spans.append(f'<tspan fill="{ASH}" font-style="normal">  /  </tspan>')
            spans.append(f'<tspan fill="{WHITE if j == 0 else PAPER}" font-style="{"italic" if j == 0 else "normal"}">{e(it)}</tspan>')
        rows.append(f'<text class="row" style="animation-delay:{0.1 * i:.2f}s" x="270" y="{y + 18}" font-family="{SERIF}" font-size="19">{"".join(spans)}</text>')
        if i < len(TOOLKIT) - 1:
            rows.append(f'<line x1="48" y1="{y + rh - 10}" x2="852" y2="{y + rh - 10}" stroke="{RULE}" stroke-opacity=".8"/>')
    style = (TW_CSS + ".row{opacity:0;animation:in .7s ease-out forwards}@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}"
             f".scan{{animation:scan 8s cubic-bezier(.45,0,.55,1) infinite}}@keyframes scan{{0%{{transform:translateY(0)}}100%{{transform:translateY({rh * len(TOOLKIT)}px)}}}}")
    body = f"""{paper(W, h, 'tk', spot=(0.9, 0.0), drift=(0.9, 0.4))}
<defs><linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{WHITE}" stop-opacity="0"/><stop offset=".5" stop-color="{WHITE}" stop-opacity=".045"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></linearGradient>
<clipPath id="tkc"><rect x="20" y="58" width="{W - 40}" height="{rh * len(TOOLKIT) + 4}"/></clipPath></defs>
<g clip-path="url(#tkc)"><rect class="scan" x="20" y="{58 - 40}" width="{W - 40}" height="44" fill="url(#scan)"/></g>
{sky(700, W - 20, 60, h - 20, 30, seed=33, every=3, omax=.45)}
{caps(48, 44, "INDEX OF TOOLS", size=10)}
{caps(852, 44, "ITALIC = DAILY DRIVER", size=10, anchor="end")}
{''.join(rows)}"""
    return doc(W, h, "Toolkit. " + " ".join(f"{l.title()}: {', '.join(it)}." for l, it in TOOLKIT), body, style)


# ────────────────────────────── CITY ───────────────────────────────
def city(D):
    """Night skyline: one building per week, height = commits that week, every lit window = one commit."""
    h, ground = 520, 380
    rnd = random.Random(42)
    weeks = [(wk["contributionDays"][0]["date"], sum(d["contributionCount"] for d in wk["contributionDays"]))
             for wk in D["weeks"]]
    top_week = max(weeks, key=lambda t: t[1])
    pk = max(top_week[1], 1)
    x0, x1 = 40, W - 40
    slot = (x1 - x0) / len(weeks)

    # distant skyline (no data, just depth)
    far, x = [], 20.0
    while x < W - 20:
        bw = rnd.uniform(14, 34)
        bh = rnd.uniform(26, 95)
        far.append(f'<rect x="{x:.1f}" y="{ground - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}"/>')
        x += bw + rnd.uniform(-4, 3)

    blds, wins, roofs = [], [], []
    tallest = sorted(range(len(weeks)), key=lambda i: -weeks[i][1])[:5]
    for i, (date, c) in enumerate(weeks):
        bw = slot - rnd.uniform(1.5, 3.5)
        bx = x0 + i * slot + (slot - bw) / 2
        bh = 34 + 196 * (c / pk) ** 0.6 if c else rnd.uniform(16, 36)
        top = ground - bh
        delay = 0.2 + i * 0.03
        g = [f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="url(#fac)"/>',
             f'<rect x="{bx:.1f}" y="{top:.1f}" width="1" height="{bh:.1f}" fill="{WHITE}" fill-opacity=".14"/>',
             f'<rect x="{bx:.1f}" y="{top:.1f}" width="{bw:.1f}" height="1" fill="{WHITE}" fill-opacity=".22"/>']
        if c and bh > 70 and i % 3 == 0:  # stepped crown
            g.append(f'<rect x="{bx + bw * .22:.1f}" y="{top - 8:.1f}" width="{bw * .56:.1f}" height="8" fill="url(#fac)"/>')
        blds.append(f'<g class="b" style="animation-delay:{delay:.2f}s">{"".join(g)}</g>')
        # windows: a grid, `c` of them lit in random seats
        cols = max(1, int((bw - 2) // 3.5))
        rows = max(0, int((bh - 10) // 5))
        seats = [(r, k) for r in range(rows) for k in range(cols)]
        lit = rnd.sample(seats, min(c, len(seats)))
        gx = bx + (bw - (cols * 3.5 - 1.5)) / 2
        for n, (r, k) in enumerate(lit):
            cls = "fl" if n % 11 == 5 else "win"
            wins.append(f'<rect class="{cls}" style="animation-delay:{delay + 1.0 + rnd.uniform(0, 2.2):.2f}s" '
                        f'x="{gx + k * 3.5:.1f}" y="{top + 7 + r * 5:.1f}" width="2" height="2.6" fill="{PAPER}" '
                        f'fill-opacity="{rnd.uniform(.55, 1):.2f}"/>')
        if i in tallest:
            ax = bx + bw / 2
            roofs.append(f'<line x1="{ax:.1f}" y1="{top:.1f}" x2="{ax:.1f}" y2="{top - 16:.1f}" stroke="{SILVER}" stroke-width=".8"/>'
                         f'<circle class="beacon" style="animation-delay:{rnd.uniform(0, 2):.1f}s" cx="{ax:.1f}" cy="{top - 17:.1f}" r="1.6" fill="{WHITE}"/>')
        if (date, c) == top_week:
            px, py = bx + bw / 2, top - 30
            label = dt.date.fromisoformat(date).strftime("WEEK OF %d %b").upper()
            roofs.append(f'<line x1="{px:.1f}" y1="{py + 6:.1f}" x2="{px:.1f}" y2="{py - 8:.1f}" stroke="{ASH}" stroke-dasharray="1 2"/>'
                         + caps(px, py - 14, f"PEAK · {label} · {c}", size=9, fill=SILVER, spacing=1.4, anchor="middle"))

    style = (TW_CSS +
             ".b{transform-box:fill-box;transform-origin:50% 100%;transform:scaleY(0);animation:up 1.1s cubic-bezier(.2,.8,.2,1) forwards}"
             "@keyframes up{to{transform:scaleY(1)}}"
             ".win{opacity:0;animation:on .5s steps(2) forwards}@keyframes on{to{opacity:1}}"
             ".fl{opacity:0;animation:on .5s steps(2) forwards,fl 6s steps(1) infinite}"
             "@keyframes fl{0%,100%{opacity:1}46%{opacity:.15}48%{opacity:1}50%{opacity:.2}52%{opacity:1}}"
             ".beacon{animation:bc 2.2s ease-in-out infinite}@keyframes bc{0%,100%{opacity:.15}50%{opacity:1}}"
             ".rip{stroke-dasharray:18 26;animation:rip 7s linear infinite}@keyframes rip{to{stroke-dashoffset:-88}}")
    ripples = "".join(f'<line class="rip" style="animation-duration:{rnd.uniform(5, 10):.1f}s" x1="30" y1="{ground + 10 + k * 12}" '
                      f'x2="{W - 30}" y2="{ground + 10 + k * 12}" stroke="{WHITE}" stroke-opacity="{.07 - k * .01:.2f}"/>'
                      for k in range(6))
    body = f"""{paper(W, h, 'city', spot=(0.5, 0.78), crop=True)}
<defs>
<linearGradient id="skyg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}" stop-opacity="0"/><stop offset="1" stop-color="#262626" stop-opacity=".6"/></linearGradient>
<linearGradient id="fac" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#262626"/><stop offset="1" stop-color="#0B0B0B"/></linearGradient>
<radialGradient id="moonglow"><stop offset="0" stop-color="{WHITE}" stop-opacity=".22"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
<radialGradient id="moon" cx=".38" cy=".35" r=".75"><stop offset="0" stop-color="#F4F4F2"/><stop offset=".7" stop-color="#BDBDBA"/><stop offset="1" stop-color="#7A7A78"/></radialGradient>
<linearGradient id="refl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".32"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="reflm"><rect x="0" y="{ground}" width="{W}" height="{h - ground}" fill="url(#refl)"/></mask>
<filter id="blur1"><feGaussianBlur stdDeviation="1.1"/></filter>
<clipPath id="cityclip"><rect width="{W}" height="{h}" rx="14"/></clipPath>
</defs>
<g clip-path="url(#cityclip)">
<rect y="140" width="{W}" height="{ground - 140}" fill="url(#skyg)"/>
{sky(20, W - 20, 18, ground - 120, 120, seed=5, every=4, omax=.7)}
<circle cx="760" cy="96" r="70" fill="url(#moonglow)"/>
<circle cx="760" cy="96" r="22" fill="url(#moon)"/>
<circle cx="753" cy="90" r="4" fill="#9A9A98" fill-opacity=".35"/><circle cx="767" cy="104" r="2.6" fill="#9A9A98" fill-opacity=".3"/><circle cx="766" cy="87" r="1.8" fill="#9A9A98" fill-opacity=".3"/>
{comet('city', 610, 40, -200, 90, dur=14, begin=3)}
<g fill="#121212">{''.join(far)}</g>
<g id="skyline">{''.join(blds)}{''.join(wins)}</g>
{''.join(roofs)}
<g mask="url(#reflm)" filter="url(#blur1)"><use href="#skyline" transform="translate(0 {2 * ground}) scale(1 -1)"/></g>
{ripples}
<line x1="0" y1="{ground}" x2="{W}" y2="{ground}" stroke="{SILVER}" stroke-opacity=".35"/>
</g>
{caps(48, 52, "THE YEAR, AFTER DARK", size=10)}
<text x="44" y="112" font-family="{SERIF}" font-size="58" letter-spacing="-2" fill="{WHITE}">{D['total']}</text>
<text x="48" y="138" font-family="{SERIF}" font-style="italic" font-size="16" fill="{SILVER}">commits, one lit window each</text>
{caps(48, 162, f"{D['active']} ACTIVE DAYS  ·  {D['streak']}-DAY STREAK  ·  PEAK {D['peak']}", size=9.5, fill=PAPER, spacing=1.4)}
{caps(48, h - 24, "ONE BUILDING PER WEEK · HEIGHT = COMMITS THAT WEEK", size=9, spacing=1.6)}
{caps(W - 48, h - 24, "REBUILT DAILY · @BHUNZ", size=9, spacing=1.6, anchor="end")}"""
    return doc(W, h, f"A night skyline built from my contribution calendar: {len(weeks)} buildings, one per week, "
               f"{D['total']} lit windows, one per commit.", body, style)


# ───────────────────────────── LEDGER ──────────────────────────────
def ledger(D):
    h = 210
    langs = D["langs"][:5]
    tot = sum(v for _, v in D["langs"]) or 1
    fills = [WHITE, "#BDBDBD", "url(#hatch)", "#6E6E6E", "url(#dots)"]
    x, bar, legend = 48.0, [], []
    for k, ((name, val), f) in enumerate(zip(langs, fills)):
        wdt = max(804 * val / tot, 3)
        bar.append(f'<rect class="seg" style="animation-delay:{0.15 * k:.2f}s" x="{x:.1f}" y="84" width="{wdt:.1f}" height="12" fill="{f}"/>')
        lx = 48 + k * 162
        legend.append(f'<rect x="{lx}" y="118" width="10" height="10" fill="{f}" stroke="{RULE}"/>'
                      f'<text x="{lx + 18}" y="127" font-family="{SERIF}" font-size="14" fill="{PAPER}">{e(name)}</text>'
                      + caps(lx + 18, 146, f"{100 * val / tot:.1f}%", size=9.5, spacing=1))
        x += wdt
    nums = [(D["n_repos"], "PUBLIC REPOS"), (sum(D["stars"].values()), "STARS EARNED"),
            (D["followers"], "FOLLOWERS"), (langs[0][0] if langs else "—", "MAIN LANGUAGE")]
    nn = "".join(f'<text x="{48 + k * 210}" y="{188}" font-family="{SERIF}" font-size="18" fill="{WHITE}">{e(n)}'
                 f'<tspan font-family="{MONO}" font-size="9.5" letter-spacing="1.6" fill="{ASH}" dx="10">{e(lbl)}</tspan></text>'
                 for k, (n, lbl) in enumerate(nums))
    style = (TW_CSS + ".seg{transform-box:fill-box;transform-origin:0 50%;transform:scaleX(0);animation:g 1.2s cubic-bezier(.2,.8,.2,1) forwards}@keyframes g{to{transform:scaleX(1)}}"
             ".shine{animation:sh 4.5s ease-in-out 1.5s infinite;opacity:0}@keyframes sh{0%{transform:translateX(0);opacity:0}10%{opacity:1}70%{opacity:1}100%{transform:translateX(860px);opacity:0}}")
    body = f"""{paper(W, h, 'ledger', spot=(0.1, 1.0), drift=(0.1, 0.9))}
<defs>
<pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="#2A2A2A"/><line x1="0" y1="0" x2="0" y2="5" stroke="#D0D0D0" stroke-width="2"/></pattern>
<pattern id="dots" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#1E1E1E"/><circle cx="2" cy="2" r="1" fill="#BDBDBD"/></pattern>
<linearGradient id="shg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset=".5" stop-color="#000" stop-opacity=".45"/><stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>
<clipPath id="barclip"><rect x="48" y="84" width="804" height="12"/></clipPath>
</defs>
{sky(560, W - 20, 20, 70, 18, seed=55, every=2, omax=.5)}
{caps(48, 50, "LEDGER — LANGUAGES BY CODE SIZE", size=10)}
{caps(852, 50, "NOTEBOOKS EXCLUDED", size=10, anchor="end")}
<rect x="48" y="84" width="804" height="12" fill="{GRAPH}"/>
{''.join(bar)}
<g clip-path="url(#barclip)"><rect class="shine" x="-20" y="84" width="70" height="12" fill="url(#shg)"/></g>
{''.join(legend)}
<line x1="48" y1="162" x2="852" y2="162" stroke="{RULE}"/>
{nn}"""
    return doc(W, h, "Languages: " + ", ".join(f"{n} {100 * v / tot:.0f}%" for n, v in langs), body, style)


# ───────────────────────────── FOOTER ──────────────────────────────
def footer():
    h = 230
    body = f"""{paper(W, h, 'foot', spot=(0.5, 1.1), drift=(0.3, 0.7))}
{sky(20, W - 20, 16, h - 16, 70, seed=77, every=3, omax=.5)}
{comet('f1', 300, 30, -220, 80, dur=12, begin=2.5)}
{comet('f2', 880, 50, -180, 70, dur=17, begin=9)}
{signature(W / 2 - 88, 26, 118, uid="foot", delay=0.4)}
{hairline('fl', 250, 450, 168, reverse=True)}{hairline('fr', 450, 650, 168)}
<text x="{W / 2}" y="196" text-anchor="middle" font-family="{SERIF}" font-style="italic" font-size="17" fill="{PAPER}">Thanks for reading. See you in the commits.</text>
{caps(W / 2, 216, "BHUNZ · INK & SIGNAL" + dt.date.today().strftime(" · %d.%m.%Y"), size=9, anchor="middle")}"""
    return doc(W, h, "Signed, BhunZ. Thanks for reading.", body, INK_CSS + TW_CSS)


HEADERS = [("01", "In Brief", "CAT ABOUT.MD"), ("02", "Selected Work", "SIX REPOSITORIES, ORDERED BY CARE"),
           ("03", "Toolkit", "WHAT I REACH FOR"), ("04", "The Year, After Dark", "ONE BUILDING PER WEEK · ONE LIT WINDOW PER COMMIT"),
           ("05", "Off the Record", "SELECT * FROM BHUNZ.SECRETS")]

if __name__ == "__main__":
    D = load()
    (OUT / "projects").mkdir(parents=True, exist_ok=True)
    files = {"hero.svg": hero(D), "about.svg": about(), "toolkit.svg": toolkit(), "city.svg": city(D),
             "ledger.svg": ledger(D), "footer.svg": footer()}
    for n, t, s in HEADERS:
        files[f"header_{n}.svg"] = header(n, t, s)
    for i, p in enumerate(PROJECTS):
        files[f"projects/{p['repo']}.svg"] = project(p, i, D["stars"].get(p["repo"], 0))
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
    print(f"wrote {len(files)} svgs · {D['total']} contributions · {D['active']} active days")
