/** Fixed value sets, matching the backend's enums (src/auditor/enums.py). */

export const RUN_STATUSES = ['queued', 'running', 'completed', 'partial', 'failed']
// A run in one of these states can still change, so the detail page keeps polling.
export const ACTIVE_RUN_STATUSES = ['queued', 'running']
export const REVIEW_STATUSES = ['open', 'confirmed', 'dismissed']
export const PROVIDERS = [
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'groq', label: 'Groq' },
]
// Short names for chips and lists.
export const PROVIDER_SHORT = { gemini: 'Gemini', openai: 'OpenAI', groq: 'Groq' }
export const MARKETS = [
  { value: '', label: 'Not given' },
  { value: 'IN', label: 'India (IN)' },
  { value: 'US', label: 'United States (US)' },
]
export const PROMPT_VERSIONS = [
  { value: 'v1', label: 'v1 — base prompt' },
  { value: 'v2', label: 'v2 — v1 + qualifier checklist' },
]

// One colour meaning everywhere: green good, amber attention, red problem.
export const RUN_STATUS_TONE = {
  queued: 'slate',
  running: 'blue',
  completed: 'green',
  partial: 'amber',
  failed: 'red',
}
export const ANSWER_STATUS_TONE = {
  pending: 'slate',
  verified: 'green',
  generation_failed: 'red',
  verification_failed: 'red',
}
export const LABEL_TONE = { supported: 'green', contradicted: 'red', unknown: 'amber' }
export const REVIEW_STATUS_TONE = { open: 'blue', confirmed: 'red', dismissed: 'slate' }

// Highlight colours for claims inside answer text.
export const LABEL_HIGHLIGHT = {
  supported: 'bg-emerald-100 decoration-emerald-500',
  contradicted: 'bg-rose-100 decoration-rose-500',
  unknown: 'bg-amber-100 decoration-amber-500',
}
// Bar colours, checked for colour-blind separation in this order: supported, unknown,
// contradicted (amber sits between green and red so those two never touch).
export const LABEL_ORDER = ['supported', 'unknown', 'contradicted']
export const LABEL_BAR = {
  supported: 'bg-emerald-600',
  unknown: 'bg-amber-500',
  contradicted: 'bg-rose-600',
}
