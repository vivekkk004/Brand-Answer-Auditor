export default function Card({
  title,
  description,
  actions,
  children,
  className = '',
  bodyClassName = 'p-5',
}) {
  const hasHeader = title || description || actions
  return (
    // min-w-0: inside a grid, let the card shrink so wide tables scroll inside it instead
    // of widening the whole page on small screens.
    <section className={`min-w-0 rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {hasHeader ? (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <div>
            {title ? <h2 className="text-base font-semibold text-slate-900">{title}</h2> : null}
            {description ? <p className="mt-0.5 text-sm text-slate-500">{description}</p> : null}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={bodyClassName}>{children}</div>
    </section>
  )
}
