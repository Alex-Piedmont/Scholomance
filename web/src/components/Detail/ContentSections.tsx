import type { TechnologyDetail } from '../../api/types'
import type { ParsedRawData } from './parseRawData'
import { stripHtml } from './parseRawData'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="py-5 border-b border-gray-100 last:border-b-0">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">{title}</h2>
      {children}
    </div>
  )
}

function TextSection({ title, text }: { title: string; text?: string }) {
  if (!text) return null
  return (
    <Section title={title}>
      <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{text}</p>
    </Section>
  )
}

function BulletSection({ title, items, color = 'blue' }: { title: string; items: string[]; color?: string }) {
  if (!items.length) return null
  const dotClass = color === 'green' ? 'text-green-500' : 'text-blue-500'
  return (
    <Section title={title}>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-gray-700">
            <span className={`${dotClass} mt-1 flex-shrink-0`}>•</span>
            <span>{item.replace(/\r\r/g, ' ').replace(/\r/g, ' ')}</span>
          </li>
        ))}
      </ul>
    </Section>
  )
}

interface Props {
  tech: TechnologyDetail
  data: ParsedRawData
}

export function ContentSections({ tech, data }: Props) {
  const {
    subtitle, shortDescription, abstractText, otherHtml, technicalProblem,
    solutionText, background, benefitHtml, marketApplicationHtml, marketOpportunity,
    developmentStage, keyPoints, applications, applicationsText, advantages,
    advantagesText, technologyValidation, publicationsList, publicationsHtml,
    ipStatusText, ipNumber, ipUrl, ipText, fullDescription,
  } = data

  const hasNoContent = !tech.description && !otherHtml && !abstractText && !shortDescription &&
    !benefitHtml && !marketApplicationHtml && !marketOpportunity &&
    !publicationsHtml && !background && !fullDescription &&
    (!keyPoints || keyPoints.length === 0) &&
    (!applications || applications.length === 0) &&
    (!advantages || advantages.length === 0)

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {subtitle && (
        <p className="text-lg text-gray-600 italic mb-2">{subtitle}</p>
      )}

      <TextSection title="Summary" text={shortDescription} />
      <TextSection title="Abstract" text={abstractText ? stripHtml(abstractText) : undefined} />
      <TextSection title="Overview" text={otherHtml ? stripHtml(otherHtml) : undefined} />

      {!otherHtml && !abstractText && !shortDescription && tech.description && (
        <TextSection
          title="Description"
          text={tech.description.replace(/\r\r/g, '\n\n').replace(/\r/g, '\n')}
        />
      )}

      <TextSection title="Technical Problem" text={technicalProblem} />
      <TextSection title="Solution" text={solutionText} />
      <TextSection title="Background" text={background} />
      <TextSection title="Benefits" text={benefitHtml ? stripHtml(benefitHtml) : undefined} />

      {(marketApplicationHtml || marketOpportunity) && (
        <TextSection
          title="Market Opportunity"
          text={marketApplicationHtml ? stripHtml(marketApplicationHtml) : marketOpportunity}
        />
      )}

      <TextSection title="Development Stage" text={developmentStage} />

      {keyPoints && keyPoints.length > 0 && (
        <BulletSection title="Key Points" items={keyPoints} />
      )}

      {applications && applications.length > 0 && (
        <BulletSection title="Applications" items={applications} color="green" />
      )}

      {!applications?.length && applicationsText && (
        <TextSection title="Applications" text={applicationsText} />
      )}

      {advantages && advantages.length > 0 && (
        <Section title="Advantages">
          <ul className="space-y-2">
            {advantages.map((adv, i) => (
              <li key={i} className="flex gap-2 text-gray-700">
                <span className="text-green-500 mt-1 flex-shrink-0">✓</span>
                <span>{adv}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {technologyValidation && technologyValidation.length > 0 && (
        <BulletSection title="Technology Validation" items={technologyValidation} />
      )}

      {!advantages?.length && advantagesText && (
        <TextSection title="Advantages" text={advantagesText} />
      )}

      {publicationsList && publicationsList.length > 0 && (
        <Section title="Publications">
          <ul className="space-y-2">
            {publicationsList.map((pub, i) => (
              <li key={i} className="text-gray-700 text-sm">
                {pub.url ? (
                  <a href={pub.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {pub.text || pub.url}
                  </a>
                ) : (
                  <span>{pub.text}</span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {!publicationsList?.length && publicationsHtml && (
        <Section title="Publications">
          {publicationsHtml.includes('<') ? (
            <div
              className="text-gray-700 leading-relaxed prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: publicationsHtml }}
            />
          ) : (
            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
              {publicationsHtml}
            </p>
          )}
        </Section>
      )}

      {(ipStatusText || ipNumber || ipText) && (
        <Section title="IP Status">
          {ipStatusText && (
            <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{ipStatusText}</p>
          )}
          {ipNumber && (
            <p className="text-gray-700 mt-2">
              <span className="font-medium">Patent: </span>
              {ipUrl ? (
                <a href={ipUrl} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  {ipNumber}
                </a>
              ) : (
                <span>{ipNumber}</span>
              )}
            </p>
          )}
          {ipText && (
            <p className="text-gray-700 mt-2 whitespace-pre-wrap">{ipText}</p>
          )}
        </Section>
      )}

      {hasNoContent && (
        <p className="text-gray-500 italic">No description available for this technology.</p>
      )}
    </div>
  )
}
