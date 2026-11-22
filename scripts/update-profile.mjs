// Swiss-Editorial / Asymmetric Bento OS — Automated GitHub Telemetry Generator
// Node.js 22+, zero external dependencies. No font-paths.json needed!
import { mkdir, writeFile, rename } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const ASSETS = new URL('../assets/', import.meta.url);
const DAY = 86_400_000;

// Change ACCENT_THEME to 'SIGNAL_ORANGE', 'ACID_LIME', or 'PURE_ICE' anytime!
const THEMES = {
  SIGNAL_ORANGE: { accent: '#FF5722', soft: '#2A150E', heat: ['#18181B', '#431407', '#9A3412', '#EA580C', '#FF5722'] },
  ACID_LIME:     { accent: '#C4F53A', soft: '#1D2608', heat: ['#18181B', '#1A2E05', '#3F6212', '#84CC16', '#C4F53A'] },
  PURE_ICE:      { accent: '#38BDF8', soft: '#082032', heat: ['#18181B', '#0C4A6E', '#0284C7', '#38BDF8', '#7DD3FC'] }
};
const ACTIVE = THEMES[process.env.BENTO_THEME || 'SIGNAL_ORANGE'] || THEMES.SIGNAL_ORANGE;

const T = {
  bg: '#0B0B0C',
  card: '#141416',
  card2: '#1A1A1E',
  border: '#27272A',
  ink: '#FAFAFA',
  muted: '#A1A1AA',
  dim: '#71717A',
  accent: ACTIVE.accent,
  soft: ACTIVE.soft,
  sans: "Segoe UI, Helvetica, Arial, sans-serif",
  mono: "Consolas, Menlo, monospace"
};

const LANGUAGE_COLORS = {
  Java: '#FF5722',
  TypeScript: '#38BDF8',
  JavaScript: '#FACC15',
  Dart: '#2DD4BF',
  Python: '#60A5FA',
  PHP: '#A78BFA',
  'C++': '#F43F5E',
  'C#': '#22C55E',
  HTML: '#FB923C',
  CSS: '#C084FC',
  Other: '#71717A'
};

const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]));
const fmt = (n) => new Intl.NumberFormat('en-US').format(n);
const ts = (d) => d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC';
const dateMs = (d) => Date.parse(d + 'T00:00:00Z');

function todayInZone(now, timeZone) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
  const p = (t) => parts.find((x) => x.type === t).value;
  return `${p('year')}-${p('month')}-${p('day')}`;
}

function parsePublicCalendar(html) {
  const days = new Map();
  for (const match of html.matchAll(/<(?:td|rect)\b[^>]*\bdata-date\s*=\s*"(\d{4}-\d{2}-\d{2})"[^>]*>/gi)) {
    const tag = match[0];
    const date = match[1];
    const levelMatch = tag.match(/data-level="(\d+)"/);
    days.set(date, levelMatch ? Number(levelMatch[1]) : 0);
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
  let current = 0;
  let idx = days.length - 1;
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
  return visible.map(([name, bytes]) => ({ name, bytes, percent: (bytes / total) * 100, color: LANGUAGE_COLORS[name] || T.accent }));
}

function wrapSvg(w, h, title, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(title)}"><rect width="${w}" height="${h}" fill="${T.bg}"/>${body}</svg>\n`;
}

function headerBar(x0, w, num, label, rightLabel) {
  return `
  <rect x="${x0}" y="16" width="36" height="22" rx="4" fill="${T.soft}" stroke="${T.accent}"/>
  <text x="${x0 + 18}" y="31" fill="${T.accent}" font-family="${T.mono}" font-size="11.5" font-weight="700" text-anchor="middle">${num}</text>
  <text x="${x0 + 48}" y="31" fill="${T.muted}" font-family="${T.mono}" font-size="12" font-weight="600" letter-spacing="1.5">${label}</text>
  <text x="${w - x0}" y="31" fill="${T.dim}" font-family="${T.mono}" font-size="12" text-anchor="end">${esc(rightLabel)}</text>
  <line x1="${x0}" y1="50" x2="${w - x0}" y2="50" stroke="${T.border}"/>`;
}

export function overviewSvg(data, mobile = false) {
  const w = mobile ? 560 : 1200;
  const h = mobile ? 430 : 250;
  const x0 = mobile ? 24 : 32;
  const stars = data.repos.reduce((s, r) => s + Number(r.stargazers_count || 0), 0);
  const metrics = [
    ['PUBLIC REPOS', fmt(data.user.public_repos), true],
    ['FOLLOWERS', fmt(data.user.followers), false],
    ['STARS EARNED', fmt(stars), false],
    ['CONTRIBUTIONS (1Y)', fmt(data.calendar.total), false]
  ];
  let body = headerBar(x0, w, '04', 'GITHUB TELEMETRY', `SYNCED ${ts(data.now)}`);
  metrics.forEach(([label, val, highlight], i) => {
    const cw = mobile ? 248 : 272;
    const ch = 148;
    const x = x0 + (mobile ? (i % 2) * 264 : i * 288);
    const y = mobile ? 70 + Math.floor(i / 2) * 164 : 72;
    const fill = highlight ? T.accent : T.card;
    const stroke = highlight ? T.accent : T.border;
    const lc = highlight ? '#0B0B0C' : T.muted;
    const vc = highlight ? '#0B0B0C' : T.ink;
    body += `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" rx="14" fill="${fill}" stroke="${stroke}" stroke-width="1.2"/>`;
    body += `<text x="${x + 22}" y="${y + 34}" fill="${lc}" font-family="${T.mono}" font-size="11.5" font-weight="700" letter-spacing="1">${label}</text>`;
    body += `<text x="${x + 22}" y="${y + 114}" fill="${vc}" font-family="${T.sans}" font-size="54" font-weight="900" letter-spacing="-2">${val}</text>`;
  });
  return wrapSvg(w, h, 'GitHub Telemetry', body);
}

export function languagesSvg(data, mobile = false) {
  const rows = languageShares(data.languages);
  const w = mobile ? 560 : 1200;
  const h = mobile ? 440 : 290;
  const x0 = mobile ? 24 : 32;
  let body = headerBar(x0, w, '05', 'CODEBASE DISTRIBUTION', 'BY PUBLIC SOURCE BYTES');
  if (!rows.length) {
    body += `<text x="${x0}" y="120" fill="${T.muted}" font-family="${T.mono}" font-size="14">No public language data yet.</text>`;
    return wrapSvg(w, 180, 'Languages', body);
  }

  // Stacked Horizontal Swiss Bar
  const barX = x0, barY = 74, barW = w - x0 * 2, barH = 22;
  let curX = barX;
  body += `<rect x="${barX}" y="${barY}" width="${barW}" height="${barH}" rx="6" fill="${T.card2}"/>`;
  rows.forEach((row) => {
    const segW = Math.max(4, (row.percent / 100) * barW - 3);
    body += `<rect x="${curX.toFixed(1)}" y="${barY}" width="${segW.toFixed(1)}" height="${barH}" rx="4" fill="${row.color}"/>`;
    curX += (row.percent / 100) * barW;
  });

  // Language Cards Grid
  const cols = mobile ? 2 : 3;
  const gap = 16;
  const cw = (w - x0 * 2 - gap * (cols - 1)) / cols;
  rows.forEach((row, i) => {
    const col = i % cols, r = Math.floor(i / cols);
    const x = x0 + col * (cw + gap);
    const y = 114 + r * 82;
    body += `<rect x="${x.toFixed(1)}" y="${y}" width="${cw.toFixed(1)}" height="68" rx="10" fill="${T.card}" stroke="${T.border}"/>`;
    body += `<rect x="${(x + 16).toFixed(1)}" y="${y + 22}" width="8" height="24" rx="3" fill="${row.color}"/>`;
    body += `<text x="${(x + 36).toFixed(1)}" y="${y + 39}" fill="${T.ink}" font-family="${T.sans}" font-size="16" font-weight="700">${esc(row.name)}</text>`;
    body += `<text x="${(x + cw - 18).toFixed(1)}" y="${y + 40}" fill="${T.muted}" font-family="${T.mono}" font-size="15" font-weight="700" text-anchor="end">${row.percent.toFixed(1)}%</text>`;
  });
  return wrapSvg(w, h, 'Most Used Languages', body);
}

export function contributionsSvg(data, mobile = false) {
  const { days, total, current, longest } = data.calendar;
  const w = mobile ? 560 : 1200;
  const h = mobile ? 430 : 340;
  const x0 = mobile ? 24 : 32;
  let body = headerBar(x0, w, '06', 'CONTRIBUTION CONSISTENCY', `${days[0].date} -> ${days.at(-1).date}`);

  // 3 Streak Metric Pills
  const stats = [
    ['YEAR TOTAL', fmt(total), T.ink],
    ['CURRENT STREAK', `${current}d`, T.accent],
    ['BEST STREAK', `${longest}d`, '#22C55E']
  ];
  const sw = (w - x0 * 2 - 32) / 3;
  stats.forEach(([label, val, col], i) => {
    const x = x0 + i * (sw + 16);
    body += `<rect x="${x.toFixed(1)}" y="68" width="${sw.toFixed(1)}" height="74" rx="12" fill="${T.card}" stroke="${T.border}"/>`;
    body += `<text x="${(x + 18).toFixed(1)}" y="94" fill="${T.muted}" font-family="${T.mono}" font-size="10.5" font-weight="700">${label}</text>`;
    body += `<text x="${(x + 18).toFixed(1)}" y="128" fill="${col}" font-family="${T.sans}" font-size="28" font-weight="900">${val}</text>`;
  });

  // Heatmap Container
  const mapY = 158, mapH = mobile ? 248 : 164;
  body += `<rect x="${x0}" y="${mapY}" width="${w - x0 * 2}" height="${mapH}" rx="14" fill="${T.card}" stroke="${T.border}"/>`;

  const sliceDays = mobile ? days.slice(-112) : days;
  const first = dateMs(sliceDays[0].date);
  const start = first - new Date(first).getUTCDay() * DAY;
  const max = Math.max(1, ...sliceDays.map((d) => d.count));
  const step = mobile ? 30 : 20.5;
  const size = mobile ? 24 : 15.5;
  const gx = x0 + (mobile ? 18 : 26);
  const gy = mapY + (mobile ? 22 : 14);

  sliceDays.forEach((d) => {
    const time = dateMs(d.date);
    const offset = Math.round((time - start) / DAY);
    const col = Math.floor(offset / 7);
    const row = offset % 7;
    const lvl = d.count === 0 ? 0 : Math.min(4, Math.max(1, Math.ceil((d.count / max) * 4)));
    body += `<rect x="${(gx + col * step).toFixed(1)}" y="${(gy + row * step).toFixed(1)}" width="${size}" height="${size}" rx="3" fill="${ACTIVE.heat[lvl]}"><title>${d.date}: ${d.count}</title></rect>`;
  });

  return wrapSvg(w, h, 'Contribution Consistency', body);
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
    } catch { /* fallback below */ }
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
    'github-overview.svg': overviewSvg(data, false),
    'github-overview-mobile.svg': overviewSvg(data, true),
    'languages.svg': languagesSvg(data, false),
    'languages-mobile.svg': languagesSvg(data, true),
    'contributions.svg': contributionsSvg(data, false),
    'contributions-mobile.svg': contributionsSvg(data, true)
  };
  await mkdir(ASSETS, { recursive: true });
  for (const [name, content] of Object.entries(cards)) {
    await writeFile(new URL(name + '.tmp', ASSETS), content, 'utf8');
    await rename(new URL(name + '.tmp', ASSETS), new URL(name, ASSETS));
  }
  console.log(`Updated ${Object.keys(cards).length} Swiss-Editorial Bento cards for ${userName}`);
}
