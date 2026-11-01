/**
 * A new Idempotency-Key. The New run form keeps one key while its values stay the same,
 * so a double click or a retry after a network error replays the same run instead of
 * starting (and paying for) a second one.
 */
export function newIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return `ui-${globalThis.crypto.randomUUID()}`
  return `ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}
