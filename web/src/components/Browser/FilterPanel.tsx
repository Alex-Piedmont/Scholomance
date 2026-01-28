import { useTaxonomy, useStatsByUniversity } from '../../hooks'
import type { TechnologyFilters } from '../../api/types'

interface FilterPanelProps {
  filters: TechnologyFilters
  onFilterChange: (filters: Partial<TechnologyFilters>) => void
}

export function FilterPanel({ filters, onFilterChange }: FilterPanelProps) {
  const { data: taxonomy } = useTaxonomy()
  const { data: universities } = useStatsByUniversity()

  const selectedField = taxonomy?.find((f) => f.name === filters.top_field)
  const subfields = selectedField?.subfields || []

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Search */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Search
          </label>
          <input
            type="text"
            value={filters.q || ''}
            onChange={(e) => onFilterChange({ q: e.target.value || undefined })}
            placeholder="Search technologies..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Field */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Field
          </label>
          <select
            value={filters.top_field || ''}
            onChange={(e) =>
              onFilterChange({
                top_field: e.target.value || undefined,
                subfield: undefined,
              })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Fields</option>
            {taxonomy?.map((field) => (
              <option key={field.name} value={field.name}>
                {field.name}
              </option>
            ))}
          </select>
        </div>

        {/* Subfield */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Subfield
          </label>
          <select
            value={filters.subfield || ''}
            onChange={(e) =>
              onFilterChange({ subfield: e.target.value || undefined })
            }
            disabled={!filters.top_field}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-400"
          >
            <option value="">All Subfields</option>
            {subfields.map((sf) => (
              <option key={sf.name} value={sf.name}>
                {sf.name}
              </option>
            ))}
          </select>
        </div>

        {/* University */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            University
          </label>
          <select
            value={filters.university || ''}
            onChange={(e) =>
              onFilterChange({ university: e.target.value || undefined })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Universities</option>
            {universities?.map((uni) => (
              <option key={uni.university} value={uni.university}>
                {uni.university} ({uni.count.toLocaleString()})
              </option>
            ))}
          </select>
        </div>

        {/* Clear Filters */}
        <div className="flex items-end">
          <button
            onClick={() =>
              onFilterChange({
                q: undefined,
                top_field: undefined,
                subfield: undefined,
                university: undefined,
                from_date: undefined,
                to_date: undefined,
              })
            }
            className="w-full px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 transition-colors"
          >
            Clear Filters
          </button>
        </div>
      </div>
    </div>
  )
}
