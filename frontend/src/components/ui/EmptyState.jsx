import Icon from './Icon'

export default function EmptyState({ icon = 'runs', title, description, action }) {
  return (
    <div className="animate-page-in flex flex-col items-center justify-center px-6 py-12 text-center sm:py-14">
      <div className="relative mb-5">
        <div className="absolute inset-0 scale-150 rounded-full bg-indigo-100/60 blur-xl" />
        <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200">
          <Icon name={icon} className="h-6 w-6" />
        </div>
      </div>
      <h3 className="text-base font-semibold text-slate-900">{title}</h3>
      {description ? <p className="mt-1.5 max-w-sm text-sm text-slate-500">{description}</p> : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  )
}
