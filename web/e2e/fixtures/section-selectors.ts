import type { Locator } from '@playwright/test'

/**
 * Section-id -> DOM locator function for Migration-QA assertions.
 *
 * Each selector takes the surface root (drawer or main/DetailPage) and returns
 * a Locator that is expected to be visible when the section has data. Scope
 * lives in the caller; selectors here are root-relative so either surface can
 * reuse them.
 *
 * Section IDs mirror `src/qa/section_catalog.py :: SECTION_IDS`. Kept in sync
 * by convention; drift is caught by catalog-only or selector-only entries.
 */

export type SectionSelector = (scope: Locator) => Locator

// Heading-based selector: case-insensitive exact-ish match. AU-7's shared
// section components render their own headings so both surfaces resolve.
const byHeading = (label: string): SectionSelector =>
  (scope) => scope.getByRole('heading', { name: new RegExp(`^\\s*${escapeRegex(label)}\\s*$`, 'i') })

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export const SECTION_SELECTORS: Record<string, SectionSelector> = {
  // Content
  subtitle: (scope) => scope.locator('[data-section="subtitle"]'),
  summary: byHeading('Summary'),
  abstract: byHeading('Abstract'),
  overview: byHeading('Overview'),
  description: byHeading('Description'),
  technical_problem: byHeading('Technical Problem'),
  solution: byHeading('Solution'),
  background: byHeading('Background'),
  full_description: byHeading('Full Description'),
  benefits: byHeading('Benefits'),
  market_opportunity: byHeading('Market Opportunity'),
  development_stage: byHeading('Development Stage'),
  trl: byHeading('Technology Readiness Level'),
  key_points: byHeading('Key Points'),
  applications: byHeading('Applications'),
  advantages: byHeading('Advantages'),
  technology_validation: byHeading('Technology Validation'),
  publications: byHeading('Publications'),
  ip_status: byHeading('IP Status'),

  // Side panel
  researchers: byHeading('Researchers'),
  inventors: byHeading('Inventors'),
  departments: byHeading('Departments'),
  contacts: byHeading(/Contact|Contacts/.source),
  classification: byHeading('Classification'),
  keywords: byHeading('Keywords'),
  tags: byHeading('Tags'),
  documents: byHeading('Documents'),
  licensing_contact: byHeading('Licensing Contact'),
  related_portfolio: byHeading('Related Technologies'),
  source_link: byHeading(/Source|View on university website/.source),
}

export type SectionStatus = 'pass' | 'missing'

export interface SectionResult {
  sectionId: string
  status: SectionStatus
}
