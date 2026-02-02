import { useEffect, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { Header } from '../components/Layout'
import { useTechnology } from '../hooks'

export function DetailPage() {
  const { uuid } = useParams<{ uuid: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { data: tech, loading, error } = useTechnology(uuid)

  // Prev/next navigation from browse list
  const navState = location.state as { uuids?: string[]; index?: number } | null
  const uuids = navState?.uuids
  const currentIndex = navState?.index ?? -1
  const prevUuid = uuids && currentIndex > 0 ? uuids[currentIndex - 1] : null
  const nextUuid = uuids && currentIndex >= 0 && currentIndex < uuids.length - 1 ? uuids[currentIndex + 1] : null

  const goToSibling = useCallback((targetUuid: string, newIndex: number) => {
    navigate(`/technology/${targetUuid}`, {
      state: { uuids, index: newIndex },
      replace: true,
    })
  }, [navigate, uuids])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'ArrowLeft' && prevUuid) {
        goToSibling(prevUuid, currentIndex - 1)
      } else if (e.key === 'ArrowRight' && nextUuid) {
        goToSibling(nextUuid, currentIndex + 1)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [prevUuid, nextUuid, currentIndex, goToSibling])

  if (loading) {
    return (
      <div>
        <Header title="Loading..." />
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-10 bg-gray-200 rounded w-3/4" />
            <div className="h-5 bg-gray-200 rounded w-1/2" />
            <div className="flex gap-6 mt-6">
              <div className="flex-1 h-64 bg-gray-200 rounded" />
              <div className="w-80 h-64 bg-gray-200 rounded" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !tech) {
    return (
      <div>
        <Header title="Error" />
        <div className="p-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-center">
              <p className="text-red-600 mb-4">
                {error?.message || 'Technology not found'}
              </p>
              <button
                onClick={() => navigate(-1)}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Go Back
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Extract additional data from raw_data
  const rawData = tech.raw_data as Record<string, unknown> | null
  const keyPoints = rawData?.key_points as string[] | undefined
  const inventors = Array.isArray(rawData?.inventors) ? rawData.inventors as string[] : undefined
  const applications = Array.isArray(rawData?.applications) ? rawData.applications as string[] : undefined
  const advantages = Array.isArray(rawData?.advantages) ? rawData.advantages as string[] : undefined
  const otherHtml = rawData?.other as string | undefined
  const abstractText = rawData?.abstract as string | undefined
  const benefitHtml = rawData?.benefit as string | undefined
  const marketApplicationHtml = rawData?.market_application as string | undefined
  const publicationsHtml = typeof rawData?.publications === 'string' ? rawData.publications as string : undefined
  const publicationsList = Array.isArray(rawData?.publications) ? rawData.publications as Array<{ text?: string; url?: string }> : undefined
  const researchers = rawData?.researchers as Array<{ name?: string; email?: string; expertise?: string }> | undefined
  const documents = rawData?.documents as Array<{ name?: string; url?: string; size?: number }> | undefined
  const contactsList = rawData?.contacts as Array<{ name?: string; email?: string; phone?: string }> | undefined
  const flintboxTags = rawData?.flintbox_tags as string[] | undefined
  // Stanford-specific fields
  const docketNumber = rawData?.docket_number as string | undefined
  const licensingContact = rawData?.licensing_contact as { name?: string; title?: string; email?: string } | undefined
  const pdfUrl = rawData?.pdf_url as string | undefined
  const relatedPortfolio = rawData?.related_portfolio as Array<{ title?: string; url?: string }> | undefined
  // Algolia-sourced structured sections
  const background = rawData?.background as string | undefined
  const shortDescription = rawData?.short_description as string | undefined
  const marketOpportunity = rawData?.market_opportunity as string | undefined
  const developmentStage = rawData?.development_stage as string | undefined
  const ipStatusText = rawData?.ip_status as string | undefined
  const ipNumber = rawData?.ip_number as string | undefined
  const ipUrl = rawData?.ip_url as string | undefined
  const technicalProblem = rawData?.technical_problem as string | undefined
  const solutionText = rawData?.solution as string | undefined
  const fullDescription = rawData?.full_description as string | undefined
  const clientDepartments = rawData?.client_departments as string[] | undefined

  // Helper to strip HTML tags and clean up text
  const stripHtml = (html: string) => {
    return html
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .replace(/\r\r/g, '\n\n')
      .replace(/\r/g, '\n')
      .trim()
  }

  // Format the updated date
  const updatedDate = tech.updated_at
    ? new Date(tech.updated_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    : tech.scraped_at
    ? new Date(tech.scraped_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    : null

  // Format patent status for display
  const formatPatentStatus = (status: string | null) => {
    if (!status || status === 'unknown') return 'Unknown'
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  return (
    <div>
      <Header title="Technology Details" />

      <div className="p-6">
        {/* Navigation Bar */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => navigate(-1)}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to list
          </button>

          {uuids && uuids.length > 1 && (
            <div className="flex items-center gap-3">
              <button
                disabled={!prevUuid}
                onClick={() => prevUuid && goToSibling(prevUuid, currentIndex - 1)}
                className="text-sm text-gray-500 hover:text-gray-700 disabled:text-gray-300 disabled:cursor-not-allowed flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Last
              </button>
              <span className="text-xs text-gray-400">{currentIndex + 1} / {uuids.length}</span>
              <button
                disabled={!nextUuid}
                onClick={() => nextUuid && goToSibling(nextUuid, currentIndex + 1)}
                className="text-sm text-gray-500 hover:text-gray-700 disabled:text-gray-300 disabled:cursor-not-allowed flex items-center gap-1"
              >
                Next
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          {tech.title}
        </h1>

        {/* Subheader: University | Legal Status | Updated Date */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600 mb-8">
          <span className="font-medium">{tech.university}</span>
          <span className="text-gray-300">|</span>
          <span className={`font-medium ${
            tech.patent_status === 'granted' ? 'text-green-600' :
            tech.patent_status === 'pending' || tech.patent_status === 'filed' ? 'text-yellow-600' :
            'text-gray-600'
          }`}>
            Patent: {formatPatentStatus(tech.patent_status)}
          </span>
          {docketNumber && (
            <>
              <span className="text-gray-300">|</span>
              <span>Docket: {docketNumber}</span>
            </>
          )}
          {updatedDate && (
            <>
              <span className="text-gray-300">|</span>
              <span>Updated {updatedDate}</span>
            </>
          )}
        </div>

        {/* Main Content: Two Column Layout */}
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Main Content Area */}
          <div className="flex-1 min-w-0">
            <div className="bg-white rounded-lg shadow p-6 space-y-6">
              {/* Short Description (Algolia-sourced) */}
              {shortDescription && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Summary</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {shortDescription}
                  </p>
                </div>
              )}

              {/* Abstract */}
              {abstractText && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Abstract</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {stripHtml(abstractText)}
                  </p>
                </div>
              )}

              {/* Description / Overview (from 'other' field) */}
              {otherHtml && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Overview</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {stripHtml(otherHtml)}
                  </p>
                </div>
              )}

              {/* Fallback to short description if no detailed content */}
              {!otherHtml && !abstractText && !shortDescription && tech.description && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {tech.description.replace(/\r\r/g, '\n\n').replace(/\r/g, '\n')}
                  </p>
                </div>
              )}

              {/* Technical Problem */}
              {technicalProblem && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Technical Problem</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {technicalProblem}
                  </p>
                </div>
              )}

              {/* Solution */}
              {solutionText && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Solution</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {solutionText}
                  </p>
                </div>
              )}

              {/* Background */}
              {background && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Background</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {background}
                  </p>
                </div>
              )}

              {/* Benefits */}
              {benefitHtml && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Benefits</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {stripHtml(benefitHtml)}
                  </p>
                </div>
              )}

              {/* Market Applications / Potential Opportunities */}
              {(marketApplicationHtml || marketOpportunity) && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Market Opportunity</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {marketApplicationHtml ? stripHtml(marketApplicationHtml) : marketOpportunity}
                  </p>
                </div>
              )}

              {/* Development Stage */}
              {developmentStage && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Development Stage</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {developmentStage}
                  </p>
                </div>
              )}

              {/* Key Points */}
              {keyPoints && keyPoints.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Key Points</h2>
                  <ul className="space-y-2">
                    {keyPoints.map((point, i) => (
                      <li key={i} className="flex gap-2 text-gray-700">
                        <span className="text-blue-500 mt-1 flex-shrink-0">•</span>
                        <span>{point.replace(/\r\r/g, ' ').replace(/\r/g, ' ')}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Applications (array from non-Algolia scrapers) */}
              {applications && applications.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Applications</h2>
                  <ul className="space-y-2">
                    {applications.map((app, i) => (
                      <li key={i} className="flex gap-2 text-gray-700">
                        <span className="text-green-500 mt-1 flex-shrink-0">•</span>
                        <span>{app}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Applications (text from Algolia) */}
              {!applications?.length && typeof rawData?.applications === 'string' && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Applications</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {String(rawData.applications)}
                  </p>
                </div>
              )}

              {/* Advantages (array from non-Algolia scrapers) */}
              {advantages && advantages.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Advantages</h2>
                  <ul className="space-y-2">
                    {advantages.map((adv, i) => (
                      <li key={i} className="flex gap-2 text-gray-700">
                        <span className="text-green-500 mt-1 flex-shrink-0">✓</span>
                        <span>{adv}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Advantages (text from Algolia) */}
              {!advantages?.length && typeof rawData?.advantages === 'string' && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Advantages</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {String(rawData.advantages)}
                  </p>
                </div>
              )}

              {/* Publications (structured list from Stanford) */}
              {publicationsList && publicationsList.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Publications</h2>
                  <ul className="space-y-2">
                    {publicationsList.map((pub, i) => (
                      <li key={i} className="text-gray-700 text-sm">
                        {pub.url ? (
                          <a href={pub.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                            {pub.text || pub.url}
                          </a>
                        ) : (
                          <span>{pub.text}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Publications (HTML from Flintbox, or plain text from Algolia) */}
              {!publicationsList?.length && (publicationsHtml || (typeof rawData?.publications === 'string' && !publicationsHtml)) && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Publications</h2>
                  {publicationsHtml && publicationsHtml.includes('<') ? (
                    <div
                      className="text-gray-700 leading-relaxed prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{ __html: publicationsHtml }}
                    />
                  ) : (
                    <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                      {String(publicationsHtml || rawData?.publications)}
                    </p>
                  )}
                </div>
              )}

              {/* IP Status */}
              {(ipStatusText || ipNumber) && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">IP Status</h2>
                  {ipStatusText && (
                    <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                      {ipStatusText}
                    </p>
                  )}
                  {ipNumber && (
                    <p className="text-gray-700 mt-2">
                      <span className="font-medium">Patent: </span>
                      {ipUrl ? (
                        <a href={ipUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                          {ipNumber}
                        </a>
                      ) : (
                        <span>{ipNumber}</span>
                      )}
                    </p>
                  )}
                </div>
              )}

              {/* Empty state if no content */}
              {!tech.description && !otherHtml && !abstractText && !shortDescription &&
               !benefitHtml && !marketApplicationHtml && !marketOpportunity &&
               !publicationsHtml && !background && !fullDescription &&
               (!keyPoints || keyPoints.length === 0) &&
               (!applications || applications.length === 0) &&
               (!advantages || advantages.length === 0) && (
                <p className="text-gray-500 italic">No description available for this technology.</p>
              )}
            </div>

          </div>

          {/* Side Pane */}
          <div className="lg:w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow p-6 space-y-6 sticky top-6">
              {/* Researchers (from Flintbox) */}
              {researchers && researchers.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Researchers</h3>
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
                </div>
              )}

              {/* Inventors (from non-Flintbox scrapers) */}
              {inventors && inventors.length > 0 && !researchers?.length && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Inventors</h3>
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
                </div>
              )}

              {/* Client Departments */}
              {clientDepartments && clientDepartments.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Departments</h3>
                  <ul className="space-y-1">
                    {clientDepartments.map((dept, i) => (
                      <li key={i} className="text-sm text-gray-700">{dept}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Contacts */}
              {contactsList && contactsList.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Contact</h3>
                  <ul className="space-y-2">
                    {contactsList.map((c, i) => (
                      <li key={i} className="text-sm text-gray-700">
                        <div className="font-medium">{c.name}</div>
                        {c.email && <div className="text-gray-500">{c.email}</div>}
                        {c.phone && <div className="text-gray-500">{c.phone}</div>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Field Classification */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Classification</h3>
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
              </div>

              {/* Keywords */}
              {tech.keywords && tech.keywords.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Keywords</h3>
                  <div className="flex flex-wrap gap-2">
                    {tech.keywords.map((kw) => (
                      <span key={kw} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Flintbox Tags */}
              {flintboxTags && flintboxTags.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Tags</h3>
                  <div className="flex flex-wrap gap-2">
                    {flintboxTags.map((tag) => (
                      <span key={tag} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Documents */}
              {documents && documents.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Documents</h3>
                  <ul className="space-y-2">
                    {documents.map((doc, i) => (
                      <li key={i}>
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          {doc.name || 'Document'}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Licensing Contact (Stanford) */}
              {licensingContact && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Licensing Contact</h3>
                  <div className="text-sm text-gray-700">
                    {licensingContact.name && <div className="font-medium">{licensingContact.name}</div>}
                    {licensingContact.title && <div className="text-gray-500">{licensingContact.title}</div>}
                    {licensingContact.email && (
                      <a href={`mailto:${licensingContact.email}`} className="text-blue-600 hover:underline">
                        {licensingContact.email}
                      </a>
                    )}
                  </div>
                </div>
              )}

              {/* PDF Download (Stanford) */}
              {pdfUrl && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Documents</h3>
                  <a
                    href={pdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    Download Docket PDF
                  </a>
                </div>
              )}

              {/* Related Portfolio (Stanford) */}
              {relatedPortfolio && relatedPortfolio.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Related Technologies</h3>
                  <ul className="space-y-1">
                    {relatedPortfolio.map((item, i) => (
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
                </div>
              )}

              {/* University Source Link */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Source</h3>
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
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
