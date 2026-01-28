import { useParams, useNavigate } from 'react-router-dom'
import { Header } from '../components/Layout'
import { MetadataPanel, IframeEmbed, RawDataViewer } from '../components/Detail'
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

        <div className="bg-white rounded-lg shadow overflow-hidden">
          {/* Header */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  {tech.title}
                </h1>
                <div className="flex items-center gap-3">
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded">
                    {tech.university}
                  </span>
                  {tech.top_field && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                      {tech.top_field}
                    </span>
                  )}
                  <span className={`px-2 py-1 text-xs rounded ${
                    tech.classification_status === 'completed'
                      ? 'bg-green-100 text-green-700'
                      : tech.classification_status === 'pending'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {tech.classification_status || 'unknown'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Metadata */}
          <div className="p-6 border-b border-gray-200 bg-gray-50">
            <MetadataPanel tech={tech} />
          </div>

          {/* Description */}
          {tech.description && (
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900 mb-3">Description</h2>
              <div className="prose prose-sm max-w-none text-gray-700">
                <p className="whitespace-pre-wrap">{tech.description}</p>
              </div>
            </div>
          )}

          {/* Iframe Embed */}
          <IframeEmbed url={tech.url} title={tech.title} />

          {/* Raw Data */}
          <RawDataViewer data={tech.raw_data} />
        </div>
      </div>
    </div>
  )
}
