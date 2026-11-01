/** Small display helpers. Missing values show as an en dash, never as 0. */

export const EMPTY = '–'

export function formatDateTime(iso) {
  if (!iso) return EMPTY
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return EMPTY
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** 0.1234 -> "12.3%". */
export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined) return EMPTY
  return `${(value * 100).toFixed(digits)}%`
}

export function formatNumber(value) {
  if (value === null || value === undefined) return EMPTY
  return value.toLocaleString()
}

export function formatMs(value) {
  if (value === null || value === undefined) return EMPTY
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`
}

/** Cost is only known when token prices are configured on the server. */
export function formatUsd(value) {
  if (value === null || value === undefined) return 'Not configured'
  return `$${value.toFixed(4)}`
}

/** Turn "water_resistance" into "Water resistance". */
export function humanize(value) {
  if (!value) return EMPTY
  const text = String(value).replaceAll('_', ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function shortId(id) {
  return id ? String(id).slice(0, 8) : EMPTY
}
