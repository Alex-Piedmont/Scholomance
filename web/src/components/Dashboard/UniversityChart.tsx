import { useNavigate } from 'react-router-dom'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { UniversityCount } from '../../api/types'

interface UniversityChartProps {
  data: UniversityCount[] | null
  loading: boolean
}

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
]

export function UniversityChart({ data, loading }: UniversityChartProps) {
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
          Technologies by University
        </h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No data available
        </div>
      </div>
    )
  }

  // Take top 8 and group the rest as "Other"
  const top = data.slice(0, 8)
  const rest = data.slice(8)
  const otherCount = rest.reduce((sum, item) => sum + item.count, 0)

  const chartData = [
    ...top.map((item) => ({
      name: item.university,
      value: item.count,
    })),
    ...(otherCount > 0 ? [{ name: 'Other', value: otherCount }] : []),
  ]

  const handleClick = (data: { name: string }) => {
    if (data.name !== 'Other') {
      navigate(`/browse?university=${encodeURIComponent(data.name)}`)
    }
  }

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Technologies by University
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={80}
              dataKey="value"
              cursor="pointer"
              onClick={(data) => handleClick(data)}
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [Number(value).toLocaleString(), name]}
            />
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              formatter={(value) => (
                <span className="text-xs text-gray-600">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-400 mt-2">Click a slice to filter</p>
    </div>
  )
}
