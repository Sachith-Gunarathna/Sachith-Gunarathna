#!/usr/bin/env python3
"""
Asymmetric Bento OS — GitHub Profile README SVG Generator
Author: Sachith Gunarathna (Nexcentauri)
Zero external dependencies (Python 3.9+ stdlib only).

Usage:
  # Generate with live GitHub GraphQL API data:
  GITHUB_TOKEN=ghp_xxx python3 scripts/generate_bento.py

  # Generate locally with preview/fallback metrics:
  python3 scripts/generate_bento.py --preview

  # Optional accent override (orange | lime | ice):
  BENTO_ACCENT=orange python3 scripts/generate_bento.py
"""

from __future__ import annotations

import base64
import datetime
import html
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ==============================================================================
# CONFIGURATION
# ==============================================================================
USERNAME = os.getenv("GITHUB_USERNAME", "Sachith-Gunarathna")
ACCENT_KEY = os.getenv("BENTO_ACCENT", "orange").lower()

ACCENTS = {
    "orange": {
        "accent": "#FF5E1A",
        "soft": "rgba(255, 94, 26, 0.14)",
        "border": "rgba(255, 94, 26, 0.42)",
        "heat": ["#18181D", "#4A1E0C", "#8C330E", "#CC4912", "#FF5E1A"],
    },
    "lime": {
        "accent": "#A3E635",
        "soft": "rgba(163, 230, 53, 0.14)",
        "border": "rgba(163, 230, 53, 0.42)",
        "heat": ["#18181D", "#23360C", "#436B12", "#73B31F", "#A3E635"],
    },
    "ice": {
        "accent": "#E4E4E7",
        "soft": "rgba(228, 228, 231, 0.12)",
        "border": "rgba(228, 228, 231, 0.42)",
        "heat": ["#18181D", "#32323A", "#5E5E6B", "#A1A1AA", "#E4E4E7"],
    },
}

LANG_COLORS = {
    "Java": "#FF5E1A",
    "TypeScript": "#38BDF8",
    "Dart": "#2DD4BF",
    "JavaScript": "#FACC15",
    "Python": "#A78BFA",
    "C++": "#F43F5E",
    "C#": "#239120",
    "PHP": "#777BB4",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Kotlin": "#A97BFF",
    "Swift": "#F05138",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "Shell": "#89E051",
    "Vue": "#41B883",
    "SCSS": "#C6538C",
}

TECH_STACK = {
    "col1": [
        ("Java", "#FF5E1A"),
        ("Spring Boot", "#6DB33F"),
        ("Hibernate", "#BCAE79"),
        ("Node.js", "#339933"),
        ("PHP", "#777BB4"),
        ("Laravel", "#FF2D20"),
        ("Python", "#3776AB"),
        ("C#", "#239120"),
        ("C++", "#00599C"),
    ],
    "col2": [
        ("TypeScript", "#3178C6"),
        ("React", "#61DAFB"),
        ("Next.js", "#FAFAFA"),
        ("Flutter", "#02569B"),
        ("Dart", "#00B4AB"),
        ("React Native", "#61DAFB"),
        ("Tailwind CSS", "#38BDF8"),
    ],
    "col3": [
        ("MySQL", "#4479A1"),
        ("PostgreSQL", "#336791"),
        ("MongoDB", "#47A248"),
        ("Firebase", "#FFCA28"),
        ("Supabase", "#3ECF8E"),
        ("DigitalOcean", "#0080FF"),
        ("Vercel", "#FAFAFA"),
        ("ESP32/ESP8266", "#E7352C"),
        ("Linux", "#FCC624"),
        ("Blender", "#F5792A"),
    ],
}

FONT_DISPLAY = "'Space Grotesk', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
FONT_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', ui-monospace, 'Cascadia Code', 'Fira Code', Consolas, Menlo, monospace"

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
DOCK_DIR = ASSETS_DIR / "dock"


# ==============================================================================
# GITHUB GRAPHQL DATA FETCHER + FALLBACK
# ==============================================================================
def preview_fallback_data() -> dict[str, Any]:
    """Exact preview dataset matching the HTML prototype."""
    seed = 42

    def rand() -> float:
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) % 4294967296
        return seed / 4294967296.0

    cells = []
    for i in range(52 * 7):
        recency = 0.18 if i > 250 else 0.0
        r = rand() + recency
        if r > 0.91:
            lvl = 4
        elif r > 0.77:
            lvl = 3
        elif r > 0.58:
            lvl = 2
        elif r > 0.38:
            lvl = 1
        else:
            lvl = 0
        commits = 0 if lvl == 0 else lvl * 2 + int(rand() * 3)
        cells.append({"level": lvl, "count": commits})

    return {
        "public_repos": 24,
        "contributions": 642,
        "followers": 48,
        "stars": 31,
        "languages": [
            {"name": "Java", "pct": 42.4, "color": "#FF5E1A"},
            {"name": "TypeScript", "pct": 22.8, "color": "#38BDF8"},
            {"name": "Dart", "pct": 14.5, "color": "#2DD4BF"},
            {"name": "JavaScript", "pct": 10.1, "color": "#FACC15"},
            {"name": "Python", "pct": 6.2, "color": "#A78BFA"},
            {"name": "C++", "pct": 4.0, "color": "#F43F5E"},
        ],
        "months": ["Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
        "heatmap": cells,
        "current_streak": 14,
        "best_streak": 42,
        "pulse_delta": "+18%",
        "sparkline": [6, 12, 9, 20, 16, 24, 18, 30, 23, 14, 26, 32, 24, 34, 28, 36],
        "live": False,
    }


def fetch_github_data(username: str, token: str) -> dict[str, Any]:
    query = """
    query($login: String!) {
      user(login: $login) {
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                contributionLevel
                date
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Sachith-Bento-OS-Generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    if "errors" in body or not body.get("data", {}).get("user"):
        raise RuntimeError(f"GitHub GraphQL error: {body.get('errors')}")

    user = body["data"]["user"]
    repos = user["repositories"]
    public_repos = repos["totalCount"]
    followers = user["followers"]["totalCount"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])

    # Aggregate language bytes
    lang_bytes: dict[str, int] = {}
    lang_api_colors: dict[str, str] = {}
    for repo in repos["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            size = edge["size"]
            lang_bytes[name] = lang_bytes.get(name, 0) + size
            if edge["node"].get("color"):
                lang_api_colors[name] = edge["node"]["color"]

    top_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:6]
    total_top_bytes = sum(b for _, b in top_langs) or 1
    languages = []
    for name, size in top_langs:
        pct = round((size / total_top_bytes) * 100.0, 1)
        color = LANG_COLORS.get(name, lang_api_colors.get(name, "#8E8E93"))
        languages.append({"name": name, "pct": pct, "color": color})

    if languages:
        diff = round(100.0 - sum(l["pct"] for l in languages), 1)
        languages[0]["pct"] = round(languages[0]["pct"] + diff, 1)
    else:
        languages = preview_fallback_data()["languages"]

    cal = user["contributionsCollection"]["contributionCalendar"]
    total_contribs = cal["totalContributions"]
    weeks = cal["weeks"][-52:]
    level_map = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }

    flat_days = []
    cells = []
    seen_months = []
    for w in weeks:
        days = w["contributionDays"]
        if days:
            dt = datetime.date.fromisoformat(days[0]["date"])
            m = dt.strftime("%b")
            if not seen_months or seen_months[-1] != m:
                seen_months.append(m)
        for d in days:
            flat_days.append(d)
            cells.append({
                "level": level_map.get(d["contributionLevel"], 0),
                "count": d["contributionCount"],
            })
        for _ in range(7 - len(days)):
            cells.append({"level": 0, "count": 0})

    month_labels = seen_months[-12:]
    while len(month_labels) < 12:
        month_labels.insert(0, "")

    best_streak = 0
    running = 0
    for d in flat_days:
        if d["contributionCount"] > 0:
            running += 1
            best_streak = max(best_streak, running)
        else:
            running = 0

    current_streak = 0
    check_days = list(reversed(flat_days))
    if check_days and check_days[0]["contributionCount"] == 0:
        check_days = check_days[1:]
    for d in check_days:
        if d["contributionCount"] > 0:
            current_streak += 1
        else:
            break

    counts = [d["contributionCount"] for d in flat_days]
    last_30 = sum(counts[-30:]) if len(counts) >= 30 else sum(counts)
    prev_30 = sum(counts[-60:-30]) if len(counts) >= 60 else 0
    if prev_30 > 0:
        delta_pct = round(((last_30 - prev_30) / prev_30) * 100)
        pulse_delta = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
    else:
        pulse_delta = f"+{last_30}" if last_30 > 0 else "0%"

    recent_32 = counts[-32:] if len(counts) >= 32 else ([0] * (32 - len(counts)) + counts)
    sparkline = [recent_32[i] + recent_32[i + 1] for i in range(0, 32, 2)]
    if max(sparkline) == 0:
        sparkline = [1] * 16

    return {
        "public_repos": public_repos,
        "contributions": total_contribs,
        "followers": followers,
        "stars": stars,
        "languages": languages,
        "months": month_labels,
        "heatmap": cells[: 52 * 7],
        "current_streak": current_streak,
        "best_streak": best_streak,
        "pulse_delta": pulse_delta,
        "sparkline": sparkline,
        "live": True,
    }


# ==============================================================================
# PORTRAIT IMAGE LOADER
# ==============================================================================
def load_portrait_data_uri() -> str | None:
    """Checks assets/ for portrait.(jpg|jpeg|png|webp) and returns a base64 data URI."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        candidate = ASSETS_DIR / f"portrait.{ext}"
        if candidate.is_file():
            mime, _ = mimetypes.guess_type(str(candidate))
            mime = mime or f"image/{ext}"
            encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{encoded}"
    return None


# ==============================================================================
# SVG HELPERS
# ==============================================================================
def estimate_mono_width(text: str, font_size: float = 11.0) -> float:
    return len(text) * font_size * 0.62


def build_pill_rows(items: list[tuple[str, str]], max_width: float, gap_x: float = 8.0, gap_y: float = 8.0) -> tuple[list[dict], float]:
    placed = []
    x = 0.0
    y = 0.0
    pill_h = 28.0
    for label, dot_color in items:
        w = round(24.0 + estimate_mono_width(label, 11.0) + 16.0, 1)
        if x > 0 and x + w > max_width:
            x = 0.0
            y += pill_h + gap_y
        placed.append({"x": x, "y": y, "w": w, "h": pill_h, "label": label, "dot": dot_color})
        x += w + gap_x
    total_h = (y + pill_h) if placed else 0.0
    return placed, total_h


def build_sparkline_paths(values: list[int], width: float = 186.0, height: float = 34.0) -> tuple[str, str]:
    n = len(values)
    max_v = max(values) if values else 1
    min_v = min(values) if values else 0
    span = max(max_v - min_v, 1)
    pad_top = 4.0
    pad_bot = 4.0
    usable_h = height - pad_top - pad_bot
    pts = []
    for i, v in enumerate(values):
        px = round((i / max(n - 1, 1)) * width, 1)
        py = round(pad_top + usable_h * (1.0 - (v - min_v) / span), 1)
        pts.append((px, py))
    line_d = " ".join((f"M{x},{y}" if idx == 0 else f"L{x},{y}") for idx, (x, y) in enumerate(pts))
    fill_d = f"{line_d} L{width},{height} L0,{height} Z"
    return fill_d, line_d


# ==============================================================================
# MAIN BENTO OS SVG BUILDER
# ==============================================================================
def build_bento_os_svg(data: dict[str, Any], accent_key: str) -> str:
    theme = ACCENTS.get(accent_key, ACCENTS["orange"])
    accent = theme["accent"]
    heat = theme["heat"]
    portrait_uri = load_portrait_data_uri()

    # Master Layout Constants (Exact 1000px Stage from HTML)
    W = 1000
    PAD = 20
    INNER_W = W - 2 * PAD  # 960
    GAP = 14

    # 12-Col widths (exact proportional grid)
    COL_7 = 554
    COL_5 = 392  # 554 + 14 + 392 = 960
    COL_9 = 716
    COL_3 = 230  # 716 + 14 + 230 = 960

    # Row 1: Hero + Portrait
    R1_Y = PAD
    R1_H = 338

    # Row 2: Telemetry (Pulse + Codebase)
    R2_Y = R1_Y + R1_H + GAP
    R2_H = 228

    # Row 3: Tech Arsenal (compute dynamic height from wrapped pills)
    R3_Y = R2_Y + R2_H + GAP
    col_w = (INNER_W - 48 - 48) / 3.0  # 288px each
    c1_pills, c1_h = build_pill_rows(TECH_STACK["col1"], col_w)
    c2_pills, c2_h = build_pill_rows(TECH_STACK["col2"], col_w)
    c3_pills, c3_h = build_pill_rows(TECH_STACK["col3"], col_w)
    pills_max_h = max(c1_h, c2_h, c3_h)
    R3_H = int(94 + pills_max_h + 24)

    # Row 4: Contribution Matrix + Velocity
    R4_Y = R3_Y + R3_H + GAP
    R4_H = 264

    H = R4_Y + R4_H + PAD

    # --- Portrait Layer ---
    px = PAD + COL_7 + GAP
    py = R1_Y
    if portrait_uri:
        portrait_content = (
            f'<image href="{portrait_uri}" x="{px}" y="{py}" width="{COL_5}" height="{R1_H}" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>\n'
            f'<rect x="{px}" y="{py}" width="{COL_5}" height="{R1_H}" rx="16" '
            f'fill="url(#portraitVignette)" clip-path="url(#portraitClip)"/>'
        )
    else:
        sil_x = px + (COL_5 - 260) / 2
        sil_y = py + R1_H - 270
        portrait_content = (
            f'<rect x="{px}" y="{py}" width="{COL_5}" height="{R1_H}" rx="16" fill="url(#portraitBg)"/>\n'
            f'<g transform="translate({sil_x:.1f}, {sil_y:.1f})" clip-path="url(#silClip)">\n'
            f'  <circle cx="130" cy="92" r="44" fill="url(#devSil)" stroke="#2E2E38" stroke-width="1.5"/>\n'
            f'  <path d="M44 280 C44 196 80 164 130 164 C180 164 216 196 216 280 Z" fill="url(#devSil)" stroke="#2E2E38" stroke-width="1.5"/>\n'
            f'</g>'
        )
    portrait_badge_label = "Sachith Gunarathna"

    # --- Codebase Distribution Bar & Legend ---
    cb_x = PAD + COL_5 + GAP
    cb_y = R2_Y
    bar_x = cb_x + 22
    bar_y = cb_y + 82
    bar_inner_w = COL_7 - 44 - 8
    langs = data["languages"]
    bar_gap = 4.0
    avail_w = bar_inner_w - bar_gap * max(len(langs) - 1, 0)
    bar_rects = []
    cur_bx = bar_x + 4
    for idx, lang in enumerate(langs):
        seg_w = max(4.0, round(avail_w * (lang["pct"] / 100.0), 1))
        if idx == len(langs) - 1:
            seg_w = max(4.0, round((bar_x + 4 + bar_inner_w) - cur_bx, 1))
        bar_rects.append(
            f'<rect x="{cur_bx:.1f}" y="{bar_y + 4}" width="{seg_w:.1f}" height="10" rx="3" fill="{lang["color"]}"/>'
        )
        cur_bx += seg_w + bar_gap

    legend_items = []
    leg_col_w = (COL_7 - 44 - 48) / 3.0
    for idx, lang in enumerate(langs[:6]):
        row = idx // 3
        col = idx % 3
        lx = cb_x + 22 + col * (leg_col_w + 24)
        ly = cb_y + 146 + row * 32
        legend_items.append(
            f'<g>\n'
            f'  <circle cx="{lx + 4:.1f}" cy="{ly - 4}" r="4" fill="{lang["color"]}"/>\n'
            f'  <text x="{lx + 16:.1f}" y="{ly}" fill="#FAFAFA" font-family="{FONT_SANS}" font-size="12" font-weight="500">{html.escape(lang["name"])}</text>\n'
            f'  <text x="{lx + leg_col_w:.1f}" y="{ly}" text-anchor="end" fill="#8E8E93" font-family="{FONT_MONO}" font-size="11">{lang["pct"]:.1f}%</text>\n'
            f'</g>'
        )

    # --- Tech Arsenal Columns ---
    def render_col_pills(pills: list[dict], ox: float, oy: float) -> str:
        out = []
        for p in pills:
            px_ = ox + p["x"]
            py_ = oy + p["y"]
            out.append(
                f'<g>\n'
                f'  <rect x="{px_:.1f}" y="{py_:.1f}" width="{p["w"]:.1f}" height="{p["h"]:.1f}" rx="8" fill="#0D0D10" stroke="#222228" stroke-width="1"/>\n'
                f'  <circle cx="{px_ + 13:.1f}" cy="{py_ + 14:.1f}" r="3" fill="{p["dot"]}"/>\n'
                f'  <text x="{px_ + 22:.1f}" y="{py_ + 18:.1f}" fill="#D4D4D8" font-family="{FONT_MONO}" font-size="11">{html.escape(p["label"])}</text>\n'
                f'</g>'
            )
        return "\n".join(out)

    col1_x = PAD + 24
    col2_x = PAD + 24 + col_w + 24
    col3_x = PAD + 24 + (col_w + 24) * 2
    div1_x = col2_x - 12
    div2_x = col3_x - 12
    pills_y = R3_Y + 94

    # --- 52-Week Contribution Heatmap ---
    hm_x = PAD + 22
    hm_y = R4_Y + 78
    cell_sz = 9.5
    step_x = 12.95
    step_y = 13.0
    heatmap_rects = []
    for i, cell in enumerate(data["heatmap"][: 52 * 7]):
        col = i // 7
        row = i % 7
        cx = hm_x + col * step_x
        cy = hm_y + row * step_y
        fill = heat[min(max(cell["level"], 0), 4)]
        heatmap_rects.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell_sz}" height="{cell_sz}" rx="2" fill="{fill}"/>'
        )

    month_texts = []
    m_step = (52 * step_x) / 12.0
    for idx, m in enumerate(data["months"][:12]):
        mx = hm_x + idx * m_step
        month_texts.append(
            f'<text x="{mx:.1f}" y="{hm_y - 10}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10">{html.escape(m)}</text>'
        )

    # --- Velocity Side-Panel Sparkline ---
    vel_x = PAD + COL_9 + GAP
    vel_y = R4_Y
    spark_fill_d, spark_line_d = build_sparkline_paths(data["sparkline"], width=186.0, height=34.0)

    status_caption = (
        "LIVE TELEMETRY • AUTO-SYNCED VIA GITHUB ACTIONS"
        if data["live"]
        else "52-WEEK COMMIT DENSITY • UTC+5:30"
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none">
  <defs>
    <style>
      @keyframes pulseSignal {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.35; }}
      }}
      .signal-dot {{
        animation: pulseSignal 2s ease-in-out infinite;
      }}
    </style>

    <pattern id="portraitGrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
    </pattern>

    <linearGradient id="portraitBg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#16161B"/>
      <stop offset="50%" stop-color="#101014"/>
      <stop offset="100%" stop-color="#09090B"/>
    </linearGradient>

    <linearGradient id="portraitVignette" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#09090B" stop-opacity="0.15"/>
      <stop offset="65%" stop-color="#09090B" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="#09090B" stop-opacity="0.72"/>
    </linearGradient>

    <linearGradient id="devSil" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#26262E"/>
      <stop offset="100%" stop-color="#121216"/>
    </linearGradient>

    <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
    </linearGradient>

    <filter id="greenGlow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="2.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <clipPath id="portraitClip">
      <rect x="{px}" y="{py}" width="{COL_5}" height="{R1_H}" rx="16"/>
    </clipPath>
    <clipPath id="silClip">
      <rect x="0" y="0" width="260" height="270"/>
    </clipPath>
  </defs>

  <!-- OUTER OBSIDIAN STAGE FRAME -->
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="24" fill="#09090B" stroke="#222228" stroke-width="1"/>

  <!-- ===================================================================== -->
  <!-- 1. TOP BENTO CLUSTER: 7 HERO + 5 PORTRAIT                             -->
  <!-- ===================================================================== -->
  <g>
    <rect x="{PAD}" y="{R1_Y}" width="{COL_7}" height="{R1_H}" rx="16" fill="#121215" stroke="#222228" stroke-width="1"/>

    <!-- Micro-header Pill -->
    <rect x="{PAD + 28}" y="{R1_Y + 26}" width="256" height="26" rx="13" fill="#09090B" stroke="#222228" stroke-width="1"/>
    <circle cx="{PAD + 44}" cy="{R1_Y + 39}" r="4" fill="#34D399" filter="url(#greenGlow)" class="signal-dot"/>
    <text x="{PAD + 56}" y="{R1_Y + 43}" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="10.5" font-weight="600" letter-spacing="1.2">NEXCENTAURI <tspan fill="{accent}">//</tspan> LEAD ENGINEER</text>

    <!-- Top-Right Tag -->
    <text x="{PAD + COL_7 - 28}" y="{R1_Y + 43}" text-anchor="end" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="1.5">SYS.01</text>

    <!-- Massive Display Name -->
    <text x="{PAD + 28}" y="{R1_Y + 114}" fill="#FAFAFA" font-family="{FONT_DISPLAY}" font-size="50" font-weight="700" letter-spacing="-1.4">Sachith</text>
    <text x="{PAD + 28}" y="{R1_Y + 166}" fill="#FAFAFA" font-family="{FONT_DISPLAY}" font-size="50" font-weight="700" letter-spacing="-1.4">Gunarathna<tspan fill="{accent}">.</tspan></text>

    <!-- Concise Punchy Bio -->
    <text x="{PAD + 28}" y="{R1_Y + 202}" fill="#8E8E93" font-family="{FONT_SANS}" font-size="14">
      <tspan fill="#FAFAFA" font-weight="500">BSc (Hons) Software Engineering</tspan> undergraduate (BCU) &amp; Co-Founder at
    </text>
    <text x="{PAD + 28}" y="{R1_Y + 223}" fill="#8E8E93" font-family="{FONT_SANS}" font-size="14">
      <tspan fill="#FAFAFA" font-weight="500">Nexcentauri</tspan>. Building enterprise POS systems, cross-platform mobile
    </text>
    <text x="{PAD + 28}" y="{R1_Y + 244}" fill="#8E8E93" font-family="{FONT_SANS}" font-size="14">
      apps, cloud infrastructure, and ESP32/ESP8266 IoT hardware.
    </text>

    <!-- Hairline Divider -->
    <line x1="{PAD + 28}" y1="{R1_Y + 272}" x2="{PAD + COL_7 - 28}" y2="{R1_Y + 272}" stroke="#222228" stroke-width="1"/>

    <!-- Bottom Pill Tags -->
    <g transform="translate({PAD + 28}, {R1_Y + 288})">
      <rect x="0" y="0" width="178" height="28" rx="8" fill="#09090B" stroke="#222228" stroke-width="1"/>
      <circle cx="14" cy="14" r="3" fill="{accent}"/>
      <text x="24" y="18" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="11">Sri Lanka • GMT+5:30</text>

      <rect x="186" y="0" width="136" height="28" rx="8" fill="#09090B" stroke="#222228" stroke-width="1"/>
      <text x="198" y="18" fill="#8E8E93" font-family="{FONT_MONO}" font-size="11">Full-Stack &amp; IoT</text>

      <rect x="330" y="0" width="146" height="28" rx="8" fill="#09090B" stroke="#222228" stroke-width="1"/>
      <text x="342" y="18" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="11" font-weight="500">nexcentauri.com <tspan fill="{accent}">↗</tspan></text>
    </g>
  </g>

  <!-- Right Card (5 cols): Full-Bleed Stylized Portrait Card -->
  <g>
    {portrait_content}
    <rect x="{px}" y="{py}" width="{COL_5}" height="{R1_H}" rx="16" fill="url(#portraitGrid)" opacity="0.65"/>
    <rect x="{px}" y="{py}" width="{COL_5}" height="{R1_H}" rx="16" fill="none" stroke="#222228" stroke-width="1"/>

    <!-- 4 Corner Crosshair Brackets -->
    <path d="M{px + 14} {py + 30} V{py + 14} H{px + 30}" stroke="{accent}" stroke-width="2" fill="none"/>
    <path d="M{px + COL_5 - 30} {py + 14} H{px + COL_5 - 14} V{py + 30}" stroke="rgba(255,255,255,0.30)" stroke-width="2" fill="none"/>
    <path d="M{px + 14} {py + R1_H - 30} V{py + R1_H - 14} H{px + 30}" stroke="rgba(255,255,255,0.30)" stroke-width="2" fill="none"/>
    <path d="M{px + COL_5 - 30} {py + R1_H - 14} H{px + COL_5 - 14} V{py + R1_H - 30}" stroke="{accent}" stroke-width="2" fill="none"/>

    <text x="{px + COL_5 - 24}" y="{py + 30}" text-anchor="end" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="1.4">ID // 06-2004</text>

    <!-- Floating Glassmorphic Bottom Badge -->
    <rect x="{px + 18}" y="{py + R1_H - 56}" width="{COL_5 - 36}" height="38" rx="12" fill="#09090B" fill-opacity="0.80" stroke="rgba(255,255,255,0.12)" stroke-width="1"/>
    <g transform="translate({px + 32}, {py + R1_H - 44})" stroke="{accent}" stroke-width="1.8" fill="none">
      <rect x="0" y="0" width="14" height="14" rx="2"/>
      <circle cx="4.5" cy="4.5" r="1.1" fill="{accent}"/>
      <polyline points="14 9.5 10 6 2 14"/>
    </g>
    <text x="{px + 54}" y="{py + R1_H - 33}" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="11" font-weight="500">{html.escape(portrait_badge_label)}</text>
    <text x="{px + COL_5 - 32}" y="{py + R1_H - 33}" text-anchor="end" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10">RAW</text>
  </g>

  <!-- ===================================================================== -->
  <!-- 2. MIDDLE TELEMETRY BENTO ROW: 5 PULSE + 7 CODEBASE                   -->
  <!-- ===================================================================== -->
  <g>
    <rect x="{PAD}" y="{R2_Y}" width="{COL_5}" height="{R2_H}" rx="16" fill="#121215" stroke="#222228" stroke-width="1"/>
    <text x="{PAD + 20}" y="{R2_Y + 30}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.4">01 // GITHUB PULSE</text>
    <circle cx="{PAD + COL_5 - 22}" cy="{R2_Y + 26}" r="3" fill="{accent}"/>

    <rect x="{PAD + 20}" y="{R2_Y + 48}" width="171" height="74" rx="12" fill="#09090B" stroke="#222228" stroke-width="1"/>
    <text x="{PAD + 34}" y="{R2_Y + 69}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="0.8">PUBLIC REPOS</text>
    <circle cx="{PAD + 177}" cy="{R2_Y + 65}" r="3" fill="{accent}"/>
    <text x="{PAD + 34}" y="{R2_Y + 107}" fill="#FAFAFA" font-family="{FONT_DISPLAY}" font-size="30" font-weight="700">{data['public_repos']}</text>

    <rect x="{PAD + 201}" y="{R2_Y + 48}" width="171" height="74" rx="12" fill="#09090B" stroke="#222228" stroke-width="1"/>
    <text x="{PAD + 215}" y="{R2_Y + 69}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="0.8">CONTRIBUTIONS</text>
    <circle cx="{PAD + 358}" cy="{R2_Y + 65}" r="3" fill="{accent}"/>
    <text x="{PAD + 215}" y="{R2_Y + 107}" fill="{accent}" font-family="{FONT_DISPLAY}" font-size="30" font-weight="700">{data['contributions']}</text>

    <rect x="{PAD + 20}" y="{R2_Y + 132}" width="171" height="74" rx="12" fill="#09090B" stroke="#222228" stroke-width="1"/>
    <text x="{PAD + 34}" y="{R2_Y + 153}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="0.8">FOLLOWERS</text>
    <circle cx="{PAD + 177}" cy="{R2_Y + 149}" r="3" fill="#3F3F46"/>
    <text x="{PAD + 34}" y="{R2_Y + 191}" fill="#FAFAFA" font-family="{FONT_DISPLAY}" font-size="30" font-weight="700">{data['followers']}</text>

    <rect x="{PAD + 201}" y="{R2_Y + 132}" width="171" height="74" rx="12" fill="#09090B" stroke="#222228" stroke-width="1"/>
    <text x="{PAD + 215}" y="{R2_Y + 153}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="0.8">STARS</text>
    <circle cx="{PAD + 358}" cy="{R2_Y + 149}" r="3" fill="#3F3F46"/>
    <text x="{PAD + 215}" y="{R2_Y + 191}" fill="#FAFAFA" font-family="{FONT_DISPLAY}" font-size="30" font-weight="700">{data['stars']}</text>
  </g>

  <g>
    <rect x="{cb_x}" y="{cb_y}" width="{COL_7}" height="{R2_H}" rx="16" fill="#121215" stroke="#222228" stroke-width="1"/>
    <text x="{cb_x + 22}" y="{cb_y + 30}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.4">02 // CODEBASE DISTRIBUTION</text>
    <text x="{cb_x + COL_7 - 22}" y="{cb_y + 30}" text-anchor="end" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="0.8">PUBLIC SOURCE BYTES</text>

    <rect x="{bar_x}" y="{bar_y}" width="{COL_7 - 44}" height="18" rx="8" fill="#09090B" stroke="#222228" stroke-width="1"/>
    {''.join(bar_rects)}

    {''.join(legend_items)}
  </g>

  <!-- ===================================================================== -->
  <!-- 3. TECH ARSENAL BENTO CARD (3-COLUMN ARCHITECTURAL)                   -->
  <!-- ===================================================================== -->
  <g>
    <rect x="{PAD}" y="{R3_Y}" width="{INNER_W}" height="{R3_H}" rx="16" fill="#121215" stroke="#222228" stroke-width="1"/>
    <text x="{PAD + 24}" y="{R3_Y + 32}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.4">03 // TECH ARSENAL</text>
    <text x="{PAD + INNER_W - 24}" y="{R3_Y + 32}" text-anchor="end" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="0.8">PRODUCTION STACK</text>
    <line x1="{PAD + 24}" y1="{R3_Y + 48}" x2="{PAD + INNER_W - 24}" y2="{R3_Y + 48}" stroke="#222228" stroke-width="1"/>

    <text x="{col1_x:.1f}" y="{R3_Y + 76}" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.2"><tspan fill="{accent}">01 /</tspan> CORE &amp; BACKEND</text>
    {render_col_pills(c1_pills, col1_x, pills_y)}

    <line x1="{div1_x:.1f}" y1="{R3_Y + 64}" x2="{div1_x:.1f}" y2="{R3_Y + R3_H - 22}" stroke="#222228" stroke-width="1"/>

    <text x="{col2_x:.1f}" y="{R3_Y + 76}" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.2"><tspan fill="{accent}">02 /</tspan> WEB &amp; MOBILE</text>
    {render_col_pills(c2_pills, col2_x, pills_y)}

    <line x1="{div2_x:.1f}" y1="{R3_Y + 64}" x2="{div2_x:.1f}" y2="{R3_Y + R3_H - 22}" stroke="#222228" stroke-width="1"/>

    <text x="{col3_x:.1f}" y="{R3_Y + 76}" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.2"><tspan fill="{accent}">03 /</tspan> DATA, CLOUD &amp; IOT</text>
    {render_col_pills(c3_pills, col3_x, pills_y)}
  </g>

  <!-- ===================================================================== -->
  <!-- 4. CONTRIBUTION MATRIX (9) + VELOCITY SIDE-PANEL (3)                  -->
  <!-- ===================================================================== -->
  <g>
    <rect x="{PAD}" y="{R4_Y}" width="{COL_9}" height="{R4_H}" rx="16" fill="#121215" stroke="#222228" stroke-width="1"/>
    <text x="{PAD + 22}" y="{R4_Y + 32}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.4">04 // CONTRIBUTION MATRIX</text>
    <text x="{PAD + COL_9 - 22}" y="{R4_Y + 32}" text-anchor="end" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="0.8">52 WEEKS • UTC+5:30</text>

    {''.join(month_texts)}
    {''.join(heatmap_rects)}

    <text x="{PAD + 22}" y="{R4_Y + R4_H - 24}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10">{status_caption}</text>
    <g transform="translate({PAD + COL_9 - 160}, {R4_Y + R4_H - 34})">
      <text x="0" y="10" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10">LESS</text>
      <rect x="32" y="1" width="10" height="10" rx="2" fill="{heat[0]}"/>
      <rect x="46" y="1" width="10" height="10" rx="2" fill="{heat[1]}"/>
      <rect x="60" y="1" width="10" height="10" rx="2" fill="{heat[2]}"/>
      <rect x="74" y="1" width="10" height="10" rx="2" fill="{heat[3]}"/>
      <rect x="88" y="1" width="10" height="10" rx="2" fill="{heat[4]}"/>
      <text x="106" y="10" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10">MORE</text>
    </g>
  </g>

  <g>
    <rect x="{vel_x}" y="{vel_y}" width="{COL_3}" height="{R4_H}" rx="16" fill="#121215" stroke="#222228" stroke-width="1"/>
    <text x="{vel_x + 22}" y="{vel_y + 32}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="11" font-weight="600" letter-spacing="1.4">VELOCITY</text>

    <rect x="{vel_x + 20}" y="{vel_y + 48}" width="{COL_3 - 40}" height="62" rx="12" fill="#09090B" stroke="#222228" stroke-width="1"/>
    <text x="{vel_x + 32}" y="{vel_y + 66}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="9.5" letter-spacing="0.8">CURRENT STREAK</text>
    <text x="{vel_x + 32}" y="{vel_y + 98}" fill="{accent}" font-family="{FONT_DISPLAY}" font-size="24" font-weight="700">{data['current_streak']} <tspan fill="#8E8E93" font-family="{FONT_SANS}" font-size="12" font-weight="400">days</tspan></text>

    <rect x="{vel_x + 20}" y="{vel_y + 120}" width="{COL_3 - 40}" height="62" rx="12" fill="#09090B" stroke="#222228" stroke-width="1"/>
    <text x="{vel_x + 32}" y="{vel_y + 138}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="9.5" letter-spacing="0.8">BEST STREAK</text>
    <text x="{vel_x + 32}" y="{vel_y + 170}" fill="#FAFAFA" font-family="{FONT_DISPLAY}" font-size="24" font-weight="700">{data['best_streak']} <tspan fill="#8E8E93" font-family="{FONT_SANS}" font-size="12" font-weight="400">days</tspan></text>

    <line x1="{vel_x + 20}" y1="{vel_y + 194}" x2="{vel_x + COL_3 - 20}" y2="{vel_y + 194}" stroke="#222228" stroke-width="1"/>
    <text x="{vel_x + 22}" y="{vel_y + 210}" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10">30D PULSE</text>
    <text x="{vel_x + COL_3 - 22}" y="{vel_y + 210}" text-anchor="end" fill="{accent}" font-family="{FONT_MONO}" font-size="10" font-weight="600">{html.escape(data['pulse_delta'])}</text>

    <g transform="translate({vel_x + 22}, {vel_y + 218})">
      <path d="{spark_fill_d}" fill="url(#sparkFill)"/>
      <path d="{spark_line_d}" fill="none" stroke="{accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
  </g>
</svg>
"""
    return svg


# ==============================================================================
# CLICKABLE CONNECT DOCK + FOOTER SVGs
# ==============================================================================
def build_dock_svgs(accent_key: str) -> dict[str, str]:
    theme = ACCENTS.get(accent_key, ACCENTS["orange"])
    accent = theme["accent"]

    items = [
        (
            "dock-nexcentauri.svg",
            "Nexcentauri",
            128,
            f'<g transform="translate(15, 11) scale(0.62)" stroke="{accent}" stroke-width="2.1" fill="none"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></g>',
        ),
        (
            "dock-linkedin.svg",
            "LinkedIn",
            106,
            '<g transform="translate(15, 11) scale(0.62)" fill="#8E8E93"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></g>',
        ),
        (
            "dock-email.svg",
            "Email",
            88,
            '<g transform="translate(15, 11) scale(0.62)" stroke="#8E8E93" stroke-width="2.1" fill="none"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></g>',
        ),
        (
            "dock-github.svg",
            "GitHub",
            96,
            '<g transform="translate(15, 11) scale(0.92)" fill="#8E8E93"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></g>',
        ),
        (
            "dock-instagram.svg",
            "Instagram",
            114,
            '<g transform="translate(15, 11) scale(0.62)" stroke="#8E8E93" stroke-width="2.1" fill="none"><rect x="2" y="2" width="20" height="20" rx="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></g>',
        ),
        (
            "dock-youtube.svg",
            "YouTube",
            104,
            '<g transform="translate(15, 11) scale(0.62)" stroke="#8E8E93" stroke-width="2.1" fill="none"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"/><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"/></g>',
        ),
    ]

    svgs = {}
    for fname, label, width, icon_svg in items:
        svgs[fname] = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="36" viewBox="0 0 {width} 36" fill="none">\n'
            f'  <rect x="0.5" y="0.5" width="{width - 1}" height="35" rx="17.5" fill="#121215" stroke="#222228" stroke-width="1"/>\n'
            f'  {icon_svg}\n'
            f'  <text x="38" y="22" fill="#FAFAFA" font-family="{FONT_MONO}" font-size="11.5" font-weight="500">{label}</text>\n'
            f'</svg>\n'
        )
    return svgs


def build_footer_svg() -> str:
    year = datetime.datetime.now().year
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="24" viewBox="0 0 600 24" fill="none">\n'
        f'  <text x="300" y="15" text-anchor="middle" fill="#8E8E93" font-family="{FONT_MONO}" font-size="10" letter-spacing="1.8">'
        f'SACHITH GUNARATHNA © {year}</text>\n'
        f'</svg>\n'
    )


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    DOCK_DIR.mkdir(parents=True, exist_ok=True)

    use_preview = "--preview" in sys.argv
    token = os.getenv("GITHUB_TOKEN", "").strip()

    if use_preview or not token:
        data = preview_fallback_data()
        print("[Bento OS] Using preview fallback dataset.")
    else:
        try:
            data = fetch_github_data(USERNAME, token)
            print(f"[Bento OS] Fetched live GitHub telemetry for @{USERNAME}.")
        except Exception as exc:
            print(f"[Bento OS] Live fetch failed ({exc}); falling back to preview dataset.")
            data = preview_fallback_data()

    bento_svg = build_bento_os_svg(data, ACCENT_KEY)
    (ASSETS_DIR / "bento-os.svg").write_text(bento_svg, encoding="utf-8")

    for fname, content in build_dock_svgs(ACCENT_KEY).items():
        (DOCK_DIR / fname).write_text(content, encoding="utf-8")

    (ASSETS_DIR / "footer.svg").write_text(build_footer_svg(), encoding="utf-8")

    print(f"[Bento OS] Generated SVGs in {ASSETS_DIR} (accent={ACCENT_KEY}).")


if __name__ == "__main__":
    main()
