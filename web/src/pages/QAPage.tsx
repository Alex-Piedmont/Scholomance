import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Header } from '../components/Layout'
import { ErrorMessage, EmptyState } from '../components/common'
import { statsApi, technologiesApi } from '../api/client'
import type { UniversityCount, TechnologySummary, PaginatedTechnologies } from '../api/types'

export function QAPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const selectedUniversity = searchParams.get('university') || ''
  const page = parseInt(searchParams.get('page') || '1', 10)
  const recentOnly = searchParams.get('recent') === '1'

  const [universities, setUniversities] = useState<UniversityCount[]>([])
  const [data, setData] = useState<PaginatedTechnologies | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch university list
  useEffect(() => {
    statsApi.getByUniversity().then(setUniversities).catch(() => {})
  }, [])

  // Fetch technologies when university or filters change
  useEffect(() => {
    if (!selectedUniversity) {
      setData(null)
      return
    }
    setLoading(true)
    setError(null)
    const filters: Record<string, unknown> = {
      university: [selectedUniversity],
      page,
      limit: 20,
    }
    if (recentOnly) {
      // Show only technologies updated in the last 2 hours
      const since = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
      filters.updated_since = since
    }
    technologiesApi
      .list(filters as import('../api/types').TechnologyFilters)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [selectedUniversity, page, recentOnly])

  const handleUniversityChange = (uni: string) => {
    const params = new URLSearchParams()
    if (uni) params.set('university', uni)
    if (recentOnly) params.set('recent', '1')
    setSearchParams(params, { replace: true })
  }

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams)
    params.set('page', String(newPage))
    setSearchParams(params, { replace: true })
  }

  const handleRecentToggle = () => {
    const params = new URLSearchParams(searchParams)
    if (recentOnly) {
      params.delete('recent')
    } else {
      params.set('recent', '1')
      params.delete('page')
    }
    setSearchParams(params, { replace: true })
  }

  return (
    <div>
      <Header title="QA Review" />

      <div className="p-6 space-y-6">
        {/* University selector + filters */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-end gap-4">
            <div className="flex-1 max-w-md">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select University
              </label>
              <select
                value={selectedUniversity}
                onChange={(e) => handleUniversityChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Choose a university...</option>
                {universities
                  .sort((a, b) => a.university.localeCompare(b.university))
                  .map((u) => (
                    <option key={u.university} value={u.university}>
                      {u.university} ({u.count} technologies)
                    </option>
                  ))}
              </select>
            </div>
            <button
              onClick={handleRecentToggle}
              className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                recentOnly
                  ? 'bg-blue-100 border-blue-300 text-blue-800 font-medium'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              Recently updated only
            </button>
          </div>
        </div>

        {/* Error */}
        {error && <ErrorMessage message={error} />}

        {/* Technology list */}
        {selectedUniversity && !error && (
          <div className="bg-white rounded-lg shadow">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : data && data.items.length > 0 ? (
              <>
                <div className="px-4 py-3 border-b border-gray-200 text-sm text-gray-500">
                  {data.total} technologies — Page {data.page} of {data.pages}
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase">
                      <th className="px-4 py-3">Title</th>
                      <th className="px-4 py-3 w-32">Tech ID</th>
                      <th className="px-4 py-3 w-24">Fields</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.items.map((tech) => (
                      <tr
                        key={tech.uuid}
                        onClick={() => {
                          // Store sibling UUIDs for prev/next navigation
                          sessionStorage.setItem(
                            'qa-siblings',
                            JSON.stringify(data.items.map((t) => t.uuid))
                          )
                          navigate(`/qa/${tech.uuid}`)
                        }}
                        className="hover:bg-blue-50 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {tech.title}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 font-mono">
                          {tech.tech_id}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">
                          {tech.top_field || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Pagination */}
                {data.pages > 1 && (
                  <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
                    <button
                      onClick={() => handlePageChange(page - 1)}
                      disabled={page <= 1}
                      className="px-3 py-1.5 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      Previous
                    </button>
                    <span className="text-sm text-gray-500">
                      Page {data.page} of {data.pages}
                    </span>
                    <button
                      onClick={() => handlePageChange(page + 1)}
                      disabled={page >= data.pages}
                      className="px-3 py-1.5 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            ) : (
              <EmptyState
                title="No technologies found"
                description={`No technologies for ${selectedUniversity}`}
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
