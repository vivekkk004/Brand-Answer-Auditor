/** Shared classes for text inputs, selects and textareas. */
export const INPUT_CLASSES =
  'block min-h-10 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 ' +
  'shadow-xs transition-[border-color,box-shadow] duration-150 placeholder:text-slate-400 ' +
  'hover:border-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-4 ' +
  'focus:ring-indigo-500/15 disabled:cursor-not-allowed disabled:bg-slate-50 ' +
  'aria-invalid:border-rose-400 aria-invalid:focus:ring-rose-500/15'

/** Same as inputs, plus a custom arrow in place of the browser's own. */
export const SELECT_CLASSES = `${INPUT_CLASSES} select-chevron cursor-pointer pr-9`
