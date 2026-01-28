import { useNavigate } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { FieldCount } from '../../api/types'

interface FieldChartProps {
  data: FieldCount[] | null
  loading: boolean
}

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
  '#14b8a6', '#a855f7',
]

export function FieldChart({ data, loading }: FieldChartProps) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="h-4 bg-gray-200 rounded w-40 mb-4" />
        <div className="h-64 bg-gray-100 rounded animate-pulse" />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Technologies by Field
        </h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No classified technologies yet
        </div>
      </div>
    )
  }

  const chartData = data.slice(0, 10).map((item) => ({
    name: item.top_field,
    count: item.count,
  }))

  const handleClick = (data: { name: string }) => {
    navigate(`/browse?top_field=${encodeURIComponent(data.name)}`)
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Technologies by Field
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
            <XAxis type="number" />
            <YAxis
              type="category"
              dataKey="name"
              width={100}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              formatter={(value) => [Number(value).toLocaleString(), 'Technologies']}
            />
            <Bar
              dataKey="count"
              cursor="pointer"
              onClick={(data) => data.name && handleClick({ name: data.name })}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-400 mt-2">Click a bar to filter</p>
    </div>
  )
}
