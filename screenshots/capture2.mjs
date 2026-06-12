import { chromium } from 'playwright';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;
const BASE = 'http://localhost:3002';
const API  = 'http://localhost:8001';

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

// Helper: dismiss the Next.js dev toast if present
const dismissToast = async () => {
  try {
    const close = page.locator('button:has-text("×"), [aria-label="Close"], button.nextjs-toast-close');
    if (await close.count()) await close.first().click();
    // Also try clicking the × on the issue badge
    const badge = page.locator('text=1 Issue').locator('..');
    if (await badge.count()) {
      const closeBtn = badge.locator('button, [role="button"]');
      if (await closeBtn.count()) await closeBtn.first().click();
    }
  } catch (_) {}
};

const shot = async (name) => {
  await dismissToast();
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log(`  ✓ ${name}.png`);
};

const jobs = await fetch(`${API}/admin/jobs`).then(r => r.json());
const backendJob = jobs.find(j => j.title?.includes('Backend'));
const mlJob      = jobs.find(j => j.title?.includes('ML'));
const fsJob      = jobs.find(j => j.title?.includes('Full') || j.company?.includes('Slate'));

// ── 01  Clean idle state ───────────────────────────────────────────────────
console.log('01 clean idle state');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);
await page.evaluate(() => {
  // Clear any filled textarea
  const ta = document.querySelector('textarea');
  if (ta) { ta.value = ''; ta.dispatchEvent(new Event('input', { bubbles: true })); }
});
await page.waitForTimeout(500);
await shot('01-idle-clean');

// ── 02  Generating state (use preview tool — can't wait for real gen) ──────
// We'll just use the already-captured one from the preview screenshots above

// ── 03  Backend result — full analysis view ───────────────────────────────
if (backendJob) {
  console.log(`03 backend result`);
  await page.goto(`${BASE}/jobs/${backendJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shot('03-backend-analysis');

  // Scroll down to show emphasized pills
  await page.evaluate(() => window.scrollTo(0, 600));
  await page.waitForTimeout(500);
  await shot('03b-backend-pills-pdf');
}

// ── 04  ML result ─────────────────────────────────────────────────────────
if (mlJob) {
  console.log(`04 ML result`);
  await page.goto(`${BASE}/jobs/${mlJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shot('04-ml-analysis');
}

// ── 05  Full-stack result ─────────────────────────────────────────────────
if (fsJob) {
  console.log(`05 full-stack result`);
  await page.goto(`${BASE}/jobs/${fsJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await shot('05-fullstack-analysis');
}

// ── 06  Profile — projects section ────────────────────────────────────────
console.log('06 profile');
await page.goto(`${BASE}/profile`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
// Scroll to show projects (first section)
await page.evaluate(() => window.scrollTo(0, 0));
await shot('06-profile-projects');
// Scroll to experience
await page.evaluate(() => window.scrollTo(0, 900));
await page.waitForTimeout(400);
await shot('06b-profile-experience');

// ── 07  Home idle with insights + recent list ─────────────────────────────
console.log('07 home with insights');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await page.evaluate(() => {
  const ta = document.querySelector('textarea');
  if (ta) { ta.value = ''; ta.dispatchEvent(new Event('input', { bubbles: true })); }
});
await page.waitForTimeout(400);
// Scroll past textarea to show insights + recent
await page.evaluate(() => window.scrollTo(0, 350));
await page.waitForTimeout(400);
await shot('07-insights-and-recent');

// ── 08  History drawer ────────────────────────────────────────────────────
console.log('08 history drawer');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(800);
// Click the history icon (list icon) in the top right navbar
await page.evaluate(() => {
  // Find the history link by its SVG or title attribute
  const links = [...document.querySelectorAll('nav a, nav button')];
  const hist = links.find(l => l.title === 'History' || l.getAttribute('href') === '/applications');
  if (hist) hist.click();
});
await page.waitForTimeout(900);
await shot('08-history-drawer');

// ── 09  Side-by-side: backend pills vs ML pills (two separate shots) ───────
if (backendJob && mlJob) {
  console.log('09 project selection comparison');

  // Backend pills
  await page.goto(`${BASE}/jobs/${backendJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  // Find and scroll to the emphasized bar
  await page.evaluate(() => {
    const allText = [...document.querySelectorAll('*')];
    const emp = allText.find(e => e.childNodes.length === 1 &&
      e.textContent?.trim() === 'EMPHASIZED');
    if (emp) emp.scrollIntoView({ behavior: 'instant', block: 'center' });
    else window.scrollTo(0, 580);
  });
  await page.waitForTimeout(400);
  await shot('09-backend-emphasized');

  // ML pills
  await page.goto(`${BASE}/jobs/${mlJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  await page.evaluate(() => {
    const allText = [...document.querySelectorAll('*')];
    const emp = allText.find(e => e.childNodes.length === 1 &&
      e.textContent?.trim() === 'EMPHASIZED');
    if (emp) emp.scrollIntoView({ behavior: 'instant', block: 'center' });
    else window.scrollTo(0, 580);
  });
  await page.waitForTimeout(400);
  await shot('10-ml-emphasized');
}

await browser.close();
console.log('\n✓ Done. Final screenshots in screenshots/');
