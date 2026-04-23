import {
  TextSection,
  BulletSection,
  CheckmarkListSection,
  ContentSectionWrapper,
} from './primitives'
import { stripHtml } from '../parseRawData'
import type { SectionProps } from './types'

/** Italic subtitle inline (no heading). Tagged with data-section for tests. */
export function SubtitleSection({ data }: SectionProps) {
  if (!data.subtitle) return null
  return (
    <p data-section="subtitle" className="text-lg text-gray-600 italic mb-2">
      {data.subtitle}
    </p>
  )
}

export function SummarySection({ data }: SectionProps) {
  return <TextSection title="Summary" text={data.shortDescription} />
}

export function AbstractSection({ data }: SectionProps) {
  return (
    <TextSection
      title="Abstract"
      text={data.abstractText ? stripHtml(data.abstractText) : undefined}
    />
  )
}

export function OverviewSection({ data }: SectionProps) {
  return (
    <TextSection
      title="Overview"
      text={data.otherHtml ? stripHtml(data.otherHtml) : undefined}
    />
  )
}

/**
 * Description falls back from top-level `tech.description` ONLY when no
 * higher-priority content block rendered. ContentSections orchestrates the
 * suppression by passing `showFallback=false` when it has already emitted a
 * Summary/Abstract/Overview. When rendered standalone (in the drawer flat
 * flow), `showFallback` defaults to true.
 */
export function DescriptionSection({
  tech,
  data,
  showFallback = true,
}: SectionProps & { showFallback?: boolean }) {
  const hasHigherPriority =
    !!(data.otherHtml || data.abstractText || data.shortDescription)
  if (hasHigherPriority || !tech.description) {
    return showFallback ? null : null
  }
  return (
    <TextSection
      title="Description"
      text={tech.description.replace(/\r\r/g, '\n\n').replace(/\r/g, '\n')}
    />
  )
}

export function TechnicalProblemSection({ data }: SectionProps) {
  return <TextSection title="Technical Problem" text={data.technicalProblem} />
}

export function SolutionSection({ data }: SectionProps) {
  return <TextSection title="Solution" text={data.solutionText} />
}

export function BackgroundSection({ data }: SectionProps) {
  return <TextSection title="Background" text={data.background} />
}

export function FullDescriptionSection({ data }: SectionProps) {
  return <TextSection title="Full Description" text={data.fullDescription} />
}

export function BenefitsSection({ data }: SectionProps) {
  return (
    <TextSection
      title="Benefits"
      text={data.benefitHtml ? stripHtml(data.benefitHtml) : undefined}
    />
  )
}

export function MarketOpportunitySection({ data }: SectionProps) {
  if (!data.marketApplicationHtml && !data.marketOpportunity) return null
  return (
    <TextSection
      title="Market Opportunity"
      text={
        data.marketApplicationHtml
          ? stripHtml(data.marketApplicationHtml)
          : data.marketOpportunity
      }
    />
  )
}

export function DevelopmentStageSection({ data }: SectionProps) {
  return <TextSection title="Development Stage" text={data.developmentStage} />
}

export function TrlSection({ data }: SectionProps) {
  return <TextSection title="Technology Readiness Level" text={data.trl} />
}

export function KeyPointsSection({ data }: SectionProps) {
  if (data.keyPoints && data.keyPoints.length > 0) {
    return <BulletSection title="Key Points" items={data.keyPoints} />
  }
  if (data.keyPointsText) {
    return <TextSection title="Key Points" text={data.keyPointsText} />
  }
  return null
}

export function ApplicationsSection({ data }: SectionProps) {
  if (data.applications && data.applications.length > 0) {
    return <BulletSection title="Applications" items={data.applications} color="green" />
  }
  if (data.applicationsText) {
    return <TextSection title="Applications" text={data.applicationsText} />
  }
  return null
}

export function AdvantagesSection({ data }: SectionProps) {
  if (data.advantages && data.advantages.length > 0) {
    return <CheckmarkListSection title="Advantages" items={data.advantages} />
  }
  if (data.advantagesText) {
    return <TextSection title="Advantages" text={data.advantagesText} />
  }
  return null
}

export function TechnologyValidationSection({ data }: SectionProps) {
  if (data.technologyValidation && data.technologyValidation.length > 0) {
    return <BulletSection title="Technology Validation" items={data.technologyValidation} />
  }
  if (data.technologyValidationText) {
    return <TextSection title="Technology Validation" text={data.technologyValidationText} />
  }
  return null
}

export function PublicationsSection({ data }: SectionProps) {
  if (data.publicationsList && data.publicationsList.length > 0) {
    return (
      <ContentSectionWrapper title="Publications">
        <ul className="space-y-2">
          {data.publicationsList.map((pub, i) => (
            <li key={i} className="text-gray-700 text-sm">
              {pub.url ? (
                <a
                  href={pub.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  {pub.text || pub.url}
                </a>
              ) : (
                <span>{pub.text}</span>
              )}
            </li>
          ))}
        </ul>
      </ContentSectionWrapper>
    )
  }
  if (data.publicationsHtml) {
    return (
      <ContentSectionWrapper title="Publications">
        {data.publicationsHtml.includes('<') ? (
          <div
            className="text-gray-700 leading-relaxed prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: data.publicationsHtml }}
          />
        ) : (
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {data.publicationsHtml}
          </p>
        )}
      </ContentSectionWrapper>
    )
  }
  return null
}

export function IpStatusSection({ data }: SectionProps) {
  const { ipStatusText, ipNumber, ipUrl, ipText } = data
  if (!ipStatusText && !ipNumber && !ipText) return null
  return (
    <ContentSectionWrapper title="IP Status">
      {ipStatusText && (
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{ipStatusText}</p>
      )}
      {ipNumber && (
        <p className="text-gray-700 mt-2">
          <span className="font-medium">Patent: </span>
          {ipUrl ? (
            <a
              href={ipUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline"
            >
              {ipNumber}
            </a>
          ) : (
            <span>{ipNumber}</span>
          )}
        </p>
      )}
      {ipText && <p className="text-gray-700 mt-2 whitespace-pre-wrap">{ipText}</p>}
    </ContentSectionWrapper>
  )
}

export function NoContentNotice({ tech, data }: SectionProps) {
  const hasNoContent =
    !tech.description &&
    !data.otherHtml &&
    !data.abstractText &&
    !data.shortDescription &&
    !data.benefitHtml &&
    !data.marketApplicationHtml &&
    !data.marketOpportunity &&
    !data.publicationsHtml &&
    !data.background &&
    !data.fullDescription &&
    (!data.keyPoints || data.keyPoints.length === 0) &&
    (!data.applications || data.applications.length === 0) &&
    (!data.advantages || data.advantages.length === 0)
  if (!hasNoContent) return null
  return (
    <p className="text-gray-500 italic">No description available for this technology.</p>
  )
}
