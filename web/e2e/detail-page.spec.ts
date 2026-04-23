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
  status: 'pass' | 'fail' | 'crash'
  surface_alive: AliveStatus
  sections: SectionResult[]
}

const SAMPLES_PATH =
  process.env.PLAYWRIGHT_SAMPLES ||
  path.resolve(__dirname, '../../docs/qa/samples-latest.json')
const COVERAGE_PATH =
  process.env.PLAYWRIGHT_COVERAGE ||
  path.resolve(__dirname, '../../docs/qa/db-coverage-latest.json')
const RESULTS_PATH = path.resolve(__dirname, '../../docs/qa/playwright-detail-latest.json')

const samples = JSON.parse(fs.readFileSync(SAMPLES_PATH, 'utf-8')) as {
  universities: Array<{
    code: string
    sampled: Array<{ uuid: string; tech_id: string }>
  }>
}
const coverage = JSON.parse(fs.readFileSync(COVERAGE_PATH, 'utf-8')) as {
  universities: Record<string, { per_record: Record<string, Record<string, string>> }>
}

const collected: RecordResult[] = []

function expectedSections(universityCode: string, uuid: string): string[] {
  const row = coverage.universities[universityCode]?.per_record[uuid] || {}
  return Object.entries(row)
    .filter(([, status]) => status === 'has_data')
    .map(([sid]) => sid)
}

for (const uni of samples.universities) {
  for (const sample of uni.sampled) {
    test(`@uni-${uni.code} detail ${sample.tech_id} (${sample.uuid.slice(0, 8)})`, async ({
      page,
    }) => {
      const expected = expectedSections(uni.code, sample.uuid)
      await page.goto(`/technology/${sample.uuid}`)

      // "Alive" = h1 with non-empty text rendered within timeout. This
      // distinguishes a blank/errored render from a "sections missing" render.
      let titleText = ''
      let aliveStatus: AliveStatus = 'crash'
      try {
        await page.locator('h1').first().waitFor({ state: 'visible', timeout: 10_000 })
        titleText = (await page.locator('h1').first().innerText().catch(() => '')) || ''
        if (titleText.trim().length > 0) aliveStatus = 'alive'
      } catch {
        /* leaves aliveStatus = 'crash' */
      }

      if (aliveStatus !== 'alive') {
        collected.push({
          university: uni.code,
          uuid: sample.uuid,
          tech_id: sample.tech_id,
          title: '',
          status: 'crash',
          surface_alive: aliveStatus,
          sections: expected.map((s) => ({ sectionId: s, status: 'missing' })),
        })
        expect.soft(aliveStatus, `DetailPage CRASH for ${sample.uuid}`).toBe('alive')
        return
      }

      const main = page.locator('main, body')

      const sections: SectionResult[] = []
      let anyMissing = false
      for (const sid of expected) {
        const selector = SECTION_SELECTORS[sid]
        if (!selector) {
          sections.push({ sectionId: sid, status: 'missing' })
          anyMissing = true
          continue
        }
        const loc = selector(main)
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
        title: titleText,
        status: anyMissing ? 'fail' : 'pass',
        surface_alive: 'alive',
        sections,
      })
      // Flag missing sections via soft expect so the Playwright HTML report
      // mirrors the JSON's miss count, without short-circuiting on first miss.
      if (anyMissing) {
        const missed = sections.filter((s) => s.status === 'missing').map((s) => s.sectionId)
        expect
          .soft(missed, `DetailPage missing sections for ${sample.uuid}: ${missed.join(', ')}`)
          .toEqual([])
      }
    })
  }
}

test.afterAll(async () => {
  const workerId = process.env.TEST_WORKER_INDEX || '0'
  const workerPath = RESULTS_PATH.replace(/\.json$/, `.worker-${workerId}.json`)
  const payload = {
    generated_at: new Date().toISOString(),
    surface: 'detail',
    worker: workerId,
    records: collected,
  }
  fs.mkdirSync(path.dirname(workerPath), { recursive: true })
  fs.writeFileSync(workerPath, JSON.stringify(payload, null, 2))
})
