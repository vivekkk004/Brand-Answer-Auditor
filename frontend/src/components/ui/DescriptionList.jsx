/** Label / value rows, one per line, used for "details" and "summary" panels. */
export default function DescriptionList({ items }) {
  return (
    <dl className="divide-y divide-slate-100 text-sm">
      {items.map(([label, value]) => (
        <div key={label} className="flex items-baseline justify-between gap-4 py-2.5 first:pt-0 last:pb-0">
          <dt className="flex-none text-slate-500">{label}</dt>
          <dd className="min-w-0 text-right font-medium break-words text-slate-900 tabular-nums">{value}</dd>
        </div>
      ))}
    </dl>
  )
}
