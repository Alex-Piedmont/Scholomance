import { useEffect, useState } from 'react'
import { Icon } from '../Layout/Icon'
import { useTechnology } from '../../hooks/useTechnology'
import { getUniversityName } from '../../utils/universityNames'
import { parseRawData } from '../Detail/parseRawData'
import {
  SubtitleSection,
  SummarySection,
  AbstractSection,
  OverviewSection,
  DescriptionSection,
  TechnicalProblemSection,
  SolutionSection,
  BackgroundSection,
  FullDescriptionSection,
  BenefitsSection,
  MarketOpportunitySection,
  DevelopmentStageSection,
  TrlSection,
  KeyPointsSection,
  ApplicationsSection,
  AdvantagesSection,
  TechnologyValidationSection,
  PublicationsSection,
  IpStatusSection,
  ResearchersSection,
  InventorsSection,
  DepartmentsSection,
  ContactsSection,
  ClassificationSection,
  KeywordsSection,
  TagsSection,
  DocumentsSection,
  ContactDetailSection,
  LicensingContactSection,
  RelatedPortfolioSection,
  SourceLinkSection,
} from '../Detail/sections'
import type { TechnologyDetail } from '../../api/types'

interface DiscoveryDrawerProps {
  uuid: string | null
  onClose: () => void
}

type Phase = 'idle' | 'queued'

export function DiscoveryDrawer({ uuid, onClose }: DiscoveryDrawerProps) {
  const open = !!uuid

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <>
      <div
        className={`drawer-overlay ${open ? 'is-open' : ''}`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside className={`drawer ${open ? 'is-open' : ''}`} aria-hidden={!open}>
        {uuid && <DrawerContent key={uuid} uuid={uuid} onClose={onClose} />}
      </aside>
    </>
  )
}

function DrawerContent({ uuid, onClose }: { uuid: string; onClose: () => void }) {
  const { data: tech, loading } = useTechnology(uuid)
  const [phase, setPhase] = useState<Phase>('idle')

  const status = (tech?.patent_status || '').toLowerCase()
  const statusClass =
    status === 'granted' ? 'is-granted' : status === 'pending' ? 'is-pending' : ''
  const showTechId = tech && /[A-Z0-9]/.test(tech.tech_id)

  return (
    <>
      {tech && (
        <div className="drawer__head">
          <div className="drawer__head-top">
            <div className="drawer__univ">
              {getUniversityName(tech.university)}
              {showTechId && <> · {tech.tech_id}</>}
            </div>
            <button className="drawer__close" onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>
          <h2 className="drawer__title">{tech.title}</h2>
          <div className="drawer__meta-row">
            {(tech.top_field || tech.subfield) && (
              <span>
                <b>{tech.top_field}</b>
                {tech.subfield && <> / {tech.subfield}</>}
              </span>
            )}
            {tech.patent_status && (
              <span className={`patent-badge ${statusClass}`}>
                <span className="dot" />
                Patent {tech.patent_status}
                {tech.patent_geography && tech.patent_geography.length > 0 && (
                  <> · {tech.patent_geography.join(', ')}</>
                )}
              </span>
            )}
            {tech.first_seen && (
              <span>
                First seen <b>{tech.first_seen.slice(0, 10)}</b>
              </span>
            )}
            {tech.url && (
              <a href={tech.url} target="_blank" rel="noreferrer">
                Source listing <Icon name="external" size={12} />
              </a>
            )}
          </div>
        </div>
      )}

      <div className="drawer__body">
        {loading && !tech && <p style={{ color: 'var(--fg-muted)' }}>Loading…</p>}
        {tech && <DrawerBody tech={tech} />}
      </div>

      <div className="drawer__footer">
        {phase === 'idle' ? (
          <>
            <button className="secondary-btn" type="button">
              Shortlist
            </button>
            <button
              className="assess-btn"
              type="button"
              onClick={() => setPhase('queued')}
              disabled={!tech}
            >
              <Icon name="arrow-right" size={16} />
              Hand-off for Enrichment
            </button>
          </>
        ) : (
          <>
            <button
              className="secondary-btn"
              type="button"
              onClick={() => setPhase('idle')}
            >
              Undo
            </button>
            <button className="assess-btn" type="button" disabled>
              <Icon name="sparkles" size={14} />
              Queued — view on Enrichment tab
            </button>
          </>
        )}
      </div>
    </>
  )
}

function DrawerBody({ tech }: { tech: TechnologyDetail }) {
  const data = parseRawData(tech)
  // Drawer parity: render the same sections DetailPage renders, in a
  // single-column stack. AssessmentSection stays DetailPage-only (explicit
  // Scope Boundaries exclusion in the Migration-QA plan).
  return (
    <div className="drawer-sections">
      <SubtitleSection tech={tech} data={data} />
      <SummarySection tech={tech} data={data} />
      <AbstractSection tech={tech} data={data} />
      <OverviewSection tech={tech} data={data} />
      <DescriptionSection tech={tech} data={data} />
      <TechnicalProblemSection tech={tech} data={data} />
      <SolutionSection tech={tech} data={data} />
      <BackgroundSection tech={tech} data={data} />
      <FullDescriptionSection tech={tech} data={data} />
      <BenefitsSection tech={tech} data={data} />
      <MarketOpportunitySection tech={tech} data={data} />
      <DevelopmentStageSection tech={tech} data={data} />
      <TrlSection tech={tech} data={data} />
      <KeyPointsSection tech={tech} data={data} />
      <ApplicationsSection tech={tech} data={data} />
      <AdvantagesSection tech={tech} data={data} />
      <TechnologyValidationSection tech={tech} data={data} />
      <PublicationsSection tech={tech} data={data} />
      <IpStatusSection tech={tech} data={data} />
      <div className="drawer-sections__side">
        <ResearchersSection tech={tech} data={data} />
        <InventorsSection tech={tech} data={data} />
        <DepartmentsSection tech={tech} data={data} />
        <ContactsSection tech={tech} data={data} />
        <ClassificationSection tech={tech} data={data} />
        <KeywordsSection tech={tech} data={data} />
        <TagsSection tech={tech} data={data} />
        <DocumentsSection tech={tech} data={data} />
        <ContactDetailSection tech={tech} data={data} />
        <LicensingContactSection tech={tech} data={data} />
        <RelatedPortfolioSection tech={tech} data={data} />
        <SourceLinkSection tech={tech} data={data} />
      </div>
    </div>
  )
}
