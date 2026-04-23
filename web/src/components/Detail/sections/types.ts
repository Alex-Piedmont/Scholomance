import type { ReactElement } from 'react'
import type { TechnologyDetail } from '../../../api/types'
import type { ParsedRawData } from '../parseRawData'

/**
 * Uniform prop contract for every section component. Each component
 * owns its own "should I render?" check and returns null when there is
 * nothing to show. This lets DetailPage and DiscoveryDrawer compose the
 * same components in different layouts without the composer needing to
 * know which sections apply to a given record.
 */
export interface SectionProps {
  tech: TechnologyDetail
  data: ParsedRawData
}

export type SectionComponent = (props: SectionProps) => ReactElement | null
