import type { TechnologyDetail } from '../../api/types'
import type { ParsedRawData } from './parseRawData'
import {
  SubtitleSection,
  SummarySection,
  AbstractSection,
  OverviewSection,
  DescriptionSection,
  TechnicalProblemSection,
  SolutionSection,
  BackgroundSection,
  FullDescriptionSection,
  BenefitsSection,
  MarketOpportunitySection,
  DevelopmentStageSection,
  TrlSection,
  KeyPointsSection,
  ApplicationsSection,
  AdvantagesSection,
  TechnologyValidationSection,
  PublicationsSection,
  IpStatusSection,
  NoContentNotice,
} from './sections'

interface Props {
  tech: TechnologyDetail
  data: ParsedRawData
}

/**
 * DetailPage's main-content composer. Each section renders itself or null.
 * DiscoveryDrawer imports the same underlying sections but arranges them
 * in a single-column drawer flow (see AU-8).
 */
export function ContentSections({ tech, data }: Props) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <SubtitleSection tech={tech} data={data} />
      <SummarySection tech={tech} data={data} />
      <AbstractSection tech={tech} data={data} />
      <OverviewSection tech={tech} data={data} />
      <DescriptionSection tech={tech} data={data} />
      <TechnicalProblemSection tech={tech} data={data} />
      <SolutionSection tech={tech} data={data} />
      <BackgroundSection tech={tech} data={data} />
      <FullDescriptionSection tech={tech} data={data} />
      <BenefitsSection tech={tech} data={data} />
      <MarketOpportunitySection tech={tech} data={data} />
      <DevelopmentStageSection tech={tech} data={data} />
      <TrlSection tech={tech} data={data} />
      <KeyPointsSection tech={tech} data={data} />
      <ApplicationsSection tech={tech} data={data} />
      <AdvantagesSection tech={tech} data={data} />
      <TechnologyValidationSection tech={tech} data={data} />
      <PublicationsSection tech={tech} data={data} />
      <IpStatusSection tech={tech} data={data} />
      <NoContentNotice tech={tech} data={data} />
    </div>
  )
}
