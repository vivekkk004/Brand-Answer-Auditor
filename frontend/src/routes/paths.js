/** Every URL in the app, in one place. Pages link with these, never with string literals. */
export const PATHS = {
  home: '/',
  connect: '/connect',
  app: '/app',
  runs: '/app/runs',
  newRun: '/app/runs/new',
  run: '/app/runs/:runId',
  verify: '/app/verify',
  answer: '/app/answers/:answerId',
  review: '/app/review',
}

export const runPath = (runId) => `/app/runs/${encodeURIComponent(runId)}`
export const answerPath = (answerId) => `/app/answers/${encodeURIComponent(answerId)}`
