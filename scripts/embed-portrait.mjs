// Run: node scripts/embed-portrait.mjs
// Place your photo at assets/portrait.jpg (or assets/portrait.png) first!
import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';

const jpgPath = new URL('../assets/portrait.jpg', import.meta.url);
const pngPath = new URL('../assets/portrait.png', import.meta.url);

let imgPath, mime;
if (existsSync(jpgPath)) { imgPath = jpgPath; mime = 'image/jpeg'; }
else if (existsSync(pngPath)) { imgPath = pngPath; mime = 'image/png'; }
else {
  console.error('❌ Please place your photo at assets/portrait.jpg or assets/portrait.png first.');
  process.exit(1);
}

const b64 = (await readFile(imgPath)).toString('base64');
const dataUri = `data:${mime};base64,${b64}`;

const targets = [
  { file: '../assets/about-bento.svg', tag: `<image href="${dataUri}" x="44" y="92" width="256" height="278" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>` },
  { file: '../assets/about-bento-mobile.svg', tag: `<image href="${dataUri}" x="40" y="88" width="128" height="148" preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClipMob)"/>` }
];

for (const { file, tag } of targets) {
  const url = new URL(file, import.meta.url);
  let svg = await readFile(url, 'utf8');
  svg = svg.replace(/<!-- PORTRAIT_SLOT_START -->[\s\S]*?<!-- PORTRAIT_SLOT_END -->/, `<!-- PORTRAIT_SLOT_START -->\n  ${tag}\n  <!-- PORTRAIT_SLOT_END -->`);
  await writeFile(url, svg, 'utf8');
  console.log(`✅ Embedded portrait into ${file}`);
}
