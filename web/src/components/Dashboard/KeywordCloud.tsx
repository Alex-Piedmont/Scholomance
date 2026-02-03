import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import type { KeywordCount } from '../../api/types'

interface KeywordCloudProps {
  data: KeywordCount[] | null
  loading: boolean
}

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
]

export function KeywordCloud({ data, loading }: KeywordCloudProps) {
  const navigate = useNavigate()

  const words = useMemo(() => {
    if (!data || data.length === 0) return []
    const max = data[0].count
    const min = data[data.length - 1].count
    const range = max - min || 1
    return data.map((item, i) => ({
      keyword: item.keyword,
      count: item.count,
      fontSize: 12 + ((item.count - min) / range) * 24,
      color: COLORS[i % COLORS.length],
    }))
  }, [data])

  if (loading) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="h-4 bg-gray-200 rounded w-40 mb-4" />
        <div className="h-64 bg-gray-100 rounded animate-pulse" />
      </div>
    )
  }

  if (words.length === 0) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Keywords</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No keyword data available
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Keywords</h3>
      <div className="h-64 overflow-auto flex flex-wrap items-center justify-center gap-x-3 gap-y-1 px-2">
        {words.map((w) => (
          <button
            key={w.keyword}
            onClick={() => navigate(`/browse?q=${encodeURIComponent(w.keyword)}`)}
            className="hover:opacity-70 transition-opacity cursor-pointer"
            style={{ fontSize: `${w.fontSize}px`, color: w.color, lineHeight: 1.3 }}
            title={`${w.keyword} (${w.count})`}
          >
            {w.keyword}
          </button>
        ))}
      </div>
    </div>
  )
}
