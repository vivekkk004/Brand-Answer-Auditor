import { describe, expect, it } from 'vitest'
import { buildSegments } from './highlight'

const claim = (id, start, end) => ({ id, start, end, label: 'supported' })

describe('buildSegments', () => {
  it('splits text into plain and claim pieces that join back to the original', () => {
    const text = 'Alpha beta gamma.'
    const segments = buildSegments(text, [claim('b', 6, 10), claim('a', 0, 5)])

    expect(segments.map((s) => [s.text, s.claim?.id ?? null])).toEqual([
      ['Alpha', 'a'],
      [' ', null],
      ['beta', 'b'],
      [' gamma.', null],
    ])
    expect(segments.map((s) => s.text).join('')).toBe(text)
  })

  it('highlights both copies of a repeated sentence using their own offsets', () => {
    const text = 'Lasts 8 hours. Lasts 8 hours.'
    const segments = buildSegments(text, [claim('first', 0, 14), claim('second', 15, 29)])
    const highlighted = segments.filter((s) => s.claim)
    expect(highlighted.map((s) => [s.claim.id, s.text])).toEqual([
      ['first', 'Lasts 8 hours.'],
      ['second', 'Lasts 8 hours.'],
    ])
  })

  it('ignores offsets outside the text and overlapping claims', () => {
    const segments = buildSegments('short', [claim('ok', 0, 2), claim('overlap', 1, 3), claim('bad', 3, 99)])
    expect(segments.filter((s) => s.claim).map((s) => s.claim.id)).toEqual(['ok'])
    expect(segments.map((s) => s.text).join('')).toBe('short')
  })

  it('returns nothing for empty text', () => {
    expect(buildSegments('', [claim('a', 0, 1)])).toEqual([])
  })
})
