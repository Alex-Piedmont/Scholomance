import type { TechnologyDetail } from '../../api/types'
import type { ParsedRawData } from './parseRawData'
import {
  ResearchersSection,
  InventorsSection,
  DepartmentsSection,
  ContactsSection,
  ClassificationSection,
  KeywordsSection,
  TagsSection,
  DocumentsSection,
  ContactDetailSection,
  LicensingContactSection,
  RelatedPortfolioSection,
  SourceLinkSection,
} from './sections'

interface Props {
  tech: TechnologyDetail
  data: ParsedRawData
}

/**
 * DetailPage's sticky right-column composer. Each section renders itself or
 * null. DiscoveryDrawer imports the same sections but arranges them in a
 * single-column drawer flow (see AU-8).
 */
export function SidePanel({ tech, data }: Props) {
  return (
    <div className="lg:w-80 flex-shrink-0">
      <div className="bg-white rounded-lg shadow p-5 divide-y divide-gray-100 sticky top-6">
        <ResearchersSection tech={tech} data={data} />
        <InventorsSection tech={tech} data={data} />
        <DepartmentsSection tech={tech} data={data} />
        <ContactsSection tech={tech} data={data} />
        <ClassificationSection tech={tech} data={data} />
        <KeywordsSection tech={tech} data={data} />
        <TagsSection tech={tech} data={data} />
        <DocumentsSection tech={tech} data={data} />
        <ContactDetailSection tech={tech} data={data} />
        <LicensingContactSection tech={tech} data={data} />
        <RelatedPortfolioSection tech={tech} data={data} />
        <SourceLinkSection tech={tech} data={data} />
      </div>
    </div>
  )
}
