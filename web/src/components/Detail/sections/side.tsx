import { useNavigate } from 'react-router-dom'
import { DocIcon, SideSectionWrapper } from './primitives'
import type { SectionProps } from './types'

export function ResearchersSection({ data }: SectionProps) {
  const navigate = useNavigate()
  if (!data.researchers || data.researchers.length === 0) return null
  return (
    <SideSectionWrapper title="Researchers">
      <div className="flex flex-wrap gap-2">
        {data.researchers.map((r, i) => (
          <button
            key={i}
            onClick={() => navigate(`/browse?q=${encodeURIComponent(r.name || '')}`)}
            className="px-3 py-1 bg-purple-50 text-purple-700 text-sm rounded-full hover:bg-purple-100 transition-colors"
          >
            {r.name}
          </button>
        ))}
      </div>
    </SideSectionWrapper>
  )
}

export function InventorsSection({ data }: SectionProps) {
  const navigate = useNavigate()
  if (data.researchers && data.researchers.length > 0) return null
  if (!data.inventors || data.inventors.length === 0) return null
  return (
    <SideSectionWrapper title="Inventors">
      <div className="flex flex-wrap gap-2">
        {data.inventors.map((inv, i) => (
          <button
            key={i}
            onClick={() => navigate(`/browse?q=${encodeURIComponent(inv)}`)}
            className="px-3 py-1 bg-purple-50 text-purple-700 text-sm rounded-full hover:bg-purple-100 transition-colors"
          >
            {inv}
          </button>
        ))}
      </div>
    </SideSectionWrapper>
  )
}

export function DepartmentsSection({ data }: SectionProps) {
  if (!data.clientDepartments || data.clientDepartments.length === 0) return null
  return (
    <SideSectionWrapper title="Departments">
      <ul className="space-y-1">
        {data.clientDepartments.map((dept, i) => (
          <li key={i} className="text-sm text-gray-700">
            {dept}
          </li>
        ))}
      </ul>
    </SideSectionWrapper>
  )
}

export function ContactsSection({ data }: SectionProps) {
  if (!data.contactsList || data.contactsList.length === 0) return null
  return (
    <SideSectionWrapper title="Contact">
      <ul className="space-y-2">
        {data.contactsList.map((c, i) => (
          <li key={i} className="text-sm text-gray-700">
            <div className="font-medium">{c.name}</div>
            {c.email && <div className="text-gray-500">{c.email}</div>}
            {c.phone && <div className="text-gray-500">{c.phone}</div>}
          </li>
        ))}
      </ul>
    </SideSectionWrapper>
  )
}

export function ClassificationSection({ tech }: SectionProps) {
  return (
    <SideSectionWrapper title="Classification">
      <dl className="space-y-2">
        {tech.top_field && (
          <div>
            <dt className="text-xs text-gray-500">Field</dt>
            <dd className="text-sm text-gray-900">{tech.top_field}</dd>
          </div>
        )}
        {tech.subfield && (
          <div>
            <dt className="text-xs text-gray-500">Subfield</dt>
            <dd className="text-sm text-gray-900">{tech.subfield}</dd>
          </div>
        )}
        {!tech.top_field && !tech.subfield && (
          <dd className="text-sm text-gray-500 italic">Not classified</dd>
        )}
      </dl>
    </SideSectionWrapper>
  )
}

export function KeywordsSection({ tech }: SectionProps) {
  if (!tech.keywords || tech.keywords.length === 0) return null
  return (
    <SideSectionWrapper title="Keywords">
      <div className="flex flex-wrap gap-2">
        {tech.keywords.map((kw) => (
          <span key={kw} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
            {kw}
          </span>
        ))}
      </div>
    </SideSectionWrapper>
  )
}

export function TagsSection({ data }: SectionProps) {
  if (!data.flintboxTags || data.flintboxTags.length === 0) return null
  return (
    <SideSectionWrapper title="Tags">
      <div className="flex flex-wrap gap-2">
        {data.flintboxTags.map((tag) => (
          <span key={tag} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded">
            {tag}
          </span>
        ))}
      </div>
    </SideSectionWrapper>
  )
}

export function DocumentsSection({ data }: SectionProps) {
  const docs = data.documents || data.supportingDocuments
  if (!docs || docs.length === 0) {
    if (data.pdfUrl) {
      return (
        <SideSectionWrapper title="Documents">
          <a
            href={data.pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            <DocIcon />
            Download Docket PDF
          </a>
        </SideSectionWrapper>
      )
    }
    return null
  }
  return (
    <SideSectionWrapper title="Documents">
      <ul className="space-y-2">
        {docs.map((doc, i) => (
          <li key={i}>
            <a
              href={doc.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
              <DocIcon />
              {doc.name || 'Document'}
            </a>
          </li>
        ))}
      </ul>
    </SideSectionWrapper>
  )
}

export function ContactDetailSection({ data }: SectionProps) {
  if (!data.contactDetail || (data.contactsList && data.contactsList.length > 0)) return null
  return (
    <SideSectionWrapper title="Contact">
      <div className="text-sm text-gray-700">
        {data.contactDetail.name && <div className="font-medium">{data.contactDetail.name}</div>}
        {data.contactDetail.email && (
          <a href={`mailto:${data.contactDetail.email}`} className="text-blue-600 hover:underline">
            {data.contactDetail.email}
          </a>
        )}
      </div>
    </SideSectionWrapper>
  )
}

export function LicensingContactSection({ data }: SectionProps) {
  if (!data.licensingContact) return null
  const { name, title, email } = data.licensingContact
  return (
    <SideSectionWrapper title="Licensing Contact">
      <div className="text-sm text-gray-700">
        {name && <div className="font-medium">{name}</div>}
        {title && <div className="text-gray-500">{title}</div>}
        {email && (
          <a href={`mailto:${email}`} className="text-blue-600 hover:underline">
            {email}
          </a>
        )}
      </div>
    </SideSectionWrapper>
  )
}

export function RelatedPortfolioSection({ data }: SectionProps) {
  if (!data.relatedPortfolio || data.relatedPortfolio.length === 0) return null
  return (
    <SideSectionWrapper title="Related Technologies">
      <ul className="space-y-1">
        {data.relatedPortfolio.map((item, i) => (
          <li key={i}>
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline"
            >
              {item.title || 'Related technology'}
            </a>
          </li>
        ))}
      </ul>
    </SideSectionWrapper>
  )
}

export function SourceLinkSection({ tech }: SectionProps) {
  return (
    <SideSectionWrapper title="Source">
      <a
        href={tech.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
          />
        </svg>
        View on university website
      </a>
    </SideSectionWrapper>
  )
}
