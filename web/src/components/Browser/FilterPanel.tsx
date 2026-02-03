import { useState, useRef, useEffect } from 'react'
import { useStatsByUniversity } from '../../hooks'
import type { TechnologyFilters } from '../../api/types'

interface FilterPanelProps {
  filters: TechnologyFilters
  onFilterChange: (filters: Partial<TechnologyFilters>) => void
}

export function FilterPanel({ filters, onFilterChange }: FilterPanelProps) {
  const { data: universities } = useStatsByUniversity()

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

        {/* University (multi-select) */}
        <UniversityMultiSelect
          selected={filters.university || []}
          universities={universities || []}
          onChange={(selected) =>
            onFilterChange({ university: selected.length > 0 ? selected : undefined })
          }
        />

        {/* Patent Status */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Patent Status
          </label>
          <select
            value={filters.patent_status || ''}
            onChange={(e) =>
              onFilterChange({ patent_status: e.target.value || undefined })
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Statuses</option>
            <option value="filed">Filed</option>
            <option value="granted">Granted</option>
            <option value="pending">Pending</option>
            <option value="provisional">Provisional</option>
            <option value="expired">Expired</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>

        {/* Publication Date */}
        <YearMonthPicker
          fromDate={filters.from_date}
          toDate={filters.to_date}
          onChange={(from_date, to_date) => onFilterChange({ from_date, to_date })}
        />

        {/* Clear Filters */}
        <div className="flex items-end">
          <button
            onClick={() =>
              onFilterChange({
                q: undefined,
                university: undefined,
                patent_status: undefined,
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
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (open && searchRef.current) {
      searchRef.current.focus()
    }
    if (!open) {
      setSearch('')
    }
  }, [open])

  const toggle = (uni: string) => {
    if (selected.includes(uni)) {
      onChange(selected.filter((u) => u !== uni))
    } else {
      onChange([...selected, uni])
    }
  }

  const filtered = search
    ? universities.filter((u) => u.university.toLowerCase().includes(search.toLowerCase()))
    : universities

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
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg">
          <div className="p-2 border-b border-gray-200">
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search universities..."
              className="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="max-h-52 overflow-auto">
            {filtered.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500">No matches</div>
            ) : (
              filtered.map((uni) => (
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
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Selection key: "2024" for whole year, "2024-03" for specific month
type DateSelection = Set<string>

function parseDateSelections(fromDate?: string, toDate?: string): DateSelection {
  const sel = new Set<string>()
  if (!fromDate || !toDate) return sel
  // Reconstruct selections from URL params stored as comma-separated in from_date
  // We encode selections in from_date as "sel:2024,2024-03,2023" and to_date as "sel"
  if (toDate === 'sel') {
    for (const s of fromDate.split(',')) sel.add(s)
    return sel
  }
  // Legacy single range — approximate as year selection
  const year = new Date(fromDate).getFullYear()
  sel.add(String(year))
  return sel
}

interface YearMonthPickerProps {
  fromDate: string | undefined
  toDate: string | undefined
  onChange: (fromDate: string | undefined, toDate: string | undefined) => void
}

function YearMonthPicker({ fromDate, toDate, onChange }: YearMonthPickerProps) {
  const [open, setOpen] = useState(false)
  const [expandedYear, setExpandedYear] = useState<number | null>(null)
  const ref = useRef<HTMLDivElement>(null)
  const selections = parseDateSelections(fromDate, toDate)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const now = new Date()
  const currentYear = now.getFullYear()
  const currentMonth = now.getMonth()
  const years = Array.from({ length: currentYear - 2014 }, (_, i) => currentYear - i)

  const applySelections = (sel: DateSelection) => {
    if (sel.size === 0) {
      onChange(undefined, undefined)
    } else {
      // Store selections encoded in from_date, with to_date as marker
      onChange(Array.from(sel).join(','), 'sel')
    }
  }

  const toggleYear = (year: number) => {
    const next = new Set(selections)
    const key = String(year)
    if (next.has(key)) {
      next.delete(key)
      // Also remove any month selections for this year
      for (const s of next) {
        if (s.startsWith(`${year}-`)) next.delete(s)
      }
    } else {
      next.add(key)
      // Remove individual month selections since whole year is selected
      for (const s of next) {
        if (s.startsWith(`${year}-`)) next.delete(s)
      }
    }
    applySelections(next)
  }

  const toggleMonth = (year: number, month: number) => {
    const next = new Set(selections)
    const key = `${year}-${String(month + 1).padStart(2, '0')}`
    const yearKey = String(year)

    if (next.has(yearKey)) {
      // Whole year was selected — deselect it, add all other months
      next.delete(yearKey)
      const maxMonth = year === currentYear ? currentMonth : 11
      for (let i = 0; i <= maxMonth; i++) {
        if (i !== month) {
          next.add(`${year}-${String(i + 1).padStart(2, '0')}`)
        }
      }
    } else if (next.has(key)) {
      next.delete(key)
    } else {
      next.add(key)
      // Check if all months are now selected — collapse to year
      const maxMonth = year === currentYear ? currentMonth : 11
      let allSelected = true
      for (let i = 0; i <= maxMonth; i++) {
        if (!next.has(`${year}-${String(i + 1).padStart(2, '0')}`)) {
          allSelected = false
          break
        }
      }
      if (allSelected) {
        for (let i = 0; i <= maxMonth; i++) {
          next.delete(`${year}-${String(i + 1).padStart(2, '0')}`)
        }
        next.add(yearKey)
      }
    }
    applySelections(next)
  }

  const isYearSelected = (year: number) => selections.has(String(year))
  const isMonthSelected = (year: number, month: number) => {
    if (selections.has(String(year))) return true
    return selections.has(`${year}-${String(month + 1).padStart(2, '0')}`)
  }
  const yearHasPartial = (year: number) => {
    if (selections.has(String(year))) return false
    for (const s of selections) {
      if (s.startsWith(`${year}-`)) return true
    }
    return false
  }

  const clear = () => {
    applySelections(new Set())
    setExpandedYear(null)
  }

  // Build label
  const count = selections.size
  let label = 'All Dates'
  if (count === 1) {
    const key = Array.from(selections)[0]
    const parts = key.split('-')
    label = parts.length === 1 ? parts[0] : `${MONTHS[parseInt(parts[1]) - 1]} ${parts[0]}`
  } else if (count > 1) {
    label = `${count} periods`
  }

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Published
      </label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white flex items-center justify-between"
      >
        <span className={count > 0 ? 'text-gray-900' : 'text-gray-500'}>
          {label}
        </span>
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-64 overflow-auto">
          {count > 0 && (
            <button
              onClick={clear}
              className="w-full px-3 py-2 text-left text-sm text-gray-500 hover:bg-gray-50 border-b border-gray-100"
            >
              Clear
            </button>
          )}
          {years.map((year) => (
            <div key={year}>
              <div className="flex items-center">
                <label className={`flex-1 flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 cursor-pointer ${
                  isYearSelected(year) ? 'text-blue-700 font-medium' : 'text-gray-900'
                }`}>
                  <input
                    type="checkbox"
                    checked={isYearSelected(year)}
                    ref={(el) => {
                      if (el) el.indeterminate = yearHasPartial(year)
                    }}
                    onChange={() => toggleYear(year)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  {year}
                </label>
                <button
                  onClick={() => setExpandedYear(expandedYear === year ? null : year)}
                  className="px-3 py-2 text-gray-400 hover:text-gray-600"
                >
                  <svg className={`w-3 h-3 transition-transform ${expandedYear === year ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
              {expandedYear === year && (
                <div className="grid grid-cols-3 gap-1 px-3 pb-2">
                  {MONTHS.map((m, i) => {
                    const isFuture = year === currentYear && i > currentMonth
                    if (isFuture) return (
                      <span key={m} className="px-2 py-1 text-xs rounded bg-gray-50 text-gray-300 text-center">
                        {m}
                      </span>
                    )
                    const selected = isMonthSelected(year, i)
                    return (
                      <button
                        key={m}
                        onClick={() => toggleMonth(year, i)}
                        className={`px-2 py-1 text-xs rounded ${
                          selected
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {m}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
