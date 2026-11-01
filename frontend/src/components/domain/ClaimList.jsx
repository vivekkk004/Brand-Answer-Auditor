import { humanize } from '../../utils/format'
import EmptyState from '../ui/EmptyState'
import { LabelBadge } from './StatusBadges'

/** One card per claim: label, what it is about, cited facts and the agent's reason. */
export default function ClaimList({ claims, activeClaimId, onSelectClaim }) {
  if (!claims.length) {
    return (
      <EmptyState
        icon="check"
        title="No checkable claims"
        description="The agent found no product claims about catalogue brands in this answer."
      />
    )
  }

  return (
    <ol className="space-y-3">
      {claims.map((claim, index) => (
        <li key={claim.id ?? index}>
          <button
            type="button"
            onClick={onSelectClaim ? () => onSelectClaim(claim.id) : undefined}
            className={`w-full rounded-lg border p-4 text-left transition-colors ${
              activeClaimId === claim.id
                ? 'border-indigo-300 bg-indigo-50/50'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400">#{index + 1}</span>
              <LabelBadge label={claim.label} />
              <span className="text-xs font-medium text-slate-500">
                {claim.product || claim.brand_id} · {humanize(claim.attribute)}
              </span>
            </div>
            <blockquote className="mt-2 border-l-2 border-slate-200 pl-3 text-sm text-slate-800">
              “{claim.quote}”
            </blockquote>
            <p className="mt-2 text-sm text-slate-600">{claim.rationale}</p>
            {claim.fact_ids.length ? (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {claim.fact_ids.map((factId) => (
                  <code
                    key={factId}
                    className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600"
                  >
                    {factId}
                  </code>
                ))}
              </div>
            ) : null}
          </button>
        </li>
      ))}
    </ol>
  )
}
