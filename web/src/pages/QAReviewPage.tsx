import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Header } from '../components/Layout'
import { ErrorMessage } from '../components/common'
import { technologiesApi } from '../api/client'
import type { TechnologyDetail } from '../api/types'

// Fields to skip in QA review (internal/structural, not page content)
const SKIP_FIELDS = new Set([
  'id', 'uuid', 'url', 'source_page', 'tech_id',
  '_members', '_documents', '_contacts', '_tags',
])

type FieldStatus = 'unchecked' | 'correct' | 'incorrect'

interface FieldState {
  status: FieldStatus
  editedValue: string
}

function formatFieldName(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map((v) => (typeof v === 'object' ? JSON.stringify(v) : String(v))).join('\n')
  }
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function isSimpleArray(value: unknown): boolean {
  return Array.isArray(value) && value.length > 0 && typeof value[0] !== 'object'
}

/** Render a simple string array as a bulleted list */
function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc list-inside space-y-0.5">
      {items.map((item, i) => (
        <li key={i}>{item.replace(/^-\s*/, '')}</li>
      ))}
    </ul>
  )
}

/** Toggle bullet prefix on each line of a textarea value */
function toggleBullets(text: string): string {
  const lines = text.split('\n').filter(Boolean)
  const allBulleted = lines.every((l) => l.startsWith('- '))
  if (allBulleted) {
    return lines.map((l) => l.replace(/^- /, '')).join('\n')
  }
  return lines.map((l) => (l.startsWith('- ') ? l : `- ${l}`)).join('\n')
}

function isComplexValue(value: unknown): boolean {
  if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object') return true
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) return true
  return false
}

export function QAReviewPage() {
  const { uuid } = useParams<{ uuid: string }>()
  const navigate = useNavigate()

  const [tech, setTech] = useState<TechnologyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [iframeError, setIframeError] = useState(false)

  // Field states keyed by field name
  const [fieldStates, setFieldStates] = useState<Record<string, FieldState>>({})

  // Sibling navigation
  const [siblings, setSiblings] = useState<string[]>([])
  const [siblingIndex, setSiblingIndex] = useState(-1)

  const fetchTech = useCallback(async () => {
    if (!uuid) return
    setLoading(true)
    setError(null)
    try {
      const data = await technologiesApi.get(uuid)
      setTech(data)
      // Initialize field states
      const rawData = data.raw_data || {}
      const states: Record<string, FieldState> = {}
      for (const key of Object.keys(rawData)) {
        if (!SKIP_FIELDS.has(key)) {
          states[key] = { status: 'unchecked', editedValue: formatValue(rawData[key]) }
        }
      }
      setFieldStates(states)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [uuid])

  useEffect(() => {
    fetchTech()
  }, [fetchTech])

  // Load sibling list from session storage for prev/next nav
  useEffect(() => {
    const stored = sessionStorage.getItem('qa-siblings')
    if (stored) {
      const list = JSON.parse(stored) as string[]
      setSiblings(list)
      if (uuid) setSiblingIndex(list.indexOf(uuid))
    }
  }, [uuid])

  const updateFieldStatus = (key: string, status: FieldStatus) => {
    setFieldStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], status },
    }))
  }

  const updateFieldValue = (key: string, value: string) => {
    setFieldStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], editedValue: value },
    }))
  }

  const handleSave = async () => {
    if (!uuid || !tech) return

    // Collect fields marked incorrect with edited values
    const updates: Record<string, unknown> = {}
    for (const [key, state] of Object.entries(fieldStates)) {
      if (state.status === 'incorrect') {
        const originalValue = tech.raw_data?.[key]
        // Try to preserve the original type
        if (Array.isArray(originalValue) && !isComplexValue(originalValue)) {
          updates[key] = state.editedValue.split('\n').filter(Boolean)
        } else {
          updates[key] = state.editedValue
        }
      }
    }

    if (Object.keys(updates).length === 0) {
      setSaveMessage('No corrections to save')
      setTimeout(() => setSaveMessage(null), 2000)
      return
    }

    setSaving(true)
    setSaveMessage(null)
    try {
      const updated = await technologiesApi.patchRawData(uuid, updates)
      setTech(updated)
      // Reset corrected fields to "correct" status
      setFieldStates((prev) => {
        const next = { ...prev }
        for (const key of Object.keys(updates)) {
          if (next[key]) {
            next[key] = { ...next[key], status: 'correct' }
          }
        }
        return next
      })
      setSaveMessage(`Saved ${Object.keys(updates).length} correction(s)`)
    } catch (e: unknown) {
      setSaveMessage(`Error: ${e instanceof Error ? e.message : 'Save failed'}`)
    } finally {
      setSaving(false)
      setTimeout(() => setSaveMessage(null), 3000)
    }
  }

  const navigateSibling = (direction: -1 | 1) => {
    const newIndex = siblingIndex + direction
    if (newIndex >= 0 && newIndex < siblings.length) {
      navigate(`/qa/${siblings[newIndex]}`)
    }
  }

  if (loading) {
    return (
      <div>
        <Header title="QA Review" />
        <div className="p-6 text-center text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error || !tech) {
    return (
      <div>
        <Header title="QA Review" />
        <div className="p-6">
          <ErrorMessage message={error || 'Technology not found'} />
        </div>
      </div>
    )
  }

  const rawData = tech.raw_data || {}
  const fieldKeys = Object.keys(rawData).filter((k) => !SKIP_FIELDS.has(k))
  const proxyUrl = technologiesApi.getProxyUrl(tech.url)

  const checkedCount = Object.values(fieldStates).filter((s) => s.status !== 'unchecked').length
  const incorrectCount = Object.values(fieldStates).filter((s) => s.status === 'incorrect').length

  return (
    <div className="flex flex-col h-full">
      <Header title="QA Review" />

      {/* Top bar with tech info and navigation */}
      <div className="px-6 py-3 bg-white border-b border-gray-200 flex items-center justify-between flex-shrink-0">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-gray-900 truncate">{tech.title}</h2>
          <p className="text-xs text-gray-500">
            {tech.university} / {tech.tech_id}
          </p>
        </div>
        <div className="flex items-center gap-2 ml-4 flex-shrink-0">
          <span className="text-xs text-gray-500">
            {checkedCount}/{fieldKeys.length} reviewed
            {incorrectCount > 0 && ` (${incorrectCount} corrected)`}
          </span>
          {siblings.length > 0 && (
            <>
              <button
                onClick={() => navigateSibling(-1)}
                disabled={siblingIndex <= 0}
                className="px-2 py-1 text-xs border rounded disabled:opacity-30 hover:bg-gray-50"
              >
                Prev
              </button>
              <span className="text-xs text-gray-400">
                {siblingIndex + 1}/{siblings.length}
              </span>
              <button
                onClick={() => navigateSibling(1)}
                disabled={siblingIndex >= siblings.length - 1}
                className="px-2 py-1 text-xs border rounded disabled:opacity-30 hover:bg-gray-50"
              >
                Next
              </button>
            </>
          )}
          <button
            onClick={() => navigate(`/qa?university=${tech.university}`)}
            className="px-3 py-1.5 text-xs border rounded hover:bg-gray-50"
          >
            Back to List
          </button>
        </div>
      </div>

      {/* Main content: side-by-side */}
      <div className="flex flex-1 min-h-0">
        {/* Left panel: fields */}
        <div className="w-2/5 border-r border-gray-200 overflow-y-auto bg-gray-50">
          <div className="p-4 space-y-3">
            {fieldKeys.map((key) => {
              const value = rawData[key]
              const state = fieldStates[key]
              if (!state) return null

              const isComplex = isComplexValue(value)

              return (
                <div key={key} className="bg-white rounded-lg border border-gray-200 p-3">
                  {/* Field header */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-700">
                      {formatFieldName(key)}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => updateFieldStatus(key, 'correct')}
                        className={`px-2 py-0.5 text-xs rounded transition-colors ${
                          state.status === 'correct'
                            ? 'bg-green-100 text-green-800 font-medium'
                            : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                        }`}
                        title="Mark correct"
                      >
                        OK
                      </button>
                      <button
                        onClick={() => updateFieldStatus(key, 'incorrect')}
                        className={`px-2 py-0.5 text-xs rounded transition-colors ${
                          state.status === 'incorrect'
                            ? 'bg-red-100 text-red-800 font-medium'
                            : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                        }`}
                        title="Mark incorrect"
                      >
                        Fix
                      </button>
                    </div>
                  </div>

                  {/* Current value */}
                  <div className="text-xs text-gray-600 whitespace-pre-wrap break-words max-h-32 overflow-y-auto bg-gray-50 rounded p-2">
                    {isComplex ? (
                      <pre className="text-xs">{JSON.stringify(value, null, 2)}</pre>
                    ) : isSimpleArray(value) ? (
                      <BulletList items={(value as string[])} />
                    ) : (
                      formatValue(value) || <span className="italic text-gray-400">empty</span>
                    )}
                  </div>

                  {/* Edit area when marked incorrect */}
                  {state.status === 'incorrect' && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs text-red-600 font-medium">
                          Corrected value:
                        </label>
                        <button
                          type="button"
                          onClick={() => updateFieldValue(key, toggleBullets(state.editedValue))}
                          className="px-1.5 py-0.5 text-xs text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded"
                          title="Toggle bullet points on each line"
                        >
                          Toggle bullets
                        </button>
                      </div>
                      <textarea
                        value={state.editedValue}
                        onChange={(e) => updateFieldValue(key, e.target.value)}
                        rows={4}
                        className="w-full text-xs border border-red-300 rounded p-2 focus:outline-none focus:ring-1 focus:ring-red-500"
                      />
                    </div>
                  )}
                </div>
              )
            })}

            {fieldKeys.length === 0 && (
              <div className="text-sm text-gray-500 text-center py-8">
                No raw_data fields to review
              </div>
            )}
          </div>

          {/* Save button */}
          {incorrectCount > 0 && (
            <div className="sticky bottom-0 p-4 bg-white border-t border-gray-200">
              <button
                onClick={handleSave}
                disabled={saving}
                className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : `Save ${incorrectCount} Correction(s)`}
              </button>
              {saveMessage && (
                <p className={`mt-2 text-xs text-center ${saveMessage.startsWith('Error') ? 'text-red-600' : 'text-green-600'}`}>
                  {saveMessage}
                </p>
              )}
            </div>
          )}

          {saveMessage && incorrectCount === 0 && (
            <div className="p-4 text-xs text-center text-green-600">{saveMessage}</div>
          )}
        </div>

        {/* Right panel: source page */}
        <div className="w-3/5 flex flex-col bg-white">
          <div className="px-4 py-2 border-b border-gray-200 flex items-center justify-between bg-gray-50">
            <span className="text-xs text-gray-500 truncate flex-1">{tech.url}</span>
            <a
              href={tech.url}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-2 px-2 py-1 text-xs text-blue-600 hover:text-blue-800 flex-shrink-0"
            >
              Open in tab
            </a>
          </div>

          {!iframeError ? (
            <iframe
              src={proxyUrl}
              className="flex-1 w-full"
              title="Source page"
              sandbox="allow-same-origin"
              onError={() => setIframeError(true)}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <p className="text-sm mb-2">Could not load source page</p>
                <a
                  href={tech.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  Open in new tab
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
