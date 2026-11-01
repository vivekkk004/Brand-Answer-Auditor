export default function Card({
  title,
  description,
  actions,
  icon,
  children,
  className = '',
  bodyClassName = 'p-5 sm:p-6',
}) {
  const hasHeader = title || description || actions
  return (
    // min-w-0: inside a grid, let the card shrink so wide tables scroll inside it instead
    // of widening the whole page on small screens.
    <section className={`surface min-w-0 ${className}`}>
      {hasHeader ? (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            {icon ? (
              <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100">
                {icon}
              </div>
            ) : null}
            <div className="min-w-0">
              {title ? (
                <h2 className="text-[15px] leading-6 font-semibold text-slate-900">{title}</h2>
              ) : null}
              {description ? <p className="mt-0.5 text-sm text-slate-500">{description}</p> : null}
            </div>
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={bodyClassName}>{children}</div>
    </section>
  )
}
