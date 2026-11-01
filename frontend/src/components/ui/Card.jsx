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
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100/80 px-5 py-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            {icon ? (
              <div className="icon-tile h-9 w-9 [&_svg]:h-[18px] [&_svg]:w-[18px]">
                {icon}
              </div>
            ) : null}
            <div className="min-w-0">
              {title ? (
                <h2 className="text-base leading-6 font-bold text-slate-900">{title}</h2>
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
