import React from 'react'
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
  SortingState,
  ColumnFiltersState,
  VisibilityState,
  RowSelectionState,
} from '@tanstack/react-table'
import { Virtuoso } from 'react-virtuoso'
import { cn } from '../../lib/utils'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  enableSorting?: boolean
  enableFiltering?: boolean
  enableRowSelection?: boolean
  enablePagination?: boolean
  enableVirtualization?: boolean
  maxHeight?: number
  onRowSelectionChange?: (selectedRows: TData[]) => void
  className?: string
}

export function DataTable<TData, TValue>({
  columns,
  data,
  enableSorting = true,
  enableFiltering = false,
  enableRowSelection = false,
  enablePagination = false,
  enableVirtualization = false,
  maxHeight = 400,
  onRowSelectionChange,
  className,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({})

  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    getFilteredRowModel: enableFiltering ? getFilteredRowModel() : undefined,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
    enableRowSelection,
  })

  React.useEffect(() => {
    if (onRowSelectionChange) {
      const selectedRows = table.getFilteredSelectedRowModel().rows.map(row => row.original)
      onRowSelectionChange(selectedRows)
    }
  }, [rowSelection, onRowSelectionChange])

  const SortableHeader: React.FC<{ column: any; children: React.ReactNode }> = ({ column, children }) => (
    <button
      className={cn(
        "flex items-center space-x-2 hover:bg-gray-100 dark:hover:bg-gray-800 p-2 rounded transition-colors",
        column.getCanSort() ? "cursor-pointer select-none" : ""
      )}
      onClick={column.getToggleSortingHandler()}
      disabled={!column.getCanSort()}
    >
      <span>{children}</span>
      {column.getCanSort() && (
        <span className="ml-2">
          {{
            asc: <ChevronUp className="h-4 w-4" />,
            desc: <ChevronDown className="h-4 w-4" />,
          }[column.getIsSorted() as string] ?? <ChevronsUpDown className="h-4 w-4" />}
        </span>
      )}
    </button>
  )

  const TableRow: React.FC<{ row: any; index: number }> = ({ row }) => (
    <tr
      key={row.id}
      className={cn(
        "border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors",
        row.getIsSelected() && "bg-blue-50 dark:bg-blue-900/20"
      )}
    >
      {row.getVisibleCells().map((cell: any) => (
        <td key={cell.id} className="px-4 py-3 text-sm">
          {flexRender(cell.column.columnDef.cell, cell.getContext())}
        </td>
      ))}
    </tr>
  )

  const renderTable = () => (
    <div className={cn("overflow-hidden border border-gray-200 dark:border-gray-700 rounded-lg", className)}>
      <table className="w-full">
        <thead className="bg-gray-50 dark:bg-gray-800">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-gray-200 dark:border-gray-700">
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {header.isPlaceholder ? null : (
                    enableSorting && header.column.getCanSort() ? (
                      <SortableHeader column={header.column}>
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </SortableHeader>
                    ) : (
                      flexRender(header.column.columnDef.header, header.getContext())
                    )
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        {!enableVirtualization && (
          <tbody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row, index) => (
                <TableRow key={row.id} row={row} index={index} />
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                  暂无数据
                </td>
              </tr>
            )}
          </tbody>
        )}
      </table>
      
      {enableVirtualization && table.getRowModel().rows?.length > 0 && (
        <div style={{ height: maxHeight, overflow: 'auto' }}>
          <Virtuoso
            data={table.getRowModel().rows}
            itemContent={(index, row) => (
              <table className="w-full">
                <tbody>
                  <TableRow row={row} index={index} />
                </tbody>
              </table>
            )}
            components={{
              Item: ({ children, ...props }) => (
                <div {...props} style={{ ...props.style, display: 'table', width: '100%' }}>
                  {children}
                </div>
              ),
            }}
          />
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-4">
      {renderTable()}
      
      {enablePagination && (
        <div className="flex items-center justify-between px-2">
          <div className="flex-1 text-sm text-gray-700 dark:text-gray-300">
            已选择 {table.getFilteredSelectedRowModel().rows.length} 行，
            共 {table.getFilteredRowModel().rows.length} 行
          </div>
          <div className="flex items-center space-x-6 lg:space-x-8">
            <div className="flex items-center space-x-2">
              <p className="text-sm font-medium">每页显示</p>
              <select
                value={table.getState().pagination.pageSize}
                onChange={(e) => {
                  table.setPageSize(Number(e.target.value))
                }}
                className="h-8 w-[70px] rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 text-sm"
              >
                {[10, 20, 30, 40, 50].map((pageSize) => (
                  <option key={pageSize} value={pageSize}>
                    {pageSize}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex w-[100px] items-center justify-center text-sm font-medium">
              第 {table.getState().pagination.pageIndex + 1} 页，
              共 {table.getPageCount()} 页
            </div>
            <div className="flex items-center space-x-2">
              <button
                className="h-8 w-8 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-0 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">第一页</span>
                <ChevronUp className="h-4 w-4 rotate-180" />
              </button>
              <button
                className="h-8 w-8 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-0 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                <span className="sr-only">上一页</span>
                <ChevronUp className="h-4 w-4 rotate-90" />
              </button>
              <button
                className="h-8 w-8 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-0 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">下一页</span>
                <ChevronUp className="h-4 w-4 -rotate-90" />
              </button>
              <button
                className="h-8 w-8 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-0 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
              >
                <span className="sr-only">最后一页</span>
                <ChevronUp className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}