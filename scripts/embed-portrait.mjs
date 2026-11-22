// Run: node scripts/embed-portrait.mjs
// Save your photo as assets/portrait.jpg (or assets/portrait.png) first!
import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';

const jpg = new URL('../assets/portrait.jpg', import.meta.url);
const png = new URL('../assets/portrait.png', import.meta.url);
let p, mime;
if (existsSync(jpg)) { p = jpg; mime = 'image/jpeg'; }
else if (existsSync(png)) { p = png; mime = 'image/png'; }
else { console.error('❌ Put your photo at assets/portrait.jpg or assets/portrait.png first.'); process.exit(1); }

const b64 = (await readFile(p)).toString('base64');
const svgUrl = new URL('../assets/01-hero-portrait.svg', import.meta.url);
let svg = await readFile(svgUrl, 'utf8');
const imgTag = `<image href="data:${mime};base64,${b64}" x="598" y="12" width="390" height="336" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>`;
svg = svg.replace(/<!-- PORTRAIT_SLOT_START -->[\s\S]*?<!-- PORTRAIT_SLOT_END -->/, `<!-- PORTRAIT_SLOT_START -->\n  ${imgTag}\n  <!-- PORTRAIT_SLOT_END -->`);
await writeFile(svgUrl, svg, 'utf8');
console.log('✅ Embedded portrait into assets/01-hero-portrait.svg');
