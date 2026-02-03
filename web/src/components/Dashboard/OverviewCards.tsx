import type { StatsOverview } from '../../api/types'

interface OverviewCardsProps {
  stats: StatsOverview | null
  loading: boolean
}

export function OverviewCards({ stats, loading }: OverviewCardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white p-4 rounded-lg shadow animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-2" />
            <div className="h-8 bg-gray-200 rounded w-20" />
          </div>
        ))}
      </div>
    )
  }

  if (!stats) return null

  const cards = [
    {
      label: 'Total Technologies',
      value: stats.total_technologies.toLocaleString(),
      color: 'text-blue-600',
    },
    {
      label: 'Universities',
      value: stats.total_universities.toString(),
      color: 'text-green-600',
    },
    {
      label: 'Granted Patents',
      value: stats.granted_patents.toLocaleString(),
      color: 'text-purple-600',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
      {cards.map((card) => (
        <div key={card.label} className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm text-gray-500">{card.label}</p>
          <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  )
}
