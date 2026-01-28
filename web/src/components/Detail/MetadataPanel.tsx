import type { TechnologyDetail } from '../../api/types'

interface MetadataPanelProps {
  tech: TechnologyDetail
}

export function MetadataPanel({ tech }: MetadataPanelProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Classification */}
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-2">Classification</h3>
        <div className="space-y-2">
          {tech.top_field ? (
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">
                {tech.top_field}
              </span>
              {tech.subfield && (
                <>
                  <span className="text-gray-400">/</span>
                  <span className="px-2 py-1 bg-blue-50 text-blue-700 text-sm rounded">
                    {tech.subfield}
                  </span>
                </>
              )}
            </div>
          ) : (
            <span className="text-gray-400 text-sm">Not classified</span>
          )}
          {tech.classification_confidence && (
            <p className="text-xs text-gray-500">
              Confidence: {(Number(tech.classification_confidence) * 100).toFixed(0)}%
            </p>
          )}
        </div>
      </div>

      {/* Dates */}
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-2">Dates</h3>
        <div className="space-y-1 text-sm">
          {tech.first_seen && (
            <p>
              <span className="text-gray-500">First seen:</span>{' '}
              {new Date(tech.first_seen).toLocaleDateString()}
            </p>
          )}
          {tech.scraped_at && (
            <p>
              <span className="text-gray-500">Last scraped:</span>{' '}
              {new Date(tech.scraped_at).toLocaleDateString()}
            </p>
          )}
          {tech.updated_at && (
            <p>
              <span className="text-gray-500">Updated:</span>{' '}
              {new Date(tech.updated_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>

      {/* Keywords */}
      {tech.keywords && tech.keywords.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-2">Keywords</h3>
          <div className="flex flex-wrap gap-1">
            {tech.keywords.map((kw) => (
              <span
                key={kw}
                className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded"
              >
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Patent Geography */}
      {tech.patent_geography && tech.patent_geography.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-2">Patent Geography</h3>
          <div className="flex flex-wrap gap-1">
            {tech.patent_geography.map((geo) => (
              <span
                key={geo}
                className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded"
              >
                {geo}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
