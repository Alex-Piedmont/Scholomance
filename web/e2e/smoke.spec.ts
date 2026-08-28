import { test, expect } from '@playwright/test'

test('discovery landing page renders', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText(/Phronesis/i).first()).toBeVisible({ timeout: 15_000 })
})

test('coverage review page is a first-class route', async ({ page }) => {
  await page.goto('/coverage')
  await expect(page.getByRole('heading', { name: /Weekly coverage finds/i })).toBeVisible({
    timeout: 15_000,
  })
  await expect(page.getByText(/not.*TTO listings/i).first()).toBeVisible()
})
