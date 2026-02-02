import { useNavigate } from 'react-router-dom'
import type { TechnologyDetail } from '../../api/types'
import type { ParsedRawData } from './parseRawData'

interface Props {
  tech: TechnologyDetail
  data: ParsedRawData
}

function SideSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <h3 className="text-sm font-semibold text-gray-900 mb-2 uppercase tracking-wide">{title}</h3>
      {children}
    </div>
  )
}

const DocIcon = () => (
  <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
  </svg>
)

export function SidePanel({ tech, data }: Props) {
  const navigate = useNavigate()
  const {
    researchers, inventors, clientDepartments, contactsList, contactDetail,
    flintboxTags, documents, supportingDocuments, licensingContact, pdfUrl,
    relatedPortfolio,
  } = data

  return (
    <div className="lg:w-80 flex-shrink-0">
      <div className="bg-white rounded-lg shadow p-5 divide-y divide-gray-100 sticky top-6">
        {/* Researchers */}
        {researchers && researchers.length > 0 && (
          <SideSection title="Researchers">
            <div className="flex flex-wrap gap-2">
              {researchers.map((r, i) => (
                <button
                  key={i}
                  onClick={() => navigate(`/browse?q=${encodeURIComponent(r.name || '')}`)}
                  className="px-3 py-1 bg-purple-50 text-purple-700 text-sm rounded-full hover:bg-purple-100 transition-colors"
                >
                  {r.name}
                </button>
              ))}
            </div>
          </SideSection>
        )}

        {/* Inventors */}
        {inventors && inventors.length > 0 && !researchers?.length && (
          <SideSection title="Inventors">
            <div className="flex flex-wrap gap-2">
              {inventors.map((inv, i) => (
                <button
                  key={i}
                  onClick={() => navigate(`/browse?q=${encodeURIComponent(inv)}`)}
                  className="px-3 py-1 bg-purple-50 text-purple-700 text-sm rounded-full hover:bg-purple-100 transition-colors"
                >
                  {inv}
                </button>
              ))}
            </div>
          </SideSection>
        )}

        {/* Departments */}
        {clientDepartments && clientDepartments.length > 0 && (
          <SideSection title="Departments">
            <ul className="space-y-1">
              {clientDepartments.map((dept, i) => (
                <li key={i} className="text-sm text-gray-700">{dept}</li>
              ))}
            </ul>
          </SideSection>
        )}

        {/* Contacts */}
        {contactsList && contactsList.length > 0 && (
          <SideSection title="Contact">
            <ul className="space-y-2">
              {contactsList.map((c, i) => (
                <li key={i} className="text-sm text-gray-700">
                  <div className="font-medium">{c.name}</div>
                  {c.email && <div className="text-gray-500">{c.email}</div>}
                  {c.phone && <div className="text-gray-500">{c.phone}</div>}
                </li>
              ))}
            </ul>
          </SideSection>
        )}

        {/* Classification */}
        <SideSection title="Classification">
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
        </SideSection>

        {/* Keywords */}
        {tech.keywords && tech.keywords.length > 0 && (
          <SideSection title="Keywords">
            <div className="flex flex-wrap gap-2">
              {tech.keywords.map((kw) => (
                <span key={kw} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                  {kw}
                </span>
              ))}
            </div>
          </SideSection>
        )}

        {/* Tags */}
        {flintboxTags && flintboxTags.length > 0 && (
          <SideSection title="Tags">
            <div className="flex flex-wrap gap-2">
              {flintboxTags.map((tag) => (
                <span key={tag} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded">
                  {tag}
                </span>
              ))}
            </div>
          </SideSection>
        )}

        {/* Documents (Flintbox) */}
        {documents && documents.length > 0 && (
          <SideSection title="Documents">
            <ul className="space-y-2">
              {documents.map((doc, i) => (
                <li key={i}>
                  <a href={doc.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline">
                    <DocIcon />
                    {doc.name || 'Document'}
                  </a>
                </li>
              ))}
            </ul>
          </SideSection>
        )}

        {/* Documents (TechPublisher) */}
        {supportingDocuments && supportingDocuments.length > 0 && (
          <SideSection title="Documents">
            <ul className="space-y-2">
              {supportingDocuments.map((doc, i) => (
                <li key={i}>
                  <a href={doc.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline">
                    <DocIcon />
                    {doc.name || 'Document'}
                  </a>
                </li>
              ))}
            </ul>
          </SideSection>
        )}

        {/* Contact (TechPublisher) */}
        {contactDetail && !contactsList?.length && (
          <SideSection title="Contact">
            <div className="text-sm text-gray-700">
              {contactDetail.name && <div className="font-medium">{contactDetail.name}</div>}
              {contactDetail.email && (
                <a href={`mailto:${contactDetail.email}`} className="text-blue-600 hover:underline">
                  {contactDetail.email}
                </a>
              )}
            </div>
          </SideSection>
        )}

        {/* Licensing Contact (Stanford) */}
        {licensingContact && (
          <SideSection title="Licensing Contact">
            <div className="text-sm text-gray-700">
              {licensingContact.name && <div className="font-medium">{licensingContact.name}</div>}
              {licensingContact.title && <div className="text-gray-500">{licensingContact.title}</div>}
              {licensingContact.email && (
                <a href={`mailto:${licensingContact.email}`} className="text-blue-600 hover:underline">
                  {licensingContact.email}
                </a>
              )}
            </div>
          </SideSection>
        )}

        {/* PDF (Stanford) */}
        {pdfUrl && (
          <SideSection title="Documents">
            <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline">
              <DocIcon />
              Download Docket PDF
            </a>
          </SideSection>
        )}

        {/* Related Portfolio (Stanford) */}
        {relatedPortfolio && relatedPortfolio.length > 0 && (
          <SideSection title="Related Technologies">
            <ul className="space-y-1">
              {relatedPortfolio.map((item, i) => (
                <li key={i}>
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                    {item.title || 'Related technology'}
                  </a>
                </li>
              ))}
            </ul>
          </SideSection>
        )}

        {/* Source */}
        <SideSection title="Source">
          <a
            href={tech.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            View on university website
          </a>
        </SideSection>
      </div>
    </div>
  )
}
