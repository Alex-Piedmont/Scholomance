import { useState, useEffect, useCallback } from 'react'
import { opportunitiesApi, ApiError } from '../../api/client'
import type { OpportunitySummary, CategoryAssessment } from '../../api/types'

function toNum(v: unknown): number | null {
  if (v === null || v === undefined) return null
  const n = typeof v === 'string' ? parseFloat(v) : Number(v)
  return isNaN(n) ? null : n
}

function scoreColorClass(score: unknown): string {
  const n = toNum(score)
  if (n === null) return 'bg-gray-100 text-gray-600'
  if (n >= 0.7) return 'bg-green-100 text-green-700'
  if (n >= 0.4) return 'bg-yellow-100 text-yellow-700'
  return 'bg-gray-100 text-gray-600'
}

function fmtScore(score: unknown): string {
  const n = toNum(score)
  return n !== null ? n.toFixed(2) : 'N/A'
}

function tierBadgeClass(tier: string | null): string {
  if (tier === 'full') return 'bg-blue-100 text-blue-700'
  if (tier === 'limited') return 'bg-gray-100 text-gray-600'
  return 'bg-gray-100 text-gray-600'
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function CategoryCard({
  title,
  assessment,
  renderDetails,
}: {
  title: string
  assessment: CategoryAssessment | null
  renderDetails?: (details: Record<string, unknown>) => React.ReactNode
}) {
  if (!assessment) {
    return (
      <div className="border border-gray-200 rounded-md p-4">
        <div className="flex items-center justify-between mb-1">
          <h4 className="font-medium text-gray-900">{title}</h4>
        </div>
        <p className="text-sm text-gray-400 italic">Not assessed (limited data)</p>
      </div>
    )
  }

  return (
    <div className="border border-gray-200 rounded-md p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-gray-900">{title}</h4>
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${scoreColorClass(assessment.score)}`}>
          Score: {fmtScore(assessment.score)}
        </span>
      </div>

      {assessment.confidence !== null && (
        <p className="text-sm text-gray-500 mb-2">
          Confidence: {fmtScore(assessment.confidence)}
        </p>
      )}

      {assessment.details && renderDetails && (
        <div className="text-sm text-gray-700 mb-2">{renderDetails(assessment.details)}</div>
      )}

      {assessment.reasoning && (
        <p className="text-sm text-gray-600 italic leading-relaxed">
          &ldquo;{assessment.reasoning}&rdquo;
        </p>
      )}
    </div>
  )
}

function TrlGapDetails({ details }: { details: Record<string, unknown> }) {
  const inventorTier = details.inventor_implied_tier as string | undefined
  const assessedTier = details.assessed_tier as string | undefined

  return (
    <div className="space-y-1">
      {inventorTier && (
        <p>
          <span className="text-gray-500">Inventor implies:</span>{' '}
          <span className="font-medium">{inventorTier}</span>
        </p>
      )}
      {assessedTier && (
        <p>
          <span className="text-gray-500">Assessed at:</span>{' '}
          <span className="font-medium">{assessedTier}</span>
        </p>
      )}
    </div>
  )
}

function FalseBarrierDetails({ details }: { details: Record<string, unknown> }) {
  const statedBarrier = details.stated_barrier as string | undefined
  const rebuttal = details.rebuttal as string | undefined

  return (
    <div className="space-y-1">
      {statedBarrier && (
        <p>
          <span className="text-gray-500">Stated barrier:</span>{' '}
          <span className="font-medium">{statedBarrier}</span>
        </p>
      )}
      {rebuttal && (
        <p>
          <span className="text-gray-500">Rebuttal:</span>{' '}
          <span>{rebuttal}</span>
        </p>
      )}
    </div>
  )
}

function AltApplicationDetails({ details }: { details: Record<string, unknown> }) {
  const original = details.original_application as string | undefined
  const suggested = details.suggested_applications as string[] | undefined

  return (
    <div className="space-y-1">
      {original && (
        <p>
          <span className="text-gray-500">Original:</span>{' '}
          <span className="font-medium">{original}</span>
        </p>
      )}
      {suggested && suggested.length > 0 && (
        <div>
          <span className="text-gray-500">Suggested:</span>{' '}
          {suggested.map((app, i) => (
            <span key={i}>
              <span className="font-medium">{app}</span>
              {i < suggested.length - 1 && ', '}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

interface Props {
  uuid: string
}

export function AssessmentSection({ uuid }: Props) {
  const [data, setData] = useState<OpportunitySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [assessing, setAssessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchAssessment = useCallback(async () => {
    setLoading(true)
    setError(null)
    setNotFound(false)
    try {
      const result = await opportunitiesApi.get(uuid)
      setData(result)
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setNotFound(true)
      } else {
        setError(e instanceof Error ? e.message : 'Failed to load assessment')
      }
    } finally {
      setLoading(false)
    }
  }, [uuid])

  useEffect(() => {
    fetchAssessment()
  }, [fetchAssessment])

  const handleAssess = async () => {
    setAssessing(true)
    setError(null)
    try {
      const result = await opportunitiesApi.assess(uuid)
      setData(result)
      setNotFound(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Assessment failed')
    } finally {
      setAssessing(false)
    }
  }

  // Loading skeleton
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4" />
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-3" />
        <div className="space-y-3">
          <div className="h-24 bg-gray-200 rounded" />
          <div className="h-24 bg-gray-200 rounded" />
          <div className="h-24 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  // Error state
  if (error && !data) {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    )
  }

  // No assessment available
  if (notFound) {
    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Opportunity Assessment</h3>
            <p className="text-sm text-gray-500 mt-1">No assessment available</p>
          </div>
          <button
            onClick={handleAssess}
            disabled={assessing}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {assessing && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {assessing ? 'Assessing...' : 'Assess'}
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Opportunity Assessment</h3>
        <div className="flex items-center gap-3">
          <button
            onClick={handleAssess}
            disabled={assessing}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {assessing && (
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {assessing ? 'Re-assessing...' : 'Re-assess'}
          </button>
          {data.assessment_tier && (
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${tierBadgeClass(data.assessment_tier)}`}>
              {data.assessment_tier} Tier
            </span>
          )}
        </div>
      </div>

      {/* Summary row */}
      <div className="flex items-center justify-between mb-5 pb-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">Composite Score:</span>
          <span className={`px-2.5 py-0.5 rounded-full text-sm font-semibold ${scoreColorClass(data.composite_score)}`}>
            {fmtScore(data.composite_score)}
          </span>
        </div>
        {data.assessed_at && (
          <span className="text-sm text-gray-500">
            Assessed: {formatDate(data.assessed_at)}
          </span>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded">
          {error}
        </div>
      )}

      {/* Category cards */}
      <div className="space-y-4">
        <CategoryCard
          title="TRL Gap"
          assessment={data.trl_gap}
          renderDetails={(details) => <TrlGapDetails details={details} />}
        />
        <CategoryCard
          title="False Barrier"
          assessment={data.false_barrier}
          renderDetails={(details) => <FalseBarrierDetails details={details} />}
        />
        <CategoryCard
          title="Alternative Application"
          assessment={data.alt_application}
          renderDetails={(details) => <AltApplicationDetails details={details} />}
        />
      </div>
    </div>
  )
}
