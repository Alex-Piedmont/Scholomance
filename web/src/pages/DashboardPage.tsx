import { Header } from '../components/Layout'
import {
  OverviewCards,
  FieldChart,
  UniversityChart,
  TimelineChart,
} from '../components/Dashboard'
import { ErrorMessage } from '../components/common'
import {
  useStatsOverview,
  useStatsByField,
  useStatsByUniversity,
  useStatsTimeline,
} from '../hooks'

export function DashboardPage() {
  const { data: stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useStatsOverview()
  const { data: fieldData, loading: fieldLoading, error: fieldError, refetch: refetchField } = useStatsByField()
  const { data: uniData, loading: uniLoading, error: uniError, refetch: refetchUni } = useStatsByUniversity()
  const { data: timelineData, loading: timelineLoading, error: timelineError, refetch: refetchTimeline } = useStatsTimeline()

  const hasError = statsError || fieldError || uniError || timelineError

  if (hasError && !stats && !fieldData && !uniData && !timelineData) {
    return (
      <div>
        <Header title="Dashboard" />
        <div className="p-6">
          <ErrorMessage
            message="Failed to load dashboard data. Please check your connection."
            onRetry={() => {
              refetchStats()
              refetchField()
              refetchUni()
              refetchTimeline()
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div>
      <Header title="Dashboard" />

      <div className="p-6">
        <OverviewCards stats={stats} loading={statsLoading} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <FieldChart data={fieldData} loading={fieldLoading} />
          <UniversityChart data={uniData} loading={uniLoading} />
        </div>

        <TimelineChart data={timelineData} loading={timelineLoading} />
      </div>
    </div>
  )
}
