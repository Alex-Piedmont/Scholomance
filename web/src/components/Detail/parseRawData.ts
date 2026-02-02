import type { TechnologyDetail } from '../../api/types'

export interface ParsedRawData {
  keyPoints: string[] | undefined
  inventors: string[] | undefined
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
  docketNumber: string | undefined
  licensingContact: { name?: string; title?: string; email?: string } | undefined
  pdfUrl: string | undefined
  relatedPortfolio: Array<{ title?: string; url?: string }> | undefined
  background: string | undefined
  shortDescription: string | undefined
  marketOpportunity: string | undefined
  developmentStage: string | undefined
  ipStatusText: string | undefined
  ipNumber: string | undefined
  ipUrl: string | undefined
  technicalProblem: string | undefined
  solutionText: string | undefined
  fullDescription: string | undefined
  clientDepartments: string[] | undefined
  trl: string | undefined
  technologyValidation: string[] | undefined
  ipText: string | undefined
  supportingDocuments: Array<{ name?: string; url?: string }> | undefined
  contactDetail: { name?: string; email?: string } | undefined
  subtitle: string | undefined
  technologyNumber: string | undefined
}

export function stripHtml(html: string): string {
  return html
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\r\r/g, '\n\n')
    .replace(/\r/g, '\n')
    .trim()
}

export function parseRawData(tech: TechnologyDetail): ParsedRawData {
  const r = tech.raw_data as Record<string, unknown> | null

  return {
    keyPoints: r?.key_points as string[] | undefined,
    inventors: Array.isArray(r?.inventors) ? r!.inventors as string[] : undefined,
    applications: Array.isArray(r?.applications) ? r!.applications as string[] : undefined,
    applicationsText: typeof r?.applications === 'string' ? r!.applications as string : undefined,
    advantages: Array.isArray(r?.advantages) ? r!.advantages as string[] : undefined,
    advantagesText: typeof r?.advantages === 'string' ? r!.advantages as string : undefined,
    otherHtml: r?.other as string | undefined,
    abstractText: r?.abstract as string | undefined,
    benefitHtml: r?.benefit as string | undefined,
    marketApplicationHtml: r?.market_application as string | undefined,
    publicationsHtml: typeof r?.publications === 'string' ? r!.publications as string : undefined,
    publicationsList: Array.isArray(r?.publications) ? r!.publications as Array<{ text?: string; url?: string }> : undefined,
    researchers: r?.researchers as Array<{ name?: string; email?: string; expertise?: string }> | undefined,
    documents: r?.documents as Array<{ name?: string; url?: string; size?: number }> | undefined,
    contactsList: r?.contacts as Array<{ name?: string; email?: string; phone?: string }> | undefined,
    flintboxTags: r?.flintbox_tags as string[] | undefined,
    docketNumber: r?.docket_number as string | undefined,
    licensingContact: r?.licensing_contact as { name?: string; title?: string; email?: string } | undefined,
    pdfUrl: r?.pdf_url as string | undefined,
    relatedPortfolio: r?.related_portfolio as Array<{ title?: string; url?: string }> | undefined,
    background: r?.background as string | undefined,
    shortDescription: r?.short_description as string | undefined,
    marketOpportunity: r?.market_opportunity as string | undefined,
    developmentStage: r?.development_stage as string | undefined,
    ipStatusText: r?.ip_status as string | undefined,
    ipNumber: r?.ip_number as string | undefined,
    ipUrl: r?.ip_url as string | undefined,
    technicalProblem: r?.technical_problem as string | undefined,
    solutionText: r?.solution as string | undefined,
    fullDescription: r?.full_description as string | undefined,
    clientDepartments: r?.client_departments as string[] | undefined,
    trl: r?.trl as string | undefined,
    technologyValidation: Array.isArray(r?.technology_validation) ? r!.technology_validation as string[] : undefined,
    ipText: r?.ip_text as string | undefined,
    supportingDocuments: Array.isArray(r?.supporting_documents) ? r!.supporting_documents as Array<{ name?: string; url?: string }> : undefined,
    contactDetail: r?.contact as { name?: string; email?: string } | undefined,
    subtitle: r?.subtitle as string | undefined,
    technologyNumber: r?.technology_number as string | undefined,
  }
}
