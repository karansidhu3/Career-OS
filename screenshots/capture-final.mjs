import { chromium } from 'playwright';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const BASE = 'http://localhost:3003';
const API  = 'http://localhost:8001';

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

const shot = async (name) => {
  await page.screenshot({ path: `${__dirname}/${name}.png` });
  console.log(`  ✓ ${name}.png`);
};

const jobs = await fetch(`${API}/admin/jobs`).then(r => r.json());
const backendJob = jobs.find(j => j.title?.includes('Backend'));
const mlJob      = jobs.find(j => j.title?.includes('ML'));
const fsJob      = jobs.find(j => j.title?.includes('Full') || j.company?.includes('Slate'));

// ── 01  Idle state ─────────────────────────────────────────────────────────
console.log('01 idle');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);
await shot('FINAL-01-idle');

// ── 02  Generating state — need to submit and catch mid-flight ──────────────
console.log('02 generating state (using pre-saved B-generating.png)');
// Already have a clean one from capture-pills.mjs — skip re-generating

// ── 03  Backend analysis ────────────────────────────────────────────────────
if (backendJob) {
  console.log(`03 backend (job ${backendJob.id})`);
  await page.goto(`${BASE}/jobs/${backendJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shot('FINAL-03-backend-analysis');
}

// ── 04  ML analysis ─────────────────────────────────────────────────────────
if (mlJob) {
  console.log(`04 ML (job ${mlJob.id})`);
  await page.goto(`${BASE}/jobs/${mlJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shot('FINAL-04-ml-analysis');
}

// ── 05  Full-stack analysis ─────────────────────────────────────────────────
if (fsJob) {
  console.log(`05 full-stack (job ${fsJob.id})`);
  await page.goto(`${BASE}/jobs/${fsJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shot('FINAL-05-fullstack-analysis');
}

// ── 06  Profile page ─────────────────────────────────────────────────────────
console.log('06 profile');
await page.goto(`${BASE}/profile`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await shot('FINAL-06-profile');
await page.evaluate(() => window.scrollTo(0, 700));
await page.waitForTimeout(400);
await shot('FINAL-06b-profile-experience');

// ── 07  Home with insights + recent ──────────────────────────────────────────
console.log('07 home insights');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await page.evaluate(() => window.scrollTo(0, 330));
await page.waitForTimeout(400);
await shot('FINAL-07-insights-recent');

// ── 08  History drawer ────────────────────────────────────────────────────────
console.log('08 history drawer');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
// Click the history button (list icon in navbar)
const histBtn = page.locator('button[title="History"]');
if (await histBtn.count()) {
  await histBtn.click();
} else {
  await page.locator('nav').getByRole('button').first().click();
}
await page.waitForTimeout(900);
await shot('FINAL-08-history-drawer');

// ── 09  Live result with emphasized pills (re-run quick generation) ───────────
console.log('09 live result with pills — submitting new generation...');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(600);

await page.fill('textarea', `ML Engineer — LLM Evaluation — Boreal AI

We evaluate instruction-following, factuality, and constraint adherence in LLMs. Looking for Python/PyTorch/Hugging Face background, annotation pipeline experience, inter-annotator agreement, NLP fine-tuning.

Stack: Python, PyTorch, Hugging Face Transformers, FastAPI, PostgreSQL`);

await page.keyboard.press('Meta+Enter');
await page.waitForTimeout(1500);
await shot('FINAL-02-generating');

// Poll for result
console.log('  waiting...');
for (let i = 0; i < 30; i++) {
  const text = await page.evaluate(() => document.body.innerText);
  if (text.includes('EMPHASIZED') || text.includes('GOOD FIT')) break;
  await page.waitForTimeout(3000);
  process.stdout.write('.');
}
await page.waitForTimeout(600);
await page.evaluate(() => window.scrollTo(0, 0));
await shot('FINAL-09-result-with-pills');

// Zoom into just the pills area
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
await shot('FINAL-09b-pills-zoomed');

await browser.close();
console.log('\n✓ Final screenshots done');
