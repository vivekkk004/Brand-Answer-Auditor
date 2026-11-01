/**
 * A row of mutually exclusive options (used as filters/tabs). `options` = [{ value, label }].
 * Same look everywhere: a light track with the chosen option raised in white.
 */
export default function SegmentedControl({ options, value, onChange, label, size = 'md', className = '' }) {
  const pad = size === 'sm' ? 'px-3 py-1 text-xs' : 'px-4 py-1.5 text-sm'
  return (
    <div
      role="tablist"
      aria-label={label}
      className={`flex max-w-full gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1 ring-1 ring-slate-200/60 ring-inset ${className}`}
    >
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(option.value)}
            className={`flex-1 rounded-lg font-medium whitespace-nowrap transition-all duration-200 sm:flex-none ${pad} ${
              selected
                ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/80'
                : 'text-slate-600 hover:bg-white/60 hover:text-slate-900'
            }`}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
