import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { TimelinePoint } from '../../api/types'

interface TimelineChartProps {
  data: TimelinePoint[] | null
  loading: boolean
}

export function TimelineChart({ data, loading }: TimelineChartProps) {
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
          Technologies Over Time
        </h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No timeline data available
        </div>
      </div>
    )
  }

  // Format month labels
  const chartData = data.map((item) => ({
    month: item.month,
    count: item.count,
    label: formatMonth(item.month),
  }))

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-medium text-gray-900 mb-4">
        Technologies Over Time
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value) => [Number(value).toLocaleString(), 'Technologies']}
              labelFormatter={(label) => `Month: ${label}`}
            />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function formatMonth(month: string): string {
  const [year, m] = month.split('-')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${months[parseInt(m, 10) - 1]} ${year.slice(2)}`
}
