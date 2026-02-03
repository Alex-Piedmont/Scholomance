import { useNavigate } from 'react-router-dom'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { useState } from 'react'
import type { TechnologySummary } from '../../api/types'

interface TechnologyTableProps {
  data: TechnologySummary[]
  loading: boolean
}

const columnHelper = createColumnHelper<TechnologySummary>()

const columns = [
  columnHelper.accessor('title', {
    header: 'Title',
    enableSorting: true,
    cell: (info) => {
      const title = info.getValue()
      return (
        <span className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer">
          {title.length > 70 ? title.slice(0, 70) + '...' : title}
        </span>
      )
    },
  }),
  columnHelper.accessor('university', {
    header: 'University',
    enableSorting: true,
    cell: (info) => (
      <span className="text-gray-600">{info.getValue()}</span>
    ),
  }),
  columnHelper.accessor('published_on', {
    header: 'First Published',
    enableSorting: true,
    sortingFn: (rowA, rowB) => {
      const a = rowA.original.published_on || rowA.original.first_seen || ''
      const b = rowB.original.published_on || rowB.original.first_seen || ''
      return a.localeCompare(b)
    },
    cell: (info) => {
      const value = info.getValue() || info.row.original.first_seen
      if (!value) return <span className="text-gray-400">-</span>
      const date = new Date(value)
      return (
        <span className="text-gray-500 text-sm">
          {date.toLocaleDateString()}
        </span>
      )
    },
  }),
]

export function TechnologyTable({ data, loading }: TechnologyTableProps) {
  const navigate = useNavigate()
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-4">
          <div className="animate-pulse space-y-3">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-12 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className={`px-4 py-3 text-left text-sm font-medium text-gray-500 ${
                    header.column.getCanSort() ? 'cursor-pointer select-none hover:text-gray-700' : ''
                  }`}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <span className="inline-flex items-center gap-1">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                    {{ asc: ' ↑', desc: ' ↓' }[header.column.getIsSorted() as string] ?? ''}
                  </span>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-gray-200">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => navigate(`/technology/${row.original.uuid}`, {
                state: {
                  uuids: data.map((d) => d.uuid),
                  index: row.index,
                },
              })}
              className="hover:bg-gray-50 cursor-pointer"
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {data.length === 0 && (
        <div className="p-8 text-center text-gray-500">
          No technologies found matching your criteria
        </div>
      )}
    </div>
  )
}
