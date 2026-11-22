// Exact Asymmetric Bento OS Telemetry Generator (Matches github_profile_preview_sachith_gunarathna.html 1:1)
// Node.js 22+, zero dependencies.
import { mkdir, writeFile, rename } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const ASSETS = new URL('../assets/', import.meta.url);
const DAY = 86_400_000;

const ACCENTS = {
  SIGNAL_ORANGE: { accent: '#FF5E1A', heat: ['#18181D', '#4A1E0C', '#8C330E', '#CC4912', '#FF5E1A'] },
  ACID_LIME:     { accent: '#A3E635', heat: ['#18181D', '#23360C', '#436B12', '#73B31F', '#A3E635'] },
  PURE_ICE:      { accent: '#E4E4E7', heat: ['#18181D', '#32323A', '#5E5E6B', '#A1A1AA', '#E4E4E7'] }
};
const THEME = ACCENTS[process.env.BENTO_THEME || 'SIGNAL_ORANGE'] || ACCENTS.SIGNAL_ORANGE;

const C = {
  bg: '#09090B',
  card: '#121215',
  border: '#222228',
  text: '#FAFAFA',
  muted: '#8E8E93',
  dim: '#3F3F46',
  accent: THEME.accent,
  sans: 'Arial, Helvetica, sans-serif',
  mono: 'Consolas, Courier New, monospace'
};

const LANG_COLORS = {
  Java: '#FF5E1A',
  TypeScript: '#38BDF8',
  Dart: '#2DD4BF',
  JavaScript: '#FACC15',
  Python: '#A78BFA',
  'C++': '#F43F5E',
  PHP: '#818CF8',
  'C#': '#22C55E',
  HTML: '#FB923C',
  CSS: '#C084FC',
  Other: '#71717A'
};

const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]));
const fmt = (n) => new Intl.NumberFormat('en-US').format(n);
const dateMs = (d) => Date.parse(d + 'T00:00:00Z');

function todayInZone(now, timeZone) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
  const p = (t) => parts.find((x) => x.type === t).value;
  return `${p('year')}-${p('month')}-${p('day')}`;
}

function parsePublicCalendar(html) {
  const days = new Map();
  for (const m of html.matchAll(/<(?:td|rect)\b[^>]*\bdata-date\s*=\s*"(\d{4}-\d{2}-\d{2})"[^>]*>/gi)) {
    const lvl = m[0].match(/data-level="(\d+)"/);
    days.set(m[1], lvl ? Number(lvl[1]) : 0);
  }
  return days;
}

function calendarWindow(source, end) {
  const last = dateMs(end);
  const first = last - 364 * DAY;
  const days = Array.from({ length: 365 }, (_, i) => {
    const date = new Date(first + i * DAY).toISOString().slice(0, 10);
    return { date, count: source.get(date) ?? 0 };
  });
  let current = 0, idx = days.length - 1;
  if (days[idx].count === 0) idx -= 1;
  while (idx >= 0 && days[idx].count > 0) { current += 1; idx -= 1; }
  let longest = 0, run = 0;
  for (const d of days) { run = d.count > 0 ? run + 1 : 0; longest = Math.max(longest, run); }
  return { days, current, longest, total: days.reduce((s, d) => s + d.count, 0) };
}

function languageShares(totals) {
  const rows = Object.entries(totals).filter(([, b]) => b > 0).sort((a, b) => b[1] - a[1]);
  const total = rows.reduce((s, [, b]) => s + b, 0) || 1;
  const visible = rows.length <= 6 ? rows : [...rows.slice(0, 5), ['Other', rows.slice(5).reduce((s, [, b]) => s + b, 0)]];
  return visible.map(([name, bytes]) => ({ name, pct: (bytes / total) * 100, color: LANG_COLORS[name] || C.accent }));
}

// ROW 2: 5-col GitHub Pulse + 7-col Codebase Distribution (1000 x 256)
export function telemetryRowSvg(data) {
  const stars = data.repos.reduce((s, r) => s + Number(r.stargazers_count || 0), 0);
  const langs = languageShares(data.languages);

  const metrics = [
    ['PUBLIC REPOS', fmt(data.user.public_repos), C.text, C.accent],
    ['CONTRIBUTIONS', fmt(data.calendar.total), C.accent, C.accent],
    ['FOLLOWERS', fmt(data.user.followers), C.text, C.dim],
    ['STARS', fmt(stars), C.text, C.dim]
  ];

  let pulseCards = '';
  metrics.forEach(([label, val, valCol, dotCol], i) => {
    const x = 32 + (i % 2) * 184;
    const y = 62 + Math.floor(i / 2) * 88;
    pulseCards += `
    <rect x="${x}" y="${y}" width="174" height="78" rx="12" fill="${C.bg}" stroke="${C.border}"/>
    <text x="${x + 14}" y="${y + 22}" fill="${C.muted}" font-family="${C.mono}" font-size="9.5" letter-spacing="0.8">${label}</text>
    <circle cx="${x + 158}" cy="${y + 19}" r="3" fill="${dotCol}"/>
    <text x="${x + 14}" y="${y + 60}" fill="${valCol}" font-family="${C.sans}" font-size="30" font-weight="800">${val}</text>`;
  });

  // Segmented horizontal bar
  const barX = 448, barY = 98, barW = 516, barH = 16;
  let barSegs = `<rect x="${barX - 4}" y="${barY - 4}" width="${barW + 8}" height="${barH + 8}" rx="8" fill="${C.bg}" stroke="${C.border}"/>`;
  let curX = barX;
  langs.forEach((l) => {
    const w = Math.max(4, (l.pct / 100) * barW - 3);
    barSegs += `<rect x="${curX.toFixed(1)}" y="${barY}" width="${w.toFixed(1)}" height="${barH}" rx="3" fill="${l.color}"/>`;
    curX += (l.pct / 100) * barW;
  });

  // 2-row x 3-col dot legend
  let legend = '';
  langs.forEach((l, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 448 + col * 176;
    const y = 166 + row * 34;
    legend += `
    <circle cx="${x + 5}" cy="${y - 4}" r="4" fill="${l.color}"/>
    <text x="${x + 16}" y="${y}" fill="${C.text}" font-family="${C.sans}" font-size="12.5" font-weight="600">${esc(l.name)}</text>
    <text x="${x + 158}" y="${y}" fill="${C.muted}" font-family="${C.mono}" font-size="11.5" text-anchor="end">${l.pct.toFixed(1)}%</text>`;
  });

  return `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="256" viewBox="0 0 1000 256" role="img" aria-label="GitHub Pulse and Codebase Distribution">
  <rect width="1000" height="256" fill="${C.bg}"/>

  <!-- Left 5-col Card: GitHub Pulse -->
  <rect x="12" y="6" width="398" height="244" rx="16" fill="${C.card}" stroke="${C.border}"/>
  <text x="32" y="38" fill="${C.muted}" font-family="${C.mono}" font-size="11" font-weight="700" letter-spacing="1.4">01 // GITHUB PULSE</text>
  <circle cx="386" cy="34" r="3.5" fill="${C.accent}"/>
  ${pulseCards}

  <!-- Right 7-col Card: Codebase Distribution -->
  <rect x="424" y="6" width="564" height="244" rx="16" fill="${C.card}" stroke="${C.border}"/>
  <text x="448" y="38" fill="${C.muted}" font-family="${C.mono}" font-size="11" font-weight="700" letter-spacing="1.4">02 // CODEBASE DISTRIBUTION</text>
  <text x="964" y="38" fill="${C.muted}" font-family="${C.mono}" font-size="10" text-anchor="end">PUBLIC SOURCE BYTES</text>
  ${barSegs}
  ${legend}
</svg>\n`;
}

// ROW 4: 9-col Contribution Matrix + 3-col Velocity Panel (1000 x 258)
export function contributionVelocitySvg(data) {
  const { days, current, longest } = data.calendar;
  const first = dateMs(days[0].date);
  const start = first - new Date(first).getUTCDay() * DAY;
  const max = Math.max(1, ...days.map((d) => d.count));

  let cells = '';
  const step = 12.8, size = 9.8, gx = 36, gy = 78;
  days.forEach((d) => {
    const off = Math.round((dateMs(d.date) - start) / DAY);
    const col = Math.floor(off / 7), row = off % 7;
    if (col > 52) return;
    const lvl = d.count === 0 ? 0 : Math.min(4, Math.max(1, Math.ceil((d.count / max) * 4)));
    cells += `<rect x="${(gx + col * step).toFixed(1)}" y="${(gy + row * step).toFixed(1)}" width="${size}" height="${size}" rx="2" fill="${THEME.heat[lvl]}"><title>${d.date}: ${d.count}</title></rect>`;
  });

  // Month labels
  const months = ['Dec','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov'];
  const monthLabels = months.map((m, i) => `<text x="${36 + i * 56}" y="66" fill="${C.muted}" font-family="${C.mono}" font-size="10">${m}</text>`).join('');

  // 30D Sparkline
  const recent = days.slice(-30);
  const rMax = Math.max(1, ...recent.map((d) => d.count));
  const pts = recent.map((d, i) => [776 + i * 6.4, 232 - (d.count / rMax) * 28]);
  const lineD = 'M' + pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' L');
  const areaD = `${lineD} L${pts.at(-1)[0].toFixed(1)},234 L776,234 Z`;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="258" viewBox="0 0 1000 258" role="img" aria-label="Contribution Matrix and Velocity">
  <defs>
    <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${C.accent}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="${C.accent}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1000" height="258" fill="${C.bg}"/>

  <!-- Left 9-col Card: 52-Week Heatmap -->
  <rect x="12" y="6" width="728" height="246" rx="16" fill="${C.card}" stroke="${C.border}"/>
  <text x="36" y="38" fill="${C.muted}" font-family="${C.mono}" font-size="11" font-weight="700" letter-spacing="1.4">04 // CONTRIBUTION MATRIX</text>
  <text x="716" y="38" fill="${C.muted}" font-family="${C.mono}" font-size="10" text-anchor="end">52 WEEKS • UTC+5:30</text>
  ${monthLabels}
  ${cells}

  <!-- Legend -->
  <text x="36" y="232" fill="${C.muted}" font-family="${C.mono}" font-size="10">Automated daily GitHub telemetry</text>
  <text x="580" y="232" fill="${C.muted}" font-family="${C.mono}" font-size="9.5">LESS</text>
  ${THEME.heat.map((h, i) => `<rect x="${614 + i * 14}" y="223" width="10" height="10" rx="2" fill="${h}"/>`).join('')}
  <text x="688" y="232" fill="${C.muted}" font-family="${C.mono}" font-size="9.5">MORE</text>

  <!-- Right 3-col Card: Velocity Panel -->
  <rect x="754" y="6" width="234" height="246" rx="16" fill="${C.card}" stroke="${C.border}"/>
  <text x="774" y="36" fill="${C.muted}" font-family="${C.mono}" font-size="11" font-weight="700" letter-spacing="1.4">VELOCITY</text>

  <rect x="774" y="52" width="194" height="58" rx="10" fill="${C.bg}" stroke="${C.border}"/>
  <text x="786" y="72" fill="${C.muted}" font-family="${C.mono}" font-size="9.5">CURRENT STREAK</text>
  <text x="786" y="99" fill="${C.accent}" font-family="${C.sans}" font-size="24" font-weight="800">${current} <tspan fill="${C.muted}" font-size="12" font-weight="400">days</tspan></text>

  <rect x="774" y="120" width="194" height="58" rx="10" fill="${C.bg}" stroke="${C.border}"/>
  <text x="786" y="140" fill="${C.muted}" font-family="${C.mono}" font-size="9.5">BEST STREAK</text>
  <text x="786" y="167" fill="${C.text}" font-family="${C.sans}" font-size="24" font-weight="800">${longest} <tspan fill="${C.muted}" font-size="12" font-weight="400">days</tspan></text>

  <line x1="774" y1="188" x2="968" y2="188" stroke="${C.border}"/>
  <text x="774" y="203" fill="${C.muted}" font-family="${C.mono}" font-size="9.5">30D PULSE</text>
  <text x="968" y="203" fill="${C.accent}" font-family="${C.mono}" font-size="9.5" text-anchor="end">LIVE</text>
  <path d="${areaD}" fill="url(#sparkFill)"/>
  <path d="${lineD}" fill="none" stroke="${C.accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>\n`;
}

async function collectProfile({ userName, token = '', now = new Date(), timeZone = 'Asia/Colombo' }) {
  const userPart = encodeURIComponent(userName);
  const end = todayInZone(now, timeZone);
  const start = new Date(dateMs(end) - 364 * DAY).toISOString().slice(0, 10);

  async function req(url, opts = {}, asText = false) {
    const headers = { 'User-Agent': 'Sachith-Bento-OS', Accept: asText ? 'text/html' : 'application/vnd.github+json', ...opts.headers };
    if (token && new URL(url).hostname === 'api.github.com') headers.Authorization = `Bearer ${token}`;
    const res = await fetch(url, { ...opts, headers });
    if (!res.ok) throw new Error(`HTTP ${res.status} on ${url}`);
    return asText ? res.text() : res.json();
  }

  const user = await req(`https://api.github.com/users/${userPart}`);
  const repos = await req(`https://api.github.com/users/${userPart}/repos?type=owner&per_page=100`);
  const sourceRepos = repos.filter((r) => !r.fork && r.name.toLowerCase() !== userName.toLowerCase() && r.size > 0);
  const languages = {};
  for (let i = 0; i < sourceRepos.length; i += 4) {
    const batch = await Promise.all(sourceRepos.slice(i, i + 4).map((r) => req(`https://api.github.com/repos/${userPart}/${encodeURIComponent(r.name)}/languages`)));
    for (const totals of batch) {
      for (const [lang, bytes] of Object.entries(totals)) languages[lang] = (languages[lang] || 0) + bytes;
    }
  }

  let source;
  if (token) {
    try {
      const gql = await req('https://api.github.com/graphql', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'query($login: String!, $from: DateTime!, $to: DateTime!) { user(login: $login) { contributionsCollection(from: $from, to: $to) { contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }',
          variables: { login: userName, from: `${start}T00:00:00Z`, to: now.toISOString() }
        })
      });
      const weeks = gql.data?.user?.contributionsCollection?.contributionCalendar?.weeks || [];
      source = new Map(weeks.flatMap((w) => w.contributionDays.map((d) => [d.date, d.contributionCount])));
    } catch { /* fallback */ }
  }
  if (!source) {
    const html = await req(`https://github.com/users/${userPart}/contributions?from=${start}&to=${end}`, {}, true);
    source = parsePublicCalendar(html);
  }
  return { user, repos, languages, calendar: calendarWindow(source, end), now };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const userName = process.env.PROFILE_USER || 'Sachith-Gunarathna';
  const data = await collectProfile({ userName, token: process.env.GITHUB_TOKEN || '', timeZone: 'Asia/Colombo' });
  const cards = {
    '02-telemetry-row.svg': telemetryRowSvg(data),
    '04-contribution-velocity.svg': contributionVelocitySvg(data)
  };
  await mkdir(ASSETS, { recursive: true });
  for (const [name, content] of Object.entries(cards)) {
    await writeFile(new URL(name + '.tmp', ASSETS), content, 'utf8');
    await rename(new URL(name + '.tmp', ASSETS), new URL(name, ASSETS));
  }
  console.log(`Updated exact Bento OS telemetry SVGs for ${userName}`);
}
