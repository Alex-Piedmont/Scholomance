import type { TechnologyDetail } from '../../api/types'

export interface ParsedRawData {
  keyPoints: string[] | undefined
  keyPointsText: string | undefined
  inventors: string[] | undefined
  inventorsText: string | undefined
  applications: string[] | undefined
  applicationsText: string | undefined
  advantages: string[] | undefined
  advantagesText: string | undefined
  otherHtml: string | undefined
  abstractText: string | undefined
  benefitHtml: string | undefined
  marketApplicationHtml: string | undefined
  publicationsHtml: string | undefined
  publicationsList: Array<{ text?: string; url?: string }> | undefined
  researchers: Array<{ name?: string; email?: string; expertise?: string }> | undefined
  documents: Array<{ name?: string; url?: string; size?: number }> | undefined
  contactsList: Array<{ name?: string; email?: string; phone?: string }> | undefined
  flintboxTags: string[] | undefined
  flintboxTagsText: string | undefined
  docketNumber: string | undefined
  licensingContact: { name?: string; title?: string; email?: string } | undefined
  pdfUrl: string | undefined
  relatedPortfolio: Array<{ title?: string; url?: string }> | undefined
  background: string | undefined
  shortDescription: string | undefined
  marketOpportunity: string | undefined
  developmentStage: string | undefined
  developmentStageList: string[] | undefined
  ipStatusText: string | undefined
  ipNumber: string | undefined
  ipUrl: string | undefined
  technicalProblem: string | undefined
  solutionText: string | undefined
  fullDescription: string | undefined
  clientDepartments: string[] | undefined
  clientDepartmentsText: string | undefined
  trl: string | undefined
  technologyValidation: string[] | undefined
  technologyValidationText: string | undefined
  ipText: string | undefined
  supportingDocuments: Array<{ name?: string; url?: string }> | undefined
  contactDetail: { name?: string; email?: string } | undefined
  subtitle: string | undefined
  technologyNumber: string | undefined
  publishedOn: string | undefined
  webPublished: string | undefined
}

export function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/[·•]\s*/g, '- ')
    .replace(/\s+/g, ' ')
    .replace(/\r\r/g, '\n\n')
    .replace(/\r/g, '\n')
    .trim()
}

// Dual-output helper: returns both array and string views of a field that may
// arrive as either. Strings split on newline before comma (newline is the
// dominant delimiter in scraped data).
function asArrayOrText(value: unknown): { array?: string[]; text?: string } {
  if (Array.isArray(value)) {
    const strings = value.filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    return strings.length === value.length
      ? { array: strings as string[] }
      : { array: value as unknown as string[] }
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    return { text: value }
  }
  return {}
}

// Parse a field that SHOULD be a string but scrapers sometimes emit as an
// array of strings. Exposes both `<field>` (joined string) and `<field>List`.
function stringOrList(value: unknown): { text?: string; list?: string[] } {
  if (typeof value === 'string' && value.trim().length > 0) {
    return { text: value }
  }
  if (Array.isArray(value)) {
    const strings = value.filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    if (strings.length > 0) {
      return { text: strings.join('\n'), list: strings }
    }
  }
  return {}
}

export function parseRawData(tech: TechnologyDetail): ParsedRawData {
  const r = tech.raw_data as Record<string, unknown> | null

  const keyPoints = asArrayOrText(r?.key_points)
  const inventors = asArrayOrText(r?.inventors)
  const applications = asArrayOrText(r?.applications)
  const advantages = asArrayOrText(r?.advantages)
  const flintboxTags = asArrayOrText(r?.flintbox_tags)
  const clientDepartments = asArrayOrText(r?.client_departments)
  const technologyValidation = asArrayOrText(r?.technology_validation)
  const devStage = stringOrList(r?.development_stage)

  return {
    keyPoints: keyPoints.array,
    keyPointsText: keyPoints.text,
    inventors: inventors.array,
    inventorsText: inventors.text,
    applications: applications.array,
    applicationsText: applications.text,
    advantages: advantages.array,
    advantagesText: advantages.text,
    otherHtml: r?.other as string | undefined,
    abstractText: r?.abstract as string | undefined,
    benefitHtml: r?.benefit as string | undefined,
    marketApplicationHtml: r?.market_application as string | undefined,
    publicationsHtml: typeof r?.publications === 'string' ? r!.publications as string : undefined,
    publicationsList: Array.isArray(r?.publications) ? r!.publications as Array<{ text?: string; url?: string }> : undefined,
    researchers: Array.isArray(r?.researchers)
      ? r!.researchers as Array<{ name?: string; email?: string; expertise?: string }>
      : typeof r?.researchers === 'string'
        ? (r!.researchers as string).split('\n').filter(Boolean).map(name => ({ name: name.trim() }))
        : undefined,
    documents: Array.isArray(r?.documents) ? r!.documents as Array<{ name?: string; url?: string; size?: number }> : undefined,
    contactsList: Array.isArray(r?.contacts) ? r!.contacts as Array<{ name?: string; email?: string; phone?: string }> : undefined,
    flintboxTags: flintboxTags.array,
    flintboxTagsText: flintboxTags.text,
    docketNumber: r?.docket_number as string | undefined,
    licensingContact: r?.licensing_contact as { name?: string; title?: string; email?: string } | undefined,
    pdfUrl: r?.pdf_url as string | undefined,
    relatedPortfolio: r?.related_portfolio as Array<{ title?: string; url?: string }> | undefined,
    background: r?.background as string | undefined,
    shortDescription: r?.short_description as string | undefined,
    marketOpportunity: r?.market_opportunity as string | undefined,
    developmentStage: devStage.text,
    developmentStageList: devStage.list,
    ipStatusText: r?.ip_status as string | undefined,
    ipNumber: r?.ip_number as string | undefined,
    ipUrl: r?.ip_url as string | undefined,
    technicalProblem: r?.technical_problem as string | undefined,
    solutionText: r?.solution as string | undefined,
    fullDescription: r?.full_description as string | undefined,
    clientDepartments: clientDepartments.array,
    clientDepartmentsText: clientDepartments.text,
    trl: r?.trl as string | undefined,
    technologyValidation: technologyValidation.array,
    technologyValidationText: technologyValidation.text,
    ipText: r?.ip_text as string | undefined,
    supportingDocuments: Array.isArray(r?.supporting_documents) ? r!.supporting_documents as Array<{ name?: string; url?: string }> : undefined,
    contactDetail: r?.contact as { name?: string; email?: string } | undefined,
    subtitle: r?.subtitle as string | undefined,
    technologyNumber: r?.technology_number as string | undefined,
    publishedOn: r?.published_on as string | undefined,
    webPublished: r?.web_published as string | undefined,
  }
}
