import { useState, useRef, useEffect } from 'react'
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

        {/* University (multi-select) */}
        <UniversityMultiSelect
          selected={filters.university || []}
          universities={universities || []}
          onChange={(selected) =>
            onFilterChange({ university: selected.length > 0 ? selected : undefined })
          }
        />

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

interface UniversityMultiSelectProps {
  selected: string[]
  universities: { university: string; count: number }[]
  onChange: (selected: string[]) => void
}

function UniversityMultiSelect({ selected, universities, onChange }: UniversityMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggle = (uni: string) => {
    if (selected.includes(uni)) {
      onChange(selected.filter((u) => u !== uni))
    } else {
      onChange([...selected, uni])
    }
  }

  const label =
    selected.length === 0
      ? 'All Universities'
      : selected.length === 1
        ? selected[0]
        : `${selected.length} universities`

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        University
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white flex items-center justify-between"
      >
        <span className={selected.length === 0 ? 'text-gray-500' : 'text-gray-900'}>
          {label}
        </span>
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
          {universities.map((uni) => (
            <label
              key={uni.university}
              className="flex items-center px-3 py-2 hover:bg-gray-50 cursor-pointer text-sm"
            >
              <input
                type="checkbox"
                checked={selected.includes(uni.university)}
                onChange={() => toggle(uni.university)}
                className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="flex-1">{uni.university}</span>
              <span className="text-gray-400 ml-1">({uni.count.toLocaleString()})</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
