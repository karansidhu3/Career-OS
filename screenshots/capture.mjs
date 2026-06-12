import { chromium } from 'playwright';
import { existsSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;
if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true });

const BASE = 'http://localhost:3002';
const API  = 'http://localhost:8001';

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

const shot = async (name) => {
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log(`  ✓ ${name}.png`);
};

// Fetch job list once
const jobs = await fetch(`${API}/admin/jobs`).then(r => r.json());
const backendJob = jobs.find(j => j.title?.includes('Backend'));
const mlJob      = jobs.find(j => j.title?.includes('ML'));
const fsJob      = jobs.find(j => j.title?.includes('Full') || j.title?.includes('Product') || j.company?.includes('Slate'));
console.log('Jobs found:', jobs.map(j => `${j.id}:${j.title}`).join(', '));

// ── 01  Idle state ─────────────────────────────────────────────────────────
console.log('\n01 idle state');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await shot('01-idle');

// ── 02  JD filled (backend JD, don't submit) ──────────────────────────────
console.log('02 jd filled');
await page.fill('textarea', `# Backend Systems Engineer — Meridian Payments

Meridian's payments platform processes 4M+ transactions per day across 60 currencies. Looking for a backend engineer to work on rate limiting, distributed tracing, latency analysis, and observability tooling.

Requirements: distributed tracing (OpenTelemetry, Jaeger), tail-based vs head-based sampling, Go, Redis, Kubernetes, high-throughput systems experience.

Stack: Go, Redis, Kafka, PostgreSQL, Kubernetes, Prometheus, Jaeger, Grafana`);
await page.waitForTimeout(400);
await shot('02-jd-filled');

// ── 03  Backend job result (archive page) ──────────────────────────────────
if (backendJob) {
  console.log(`03 backend result (job ${backendJob.id})`);
  await page.goto(`${BASE}/jobs/${backendJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot('03-result-backend-top');

  // Scroll to show emphasized pills + PDF area
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(400);
  await shot('03b-result-backend-analysis');
}

// ── 04  ML job result ─────────────────────────────────────────────────────
if (mlJob) {
  console.log(`04 ml result (job ${mlJob.id})`);
  await page.goto(`${BASE}/jobs/${mlJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot('04-result-ml');
}

// ── 05  Full-stack result ──────────────────────────────────────────────────
if (fsJob) {
  console.log(`05 fullstack result (job ${fsJob.id})`);
  await page.goto(`${BASE}/jobs/${fsJob.id}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot('05-result-fullstack');
}

// ── 06  Profile page ──────────────────────────────────────────────────────
console.log('06 profile page');
await page.goto(`${BASE}/profile`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1000);
await shot('06-profile-top');
await page.evaluate(() => window.scrollTo(0, 600));
await page.waitForTimeout(400);
await shot('06-profile-projects');

// ── 07  Home idle with recent list (all 3 applications) ───────────────────
console.log('07 home with recent list');
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await shot('07-idle-with-history');

// ── 08  History drawer open ───────────────────────────────────────────────
console.log('08 history drawer');
// Click the history (list) icon in the navbar
const navLinks = page.locator('nav a, nav button');
const count = await navLinks.count();
for (let i = 0; i < count; i++) {
  const el = navLinks.nth(i);
  const title = await el.getAttribute('title');
  if (title === 'History' || title === 'Log') {
    await el.click();
    break;
  }
}
await page.waitForTimeout(800);
await shot('08-history-drawer');

// ── 09  Backend result on home page (re-enter from recent) ────────────────
if (backendJob) {
  console.log('09 full result view on homepage');
  // Navigate to home and click the backend application in recent list
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  const recentLink = page.locator(`text=Meridian Payments`).first();
  if (await recentLink.count()) {
    await recentLink.click();
    await page.waitForTimeout(800);
    await shot('09-home-result-state');
    // Scroll to project pills
    await page.evaluate(() => {
      const el = document.querySelector('[class*="Emphasized"], [class*="emphasized"]') ||
                 Array.from(document.querySelectorAll('*')).find(e => e.textContent?.trim() === 'EMPHASIZED');
      if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
    });
    await page.waitForTimeout(400);
    await shot('09b-project-pills');
  }
}

await browser.close();
console.log('\n✓ All screenshots saved to screenshots/');
