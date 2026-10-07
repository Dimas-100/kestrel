// The one word about a lot's stop, the same on Home and the Book page: a level, "resting (level not reported)",
// a red "No stop" when the source says there is none, a muted "not on record" when nothing is reported, and
// "signal exit" for a strategy that never rests one. Never colour alone.
import { Icon } from './Icon'
import type { StopFlag } from '../lib/api'
import { num } from '../lib/format'

export function stopWords(flag: StopFlag): string {
  if (flag === 'no_stop') return 'No stop'
  if (flag === 'unknown_stop') return 'not on record'
  if (flag === 'signal_exit') return 'signal exit'
  return ''
}

export function StopCell({ stopPrice, stopResting, flag }: { stopPrice: number | null; stopResting: boolean | null; flag: StopFlag }) {
  if (stopPrice != null) return <span className="num">{num(stopPrice)}</span>
  // no whitespace-nowrap: letting a long label wrap two lines (the row is tall enough) keeps the table from
  // needing to scroll to show the columns after it, such as P/L
  if (stopResting) return <span className="text-xs text-ink3">resting (level not reported)</span>
  if (flag === 'no_stop') {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap" style={{ color: 'var(--serious)' }}>
        <Icon name="shield" size={13} />No stop
      </span>
    )
  }
  if (flag === 'unknown_stop') {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap" style={{ color: 'var(--warn)' }}
        title="no protective stop reported; it may rest unreported">
        <Icon name="info" size={13} />not on record
      </span>
    )
  }
  return <span className="text-xs text-ink3">{flag === 'signal_exit' ? 'signal exit' : '—'}</span>
}
