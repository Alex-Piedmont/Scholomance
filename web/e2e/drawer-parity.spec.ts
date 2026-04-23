import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { SECTION_SELECTORS, type SectionResult } from './fixtures/section-selectors'
import { type AliveStatus } from './fixtures/crash-detection'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

type RecordResult = {
  university: string
  uuid: string
  tech_id: string
  title: string
  status: 'pass' | 'fail' | 'crash' | 'unreachable'
  surface_alive: AliveStatus
  sections: SectionResult[]
}

const SAMPLES_PATH =
  process.env.PLAYWRIGHT_SAMPLES ||
  path.resolve(__dirname, '../../docs/qa/samples-latest.json')
const COVERAGE_PATH =
  process.env.PLAYWRIGHT_COVERAGE ||
  path.resolve(__dirname, '../../docs/qa/db-coverage-latest.json')
const RESULTS_PATH = path.resolve(__dirname, '../../docs/qa/playwright-drawer-latest.json')

const samples = JSON.parse(fs.readFileSync(SAMPLES_PATH, 'utf-8')) as {
  universities: Array<{
    code: string
    name: string
    sampled: Array<{ uuid: string; tech_id: string; first_seen: string | null; stratum: string }>
  }>
}

const coverage = JSON.parse(fs.readFileSync(COVERAGE_PATH, 'utf-8')) as {
  universities: Record<string, { per_record: Record<string, Record<string, string>> }>
}

// Accumulate results per record across the parallel workers
const collected: RecordResult[] = []

function expectedDrawerSections(universityCode: string, uuid: string): string[] {
  const row = coverage.universities[universityCode]?.per_record[uuid] || {}
  // Drawer surfaces every section that has data in the DB. Subtitle is dropped
  // because it has no canonical heading selector (handled via data-section).
  return Object.entries(row)
    .filter(([, status]) => status === 'has_data')
    .map(([sid]) => sid)
}

for (const uni of samples.universities) {
  for (const sample of uni.sampled) {
    test(`@uni-${uni.code} ${sample.tech_id} (${sample.uuid.slice(0, 8)})`, async ({ page }) => {
        const expected = expectedDrawerSections(uni.code, sample.uuid)

        // Prefer AU-8 ?openTech= deep link (deterministic across all samples).
        // Fall back to click-on-card for records that happen to be on the
        // landing page (back-compat; not required after AU-8).
        await page.goto(`/?openTech=${sample.uuid}`)

        const drawer = page.locator('.drawer.is-open')
        await expect(drawer).toBeVisible({ timeout: 10_000 })

        const titleLocator = drawer.locator('.drawer__title')
        let title = ''
        let aliveStatus: AliveStatus = 'crash'
        try {
          await titleLocator.waitFor({ state: 'visible', timeout: 8_000 })
          title = (await titleLocator.innerText().catch(() => '')) || ''
          if (title.trim().length > 0) aliveStatus = 'alive'
        } catch {
          /* leaves aliveStatus = 'crash' */
        }
        const alive = { status: aliveStatus }

        if (alive.status !== 'alive') {
          collected.push({
            university: uni.code,
            uuid: sample.uuid,
            tech_id: sample.tech_id,
            title,
            status: 'crash',
            surface_alive: alive.status,
            sections: expected.map((s) => ({ sectionId: s, status: 'missing' })),
          })
          expect.soft(alive.status, `drawer CRASH for ${sample.uuid}`).toBe('alive')
          return
        }

        const sections: SectionResult[] = []
        let anyMissing = false
        for (const sid of expected) {
          const selector = SECTION_SELECTORS[sid]
          if (!selector) {
            sections.push({ sectionId: sid, status: 'missing' })
            anyMissing = true
            continue
          }
          const loc = selector(drawer)
          try {
            await expect(loc.first()).toBeVisible({ timeout: 2_000 })
            sections.push({ sectionId: sid, status: 'pass' })
          } catch {
            sections.push({ sectionId: sid, status: 'missing' })
            anyMissing = true
          }
        }

        collected.push({
          university: uni.code,
          uuid: sample.uuid,
          tech_id: sample.tech_id,
          title,
          status: anyMissing ? 'fail' : 'pass',
          surface_alive: 'alive',
          sections,
        })
        if (anyMissing) {
          const missed = sections.filter((s) => s.status === 'missing').map((s) => s.sectionId)
          expect
            .soft(missed, `Drawer missing sections for ${sample.uuid}: ${missed.join(', ')}`)
            .toEqual([])
        }
      })
  }
}

test.afterAll(async () => {
  // Each worker writes its own partial; merge under a worker-suffixed filename
  // to avoid races. A separate merge happens in AU-9.
  const workerId = process.env.TEST_WORKER_INDEX || '0'
  const workerPath = RESULTS_PATH.replace(/\.json$/, `.worker-${workerId}.json`)
  const payload = {
    generated_at: new Date().toISOString(),
    surface: 'drawer',
    worker: workerId,
    records: collected,
  }
  fs.mkdirSync(path.dirname(workerPath), { recursive: true })
  fs.writeFileSync(workerPath, JSON.stringify(payload, null, 2))
})
