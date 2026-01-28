import { useParams, useNavigate } from 'react-router-dom'
import { Header } from '../components/Layout'
import { SourceLink, RawDataViewer } from '../components/Detail'
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
          <div className="bg-white rounded-lg shadow">
            <div className="p-6">
              <div className="animate-pulse space-y-4">
                <div className="h-8 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/4" />
                <div className="h-32 bg-gray-200 rounded" />
              </div>
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
  const publishedOn = rawData?.published_on as string | undefined
  const inventors = rawData?.inventors as string[] | undefined
  const applications = rawData?.applications as string[] | undefined
  const advantages = rawData?.advantages as string[] | undefined
  const stage = rawData?.stage as string | undefined

  return (
    <div>
      <Header title="Technology Details" />

      <div className="p-6">
        {/* Back Button */}
        <button
          onClick={() => navigate(-1)}
          className="mb-4 text-sm text-blue-600 hover:underline flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </button>

        <div className="space-y-6">
          {/* Main Card */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-gray-200">
              <h1 className="text-2xl font-bold text-gray-900 mb-3">
                {tech.title}
              </h1>
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-3 py-1 bg-gray-100 text-gray-700 text-sm font-medium rounded">
                  {tech.university.toUpperCase()}
                </span>
                {tech.top_field && (
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                    {tech.top_field}
                  </span>
                )}
                {tech.subfield && (
                  <span className="px-3 py-1 bg-blue-50 text-blue-700 text-sm rounded">
                    {tech.subfield}
                  </span>
                )}
                {tech.patent_status && tech.patent_status !== 'unknown' && (
                  <span className={`px-3 py-1 text-sm rounded ${
                    tech.patent_status === 'granted' ? 'bg-green-100 text-green-700' :
                    tech.patent_status === 'pending' || tech.patent_status === 'filed' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    Patent: {tech.patent_status}
                  </span>
                )}
                {stage && (
                  <span className="px-3 py-1 bg-purple-100 text-purple-700 text-sm rounded">
                    {stage}
                  </span>
                )}
              </div>
            </div>

            {/* Description */}
            {tech.description && (
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Description</h2>
                <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {tech.description.replace(/\r\r/g, '\n\n').replace(/\r/g, '\n')}
                </p>
              </div>
            )}

            {/* Key Points */}
            {keyPoints && keyPoints.length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Key Points</h2>
                <ul className="space-y-2">
                  {keyPoints.map((point, i) => (
                    <li key={i} className="flex gap-2 text-gray-700">
                      <span className="text-blue-500 mt-1">•</span>
                      <span>{point.replace(/\r\r/g, ' ').replace(/\r/g, ' ')}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Applications */}
            {applications && applications.length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Applications</h2>
                <ul className="space-y-2">
                  {applications.map((app, i) => (
                    <li key={i} className="flex gap-2 text-gray-700">
                      <span className="text-green-500 mt-1">•</span>
                      <span>{app}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Advantages */}
            {advantages && advantages.length > 0 && (
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Advantages</h2>
                <ul className="space-y-2">
                  {advantages.map((adv, i) => (
                    <li key={i} className="flex gap-2 text-gray-700">
                      <span className="text-green-500 mt-1">✓</span>
                      <span>{adv}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Source Link */}
            <SourceLink url={tech.url} />
          </div>

          {/* Sidebar Info */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Metadata Card */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wide">Details</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="text-xs text-gray-500 uppercase">University</dt>
                  <dd className="text-sm text-gray-900 font-medium">{tech.university}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-500 uppercase">Tech ID</dt>
                  <dd className="text-sm text-gray-900 font-mono">{tech.tech_id}</dd>
                </div>
                {publishedOn && (
                  <div>
                    <dt className="text-xs text-gray-500 uppercase">Published</dt>
                    <dd className="text-sm text-gray-900">{new Date(publishedOn).toLocaleDateString()}</dd>
                  </div>
                )}
                {tech.first_seen && (
                  <div>
                    <dt className="text-xs text-gray-500 uppercase">First Seen</dt>
                    <dd className="text-sm text-gray-900">{new Date(tech.first_seen).toLocaleDateString()}</dd>
                  </div>
                )}
                {tech.classification_status && (
                  <div>
                    <dt className="text-xs text-gray-500 uppercase">Classification</dt>
                    <dd className="text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        tech.classification_status === 'completed' ? 'bg-green-100 text-green-700' :
                        tech.classification_status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {tech.classification_status}
                      </span>
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Keywords Card */}
            {tech.keywords && tech.keywords.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wide">Keywords</h3>
                <div className="flex flex-wrap gap-2">
                  {tech.keywords.map((kw) => (
                    <span key={kw} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Patent Geography Card */}
            {tech.patent_geography && tech.patent_geography.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wide">Patent Coverage</h3>
                <div className="flex flex-wrap gap-2">
                  {tech.patent_geography.map((geo) => (
                    <span key={geo} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded font-medium">
                      {geo}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Inventors Card */}
            {inventors && inventors.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wide">Inventors</h3>
                <ul className="space-y-1">
                  {inventors.map((inv, i) => (
                    <li key={i} className="text-sm text-gray-700">{inv}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Raw Data */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <RawDataViewer data={tech.raw_data} />
          </div>
        </div>
      </div>
    </div>
  )
}
