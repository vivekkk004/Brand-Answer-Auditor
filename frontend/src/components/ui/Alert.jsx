import Icon from './Icon'

const TONES = {
  info: { box: 'border-blue-200 bg-blue-50', icon: 'text-blue-600', title: 'text-blue-900', body: 'text-blue-800', name: 'info' },
  warning: { box: 'border-amber-200 bg-amber-50', icon: 'text-amber-600', title: 'text-amber-900', body: 'text-amber-800', name: 'alert' },
  danger: { box: 'border-rose-200 bg-rose-50', icon: 'text-rose-600', title: 'text-rose-800', body: 'text-rose-700', name: 'alert' },
}

/**
 * One notice box for the whole app (info, warning, error), so every message has the same
 * shape: icon, optional title, text, and an optional action on the right.
 */
export default function Alert({ tone = 'info', title, action, role, children }) {
  const style = TONES[tone]
  return (
    <div role={role} className={`animate-page-in rounded-xl border p-4 ${style.box}`}>
      <div className="flex flex-wrap gap-3 sm:flex-nowrap">
        <Icon name={style.name} className={`mt-0.5 h-5 w-5 flex-none ${style.icon}`} />
        <div className={`min-w-0 flex-1 text-sm ${style.body}`}>
          {title ? <p className={`font-semibold ${style.title}`}>{title}</p> : null}
          <div className={title ? 'mt-1' : ''}>{children}</div>
        </div>
        {action ? <div className="flex-none">{action}</div> : null}
      </div>
    </div>
  )
}
