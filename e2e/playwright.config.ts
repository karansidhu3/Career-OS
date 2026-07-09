import { defineConfig, devices } from '@playwright/test'
import { config as dotenvConfig } from 'dotenv'
import { join } from 'path'

// Load Clerk keys + test email into the Playwright process — the Next.js dev
// server reads these from the same file for itself, but the Playwright process
// (global-setup, test files) needs them separately.
dotenvConfig({ path: join(__dirname, '../frontend/.env.local') })

export default defineConfig({
  testDir: '.',
  globalSetup: require.resolve('./global-setup'),
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'list',

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Start the Next.js dev server automatically when not in CI.
  // In CI the server is started separately so we can layer in the backend.
  webServer: process.env.CI ? undefined : {
    command: 'cd ../frontend && npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 30_000,
  },
})
