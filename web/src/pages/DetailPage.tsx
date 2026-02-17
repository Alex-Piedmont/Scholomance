import { useEffect, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { Header } from '../components/Layout'
import { useTechnology } from '../hooks'
import { parseRawData } from '../components/Detail/parseRawData'
import { ContentSections } from '../components/Detail/ContentSections'
import { AssessmentSection } from '../components/Detail/AssessmentSection'
import { SidePanel } from '../components/Detail/SidePanel'
import { getUniversityName } from '../utils/universityNames'

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

  const data = parseRawData(tech)

  const formatPatentStatus = (status: string | null) => {
    if (!status || status === 'unknown') return 'Unknown'
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const dateFmt = { year: 'numeric' as const, month: 'long' as const, day: 'numeric' as const }

  const publishedRaw = data.publishedOn || data.webPublished
  const publishedDate = publishedRaw
    ? new Date(publishedRaw).toLocaleDateString('en-US', dateFmt)
    : null

  const updatedDate = (tech.updated_at || tech.scraped_at)
    ? new Date((tech.updated_at || tech.scraped_at)!).toLocaleDateString('en-US', dateFmt)
    : null

  const patentColorClass =
    tech.patent_status === 'granted' ? 'bg-green-100 text-green-700' :
    tech.patent_status === 'pending' || tech.patent_status === 'filed' ? 'bg-yellow-100 text-yellow-700' :
    'bg-gray-100 text-gray-600'

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
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{tech.title}</h1>

        {/* Subheader */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600 mb-8">
          <span className="font-medium">{getUniversityName(tech.university)}</span>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${patentColorClass}`}>
            {formatPatentStatus(tech.patent_status)}
          </span>
          {data.docketNumber && (
            <>
              <span className="text-gray-300">|</span>
              <span>Docket: {data.docketNumber}</span>
            </>
          )}
          {data.technologyNumber && (
            <>
              <span className="text-gray-300">|</span>
              <span>Tech No. {data.technologyNumber}</span>
            </>
          )}
          {data.trl && (
            <>
              <span className="text-gray-300">|</span>
              <span>TRL: {data.trl}</span>
            </>
          )}
          {publishedDate && (
            <>
              <span className="text-gray-300">|</span>
              <span>Published {publishedDate}</span>
            </>
          )}
          {updatedDate && (
            <>
              <span className="text-gray-300">|</span>
              <span>Updated {updatedDate}</span>
            </>
          )}
        </div>

        {/* Two Column Layout */}
        <div className="flex flex-col lg:flex-row gap-8">
          <div className="flex-1 min-w-0 max-w-3xl">
            <AssessmentSection uuid={tech.uuid} />
            <ContentSections tech={tech} data={data} />
          </div>
          <SidePanel tech={tech} data={data} />
        </div>
      </div>
    </div>
  )
}
