import { useParams, useNavigate } from 'react-router-dom'
import { Header } from '../components/Layout'
import { useTechnology } from '../hooks'

export function DetailPage() {
  const { uuid } = useParams<{ uuid: string }>()
  const navigate = useNavigate()
  const { data: tech, loading, error } = useTechnology(uuid)

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
  const inventors = rawData?.inventors as string[] | undefined
  const applications = rawData?.applications as string[] | undefined
  const advantages = rawData?.advantages as string[] | undefined

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
        {/* Back Button */}
        <button
          onClick={() => navigate(-1)}
          className="mb-6 text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to list
        </button>

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
              {/* Description */}
              {tech.description && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {tech.description.replace(/\r\r/g, '\n\n').replace(/\r/g, '\n')}
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

              {/* Applications */}
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

              {/* Advantages */}
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

              {/* Empty state if no content */}
              {!tech.description && (!keyPoints || keyPoints.length === 0) &&
               (!applications || applications.length === 0) &&
               (!advantages || advantages.length === 0) && (
                <p className="text-gray-500 italic">No description available for this technology.</p>
              )}
            </div>

          </div>

          {/* Side Pane */}
          <div className="lg:w-80 flex-shrink-0">
            <div className="bg-white rounded-lg shadow p-6 space-y-6 sticky top-6">
              {/* Inventors */}
              {inventors && inventors.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 mb-3 uppercase tracking-wide">Inventors</h3>
                  <ul className="space-y-1">
                    {inventors.map((inv, i) => (
                      <li key={i} className="text-sm text-gray-700">{inv}</li>
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
