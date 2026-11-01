/**
 * A plain data table. `columns` = [{ key, header, render(row), className }].
 * `onRowClick` makes rows clickable (the first column should still hold a real link, so
 * keyboard users can reach the same place).
 */
export default function Table({ columns, rows, rowKey = (row) => row.id, onRowClick, empty }) {
  if (!rows.length && empty) return empty
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm tabular-nums">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/70">
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={`px-4 py-3 text-left text-[11px] font-semibold tracking-wider whitespace-nowrap text-slate-500 uppercase first:pl-5 last:pr-5 sm:first:pl-6 sm:last:pr-6 ${column.className || ''}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className={`transition-colors duration-150 ${onRowClick ? 'cursor-pointer hover:bg-indigo-50/50' : 'hover:bg-slate-50/60'}`}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-4 py-3.5 text-slate-700 first:pl-5 last:pr-5 sm:first:pl-6 sm:last:pr-6 ${column.className || ''}`}
                >
                  {column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
