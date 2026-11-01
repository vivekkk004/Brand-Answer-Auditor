/**
 * Split an answer into plain and highlighted pieces, using the claim offsets the API
 * returns (computed by the backend, so text.slice(start, end) === quote).
 *
 * The result is a list of { text, claim } pieces; claim is null for plain text. Rendering
 * pieces as React text (never as HTML) means a quote cannot inject markup into the page.
 */
export function buildSegments(text, claims) {
  if (!text) return []
  const ordered = [...(claims || [])]
    .filter((claim) => claim.start >= 0 && claim.end <= text.length && claim.start < claim.end)
    .sort((a, b) => a.start - b.start)

  const segments = []
  let cursor = 0
  for (const claim of ordered) {
    // Claims never overlap (each quote has its own span); skip one defensively if it does.
    if (claim.start < cursor) continue
    if (claim.start > cursor) segments.push({ text: text.slice(cursor, claim.start), claim: null })
    segments.push({ text: text.slice(claim.start, claim.end), claim })
    cursor = claim.end
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), claim: null })
  return segments
}
