import { LABEL_HIGHLIGHT } from '../../utils/constants'
import { buildSegments } from '../../utils/highlight'

/**
 * The answer text with every claim highlighted in its label's colour.
 * Pieces are rendered as React text, never as HTML, so answer text cannot inject markup.
 */
export default function HighlightedAnswer({ text, claims, activeClaimId, onSelectClaim }) {
  const segments = buildSegments(text, claims)

  return (
    <p className="text-[15px] leading-8 whitespace-pre-wrap text-slate-800">
      {segments.map((segment, index) =>
        segment.claim ? (
          <mark
            key={segment.claim.id ?? index}
            data-label={segment.claim.label}
            className={`cursor-pointer rounded px-0.5 text-slate-900 underline decoration-2 underline-offset-4 ${
              LABEL_HIGHLIGHT[segment.claim.label] || 'bg-slate-100'
            } ${activeClaimId === segment.claim.id ? 'ring-2 ring-indigo-400' : ''}`}
            onClick={onSelectClaim ? () => onSelectClaim(segment.claim.id) : undefined}
            title={`${segment.claim.label}: ${segment.claim.rationale || ''}`}
          >
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </p>
  )
}
