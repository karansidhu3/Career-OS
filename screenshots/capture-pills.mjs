import { chromium } from 'playwright';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE = 'http://localhost:3002';

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

const shot = async (name) => {
  await page.screenshot({ path: `${__dirname}/${name}.png` });
  console.log(`  ✓ ${name}.png`);
};

console.log('Loading home page...');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(800);

// Fill a concise JD
await page.fill('textarea', `Software Engineer (Full-Stack) — Slate

Real-time collaborative workspace. We need someone with CRDT/WebSocket experience, TypeScript and React, Node.js backend, offline-first design with IndexedDB sync.

Bonus: Yjs/Automerge, presence systems, canvas rendering.
Stack: TypeScript, React, Node.js, WebSockets, PostgreSQL, Redis`);

// Screenshot with JD filled — shows the clean input state
await page.waitForTimeout(300);
await shot('A-jd-filled');

// Submit
await page.keyboard.press('Meta+Enter');
await page.waitForTimeout(1500);

// Screenshot the generating state
await shot('B-generating');

// Wait for result
console.log('Waiting for generation (up to 90s)...');
let done = false;
for (let i = 0; i < 30; i++) {
  const text = await page.evaluate(() => document.body.innerText);
  if (text.includes('EMPHASIZED') || text.includes('GOOD FIT')) { done = true; break; }
  await page.waitForTimeout(3000);
  process.stdout.write('.');
}
if (!done) throw new Error('Generation timed out after 90s');
await page.waitForTimeout(800);

// Screenshot the full result state from top
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(300);
await shot('C-result-top');

// Scroll to show analysis + emphasized pills together
await page.evaluate(() => window.scrollTo(0, 250));
await page.waitForTimeout(300);
await shot('D-analysis-and-pills');

// Find and center on the emphasized pills
await page.evaluate(() => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while (node = walker.nextNode()) {
    if (node.textContent?.trim() === 'EMPHASIZED') {
      node.parentElement?.scrollIntoView({ behavior: 'instant', block: 'center' });
      break;
    }
  }
});
await page.waitForTimeout(400);
await shot('E-pills-centered');

// Scroll down past pills to show the resume section
await page.evaluate(() => window.scrollTo(0, window.scrollY + 200));
await page.waitForTimeout(400);
await shot('F-resume-section');

await browser.close();
console.log('\n✓ Done');
