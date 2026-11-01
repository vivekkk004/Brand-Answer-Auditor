/**
 * A labelled form field with an optional hint and error message. `action` is a small
 * control shown on the label's line (for example "Try an example").
 */
export default function Field({ id, label, hint, error, action, children }) {
  return (
    <div>
      <div className="flex min-h-6 items-center justify-between gap-3">
        <label htmlFor={id} className="block text-sm font-medium text-slate-700">
          {label}
        </label>
        {action}
      </div>
      <div className="mt-1.5">{children}</div>
      {error ? (
        <p className="mt-1.5 flex items-center gap-1.5 text-sm text-rose-600" id={`${id}-error`}>
          <span className="h-1 w-1 flex-none rounded-full bg-rose-500" aria-hidden />
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1.5 text-xs leading-5 text-slate-500">{hint}</p>
      ) : null}
    </div>
  )
}
