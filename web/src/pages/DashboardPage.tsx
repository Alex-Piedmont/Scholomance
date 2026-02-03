import { Header } from '../components/Layout'
import {
  OverviewCards,
  KeywordCloud,
  UniversityChart,
  TimelineChart,
} from '../components/Dashboard'
import { ErrorMessage } from '../components/common'
import {
  useStatsOverview,
  useStatsKeywords,
  useStatsByUniversity,
  useStatsTimeline,
} from '../hooks'

export function DashboardPage() {
  const { data: stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useStatsOverview()
  const { data: keywordData, loading: keywordLoading, error: keywordError, refetch: refetchKeywords } = useStatsKeywords()
  const { data: uniData, loading: uniLoading, error: uniError, refetch: refetchUni } = useStatsByUniversity()
  const { data: timelineData, loading: timelineLoading, error: timelineError, refetch: refetchTimeline } = useStatsTimeline()

  const hasError = statsError || keywordError || uniError || timelineError

  if (hasError && !stats && !keywordData && !uniData && !timelineData) {
    return (
      <div>
        <Header title="Dashboard" />
        <div className="p-6">
          <ErrorMessage
            message="Failed to load dashboard data. Please check your connection."
            onRetry={() => {
              refetchStats()
              refetchKeywords()
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
          <KeywordCloud data={keywordData} loading={keywordLoading} />
          <UniversityChart data={uniData} loading={uniLoading} />
        </div>

        <TimelineChart data={timelineData} loading={timelineLoading} />
      </div>
    </div>
  )
}
