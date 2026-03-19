import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Header } from '../components/Layout'
import { ErrorMessage, EmptyState } from '../components/common'
import { qaApi } from '../api/client'
import type { UniversityQAStatus, QASample } from '../api/types'

export function QAPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const selectedUniversity = searchParams.get('university') || ''
  const hideApproved = searchParams.get('hideApproved') !== '0' // default ON

  const [universities, setUniversities] = useState<UniversityQAStatus[]>([])
  const [sample, setSample] = useState<QASample | null>(null)
  const [sampleLoading, setSampleLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch university list
  const fetchUniversities = useCallback(() => {
    qaApi.getUniversities().then(setUniversities).catch(() => {})
  }, [])

  useEffect(() => {
    fetchUniversities()
  }, [fetchUniversities])

  // Load sample when university changes
  useEffect(() => {
    if (!selectedUniversity) {
      setSample(null)
      return
    }
    setSampleLoading(true)
    setError(null)
    qaApi
      .getSample(selectedUniversity)
      .then(setSample)
      .catch((e) => {
        if (e.status === 404) {
          setSample(null)
        } else {
          setError(e.message)
        }
      })
      .finally(() => setSampleLoading(false))
  }, [selectedUniversity])

  const handleUniversityChange = (uni: string) => {
    const params = new URLSearchParams()
    if (uni) params.set('university', uni)
    if (!hideApproved) params.set('hideApproved', '0')
    setSearchParams(params, { replace: true })
  }

  const handleApprovedToggle = () => {
    const params = new URLSearchParams(searchParams)
    if (hideApproved) {
      params.set('hideApproved', '0')
    } else {
      params.delete('hideApproved')
    }
    setSearchParams(params, { replace: true })
  }

  const handleCreateSample = async () => {
    if (!selectedUniversity) return
    setSampleLoading(true)
    try {
      const s = await qaApi.createSample(selectedUniversity)
      setSample(s)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create sample')
    } finally {
      setSampleLoading(false)
    }
  }

  const handleRefreshSample = async () => {
    if (!selectedUniversity) return
    setRefreshing(true)
    try {
      await qaApi.refreshSample(selectedUniversity)
      // Reload sample techs
      const s = await qaApi.getSample(selectedUniversity)
      setSample(s)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to refresh')
    } finally {
      setRefreshing(false)
    }
  }

  const handleApprove = async () => {
    if (!selectedUniversity) return
    const uni = universities.find((u) => u.university === selectedUniversity)
    try {
      if (uni?.status === 'approved') {
        await qaApi.unapprove(selectedUniversity)
      } else {
        await qaApi.approve(selectedUniversity)
      }
      fetchUniversities()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to update approval')
    }
  }

  const currentUni = universities.find((u) => u.university === selectedUniversity)
  const filteredUniversities = hideApproved
    ? universities.filter((u) => u.status !== 'approved')
    : universities

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
                {filteredUniversities
                  .sort((a, b) => a.university.localeCompare(b.university))
                  .map((u) => (
                    <option key={u.university} value={u.university}>
                      {u.university} ({u.count} techs)
                      {u.status === 'approved' ? ' [approved]' : ''}
                      {u.conflict_count > 0 ? ` [${u.conflict_count} conflicts]` : ''}
                    </option>
                  ))}
              </select>
            </div>
            <button
              onClick={handleApprovedToggle}
              className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                hideApproved
                  ? 'bg-blue-100 border-blue-300 text-blue-800 font-medium'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              Unapproved only
            </button>
            {selectedUniversity && (
              <>
                <button
                  onClick={handleApprove}
                  className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                    currentUni?.status === 'approved'
                      ? 'bg-green-100 border-green-300 text-green-800 font-medium'
                      : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {currentUni?.status === 'approved' ? 'Approved' : 'Approve'}
                </button>
                {sample && (
                  <button
                    onClick={handleRefreshSample}
                    disabled={refreshing}
                    className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                  >
                    {refreshing ? 'Refreshing...' : 'Refresh Sample'}
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Error */}
        {error && <ErrorMessage message={error} />}

        {/* Sample management */}
        {selectedUniversity && !error && (
          <div className="bg-white rounded-lg shadow">
            {sampleLoading ? (
              <div className="p-8 text-center text-gray-500">Loading sample...</div>
            ) : !sample ? (
              <div className="p-8 text-center">
                <p className="text-sm text-gray-500 mb-4">
                  No QA sample exists for {selectedUniversity}. Create one to start reviewing.
                </p>
                <button
                  onClick={handleCreateSample}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Create Sample (10 technologies)
                </button>
              </div>
            ) : sample.technology_ids.length === 0 ? (
              <EmptyState
                title="No technologies"
                description={`No technologies found for ${selectedUniversity}`}
              />
            ) : (
              <>
                <div className="px-4 py-3 border-b border-gray-200 text-sm text-gray-500">
                  {sample.technology_ids.length} technologies in sample
                  {currentUni?.conflict_count
                    ? ` — ${currentUni.conflict_count} unresolved conflict(s)`
                    : ''}
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase">
                      <th className="px-4 py-3">#</th>
                      <th className="px-4 py-3">Technology ID</th>
                      <th className="px-4 py-3">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {sample.technology_ids.map((id, idx) => (
                      <tr
                        key={id}
                        onClick={() => {
                          // Store sample IDs for prev/next navigation
                          sessionStorage.setItem(
                            'qa-sample-ids',
                            JSON.stringify(sample.technology_ids)
                          )
                          sessionStorage.setItem('qa-university', selectedUniversity)
                          navigate(`/qa/by-id/${id}`)
                        }}
                        className="hover:bg-blue-50 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3 text-sm text-gray-500">{idx + 1}</td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-900">
                          #{id}
                        </td>
                        <td className="px-4 py-3 text-xs text-blue-600">Review</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
