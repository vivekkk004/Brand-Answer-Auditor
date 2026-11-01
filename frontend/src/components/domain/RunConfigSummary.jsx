import { formatNumber } from '../../utils/format'

/** The run's stored configuration as a short definition list. */
export default function RunConfigSummary({ config, modelCalls, maxModelCalls }) {
  const items = [
    ['Category', config.category],
    ['Prompts', config.prompt_ids?.length ? config.prompt_ids.join(', ') : 'All in category'],
    ['Answer providers', config.answer_providers?.join(', ')],
    ['Repeats', config.repeats],
    ['Agent prompt', config.agent_version],
    ['Model calls', `${formatNumber(modelCalls)} of ${formatNumber(maxModelCalls)}`],
  ]
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</dt>
          <dd className="mt-1 text-sm font-medium text-slate-900">{value ?? '–'}</dd>
        </div>
      ))}
    </dl>
  )
}
