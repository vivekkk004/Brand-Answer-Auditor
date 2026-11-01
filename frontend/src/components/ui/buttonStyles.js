/** Shared button classes, so a <button> and a router <Link> can look the same. */
const BASE =
  'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-all duration-150 ' +
  'disabled:cursor-not-allowed disabled:opacity-60 whitespace-nowrap active:translate-y-px'

const VARIANTS = {
  primary:
    'bg-gradient-to-b from-indigo-500 to-indigo-600 text-white shadow-md shadow-indigo-600/30 ' +
    'ring-1 ring-inset ring-white/15 hover:from-indigo-500 hover:to-violet-600 ' +
    'hover:shadow-lg hover:shadow-indigo-600/35',
  secondary:
    'bg-white text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 hover:text-slate-900',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
  danger: 'bg-rose-600 text-white shadow-sm shadow-rose-600/20 hover:bg-rose-500 hover:shadow-md hover:shadow-rose-600/25',
  success: 'bg-emerald-600 text-white shadow-sm hover:bg-emerald-500',
  // For use on coloured (indigo/violet) backgrounds.
  white: 'bg-white text-indigo-700 shadow-sm hover:bg-indigo-50',
  glass: 'bg-white/10 text-white ring-1 ring-inset ring-white/20 backdrop-blur hover:bg-white/20',
}

const SIZES = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-5 text-[15px]',
}

export function buttonClasses(variant = 'primary', size = 'md', extra = '') {
  return `${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${extra}`.trim()
}
