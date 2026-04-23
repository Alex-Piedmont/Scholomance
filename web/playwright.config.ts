import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for Migration-QA e2e suite.
 *
 * baseURL resolves via env:
 *   - unset         -> http://localhost:5173 (local dev server, auto-started)
 *   - set to URL    -> that URL (Vercel prod or preview); webServer is skipped
 *
 * Point dev against production API by writing `web/.env.local` (see
 * `web/.env.local.example`). The dev server picks it up automatically.
 */

const baseURL = process.env.PLAYWRIGHT_BASE_URL?.replace(/\/$/, '') || 'http://localhost:5173'
const usingLocal = !process.env.PLAYWRIGHT_BASE_URL

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : '50%',
  reporter: [['html', { open: 'never' }], ['list']],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: usingLocal
    ? {
        command: 'npm run dev',
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      }
    : undefined,
})
