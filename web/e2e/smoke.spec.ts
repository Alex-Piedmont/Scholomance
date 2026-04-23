import { test, expect } from '@playwright/test'

test('discovery landing page renders', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText(/Phronesis/i).first()).toBeVisible({ timeout: 15_000 })
})
