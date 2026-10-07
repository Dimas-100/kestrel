// The next review: how far it is (trades or a date, whichever first), what the last one said, and the criteria it
// scores with their latest reading. Status carries a word and an icon, never colour alone.
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import { Icon, type IconName } from '../../components/Icon'
import type { Criterion, ReviewProgress } from '../../lib/api'
import { monthLabel } from '../../lib/format'

const STATUS: Record<Criterion['status'], { icon: IconName; color: string; word: string }> = {
  pass: { icon: 'check', color: 'var(--good)', word: 'Pass' },
  fail: { icon: 'alert', color: 'var(--warn)', word: 'Fail' },
  pending: { icon: 'clock', color: 'var(--ink3)', word: 'Pending' },
  info: { icon: 'info', color: 'var(--ink3)', word: 'Reported' },
}

/** "12 of 20 trades since 2 Oct" · "by 2 Nov (26 days)" · "Due" */
export function reviewLine(r: ReviewProgress): string {
  const parts: string[] = []
  if (r.at_trades != null) {
    parts.push(`${r.trades} of ${r.at_trades} trades${r.counted_since ? ` since ${monthLabel(r.counted_since, true)}` : ''}`)
  }
  if (r.by) {
    const left = r.days_left == null ? '' : r.days_left > 0 ? ` (${r.days_left} day${r.days_left === 1 ? '' : 's'})` : ''
    parts.push(`by ${monthLabel(r.by, true)}${left}`)
  }
  if (r.due) parts.push('due now')
  return parts.join(' · ')
}

export function ReviewPanel({ review }: { review: ReviewProgress | null }) {
  const passing = review ? review.criteria.filter((c) => c.status === 'pass').length : 0
  const scored = review ? review.criteria.filter((c) => c.status === 'pass' || c.status === 'fail').length : 0
  return (
    <Panel id="review" title="Next review" span={7} height={372}
      subtitle={review ? `${review.label}${review.doc ? ` · ${review.doc}` : ''}` : undefined}
      actions={review && scored > 0 && <span className="chip">{passing} of {scored} criteria passing</span>}>
      {!review ? (
        <Empty>This strategy hasn&rsquo;t set a review.</Empty>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className={`text-sm ${review.due ? 'font-semibold' : 'text-ink2'}`}>{reviewLine(review)}</span>
            {review.last_at && (
              <span className="text-xs text-ink3">Last review {monthLabel(review.last_at, true)}</span>
            )}
          </div>
          {review.at_trades != null && (
            <div role="progressbar" aria-label={`${review.label}: trades counted`} aria-valuemin={0}
              aria-valuemax={review.at_trades} aria-valuenow={Math.min(review.trades, review.at_trades)}
              className="relative h-2 rounded mt-2 overflow-hidden bg-panel2" style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
              <span className="absolute inset-y-0 left-0 rounded"
                style={{ width: `${Math.min(100, (review.trades / review.at_trades) * 100)}%`, background: 'var(--acc)' }} />
            </div>
          )}
          {review.last_note && <p className="text-xs text-ink2 mt-2.5 [overflow-wrap:anywhere]">{review.last_note}</p>}
          {review.criteria.length > 0 && (
            <div className="table-scroll mt-3">
              <table className="tbl" style={{ minWidth: 520 }}>
                <thead>
                  <tr><th>What it needs</th><th>Bar</th><th className="r">Now</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {review.criteria.map((c) => {
                    const look = STATUS[c.status]
                    return (
                      <tr key={c.key}>
                        <td>
                          <div className="text-sm">{c.label}</div>
                          {c.measure && <div className="text-[11px] text-ink3">{c.measure}</div>}
                        </td>
                        <td className="text-xs text-ink2">{c.target || <Missing />}</td>
                        <td className="r num text-sm">{c.value || <Missing />}</td>
                        <td>
                          <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: look.color }}>
                            <Icon name={look.icon} size={14} />{look.word}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
