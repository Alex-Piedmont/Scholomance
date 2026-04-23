import type { Locator, Page } from '@playwright/test'

export type AliveStatus = 'alive' | 'crash' | 'unreachable'

export interface AliveResult {
  status: AliveStatus
  reason?: string
}

/**
 * Assert the surface is alive (title renders) before running per-section
 * assertions. Distinguishes CRASH from MISSING_SECTION: if the title never
 * shows, the whole surface is broken and per-section "missing" would be noise.
 */
export async function assertSurfaceAlive(
  scope: Locator,
  title: string,
  timeoutMs = 10_000,
): Promise<AliveResult> {
  // Title can be long; use substring match on the first 60 chars to avoid
  // false-negatives from newline/whitespace noise in scraped data.
  const needle = title.trim().slice(0, 60)
  try {
    await scope.getByText(new RegExp(escapeRegex(needle).slice(0, 60), 'i')).first().waitFor({
      state: 'visible',
      timeout: timeoutMs,
    })
    return { status: 'alive' }
  } catch (err) {
    return { status: 'crash', reason: (err as Error).message.slice(0, 140) }
  }
}

export async function cardIsOnPage(page: Page, uuid: string): Promise<boolean> {
  const card = page.locator(`[data-uuid="${uuid}"]`)
  try {
    await card.first().waitFor({ state: 'attached', timeout: 3_000 })
    return true
  } catch {
    return false
  }
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
