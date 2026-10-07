// The last decision cycle: what the runner read, what it queued, what the gate refused and why, what was placed,
// what filled, what expired — plus the book's runs and how fresh its prices are.
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { Missing, Panel, Seg } from '../../components/bits'
import { Icon, type IconName } from '../../components/Icon'
import type { Cycle, DecisionKind } from '../../lib/api'
import { monthLabel, num, timeHM } from '../../lib/format'

const VIEWS = ['Cycle', 'Runs'] as const

export const KIND: Record<DecisionKind, { word: string; icon: IconName; color: string }> = {
  signal: { word: 'Signal', icon: 'activity', color: 'var(--ink2)' },
  queued: { word: 'Queued', icon: 'clock', color: 'var(--ink2)' },
  blocked: { word: 'Blocked', icon: 'shield', color: 'var(--warn)' },
  placed: { word: 'Placed', icon: 'arrow', color: 'var(--acc-ink)' },
  filled: { word: 'Filled', icon: 'check', color: 'var(--good)' },
  expired: { word: 'Expired', icon: 'close', color: 'var(--ink3)' },
  cancelled: { word: 'Cancelled', icon: 'close', color: 'var(--ink3)' },
  skipped: { word: 'Skipped', icon: 'info', color: 'var(--ink3)' },
  error: { word: 'Error', icon: 'alert', color: 'var(--serious)' },
}

const RUN_COLOR: Record<string, string> = {
  done: 'var(--good)', failed: 'var(--serious)', late: 'var(--warn)', due: 'var(--ink3)', paused: 'var(--ink3)',
}

/** "3 signals · 2 queued · 1 blocked · 1 filled" */
export function countsText(c: Cycle): string {
  return c.counts.map(({ kind, count }) => `${count} ${KIND[kind].word.toLowerCase()}${kind === 'signal' && count !== 1 ? 's' : ''}`).join(' · ')
}

export function CyclePanel({ c, tz }: { c: Cycle; tz: string }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Cycle')
  const freshness = c.prices_as_of
    ? `prices as of ${monthLabel(c.prices_as_of, true)} (${c.freshness})` : 'prices: date not reported'
  return (
    <Panel id="cycle" title="Last decision cycle" span={7} height={452}
      subtitle={c.book_id ? `${c.session ? `Ended ${monthLabel(c.session, true)} · ` : ''}${freshness}` : undefined}
      actions={c.book_id && (c.reported || c.runs.length > 0) && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {c.book_id == null ? (
        <Empty>No book trades this strategy yet.</Empty>
      ) : view === 'Runs' ? (
        c.runs.length === 0 ? <Empty>No runs reported for this book.</Empty> : (
          <div className="table-scroll overflow-y-auto mt-3" style={{ maxHeight: 360 }}>
            <table className="tbl" style={{ '--row': '40px' } as CSSProperties}>
              <thead><tr><th>Run</th><th>When</th><th>Status</th><th>Detail</th></tr></thead>
              <tbody>
                {c.runs.map((r, i) => (
                  <tr key={`${r.label}-${i}`}>
                    <td className="text-sm">{r.label}</td>
                    <td className="num text-ink2 text-xs whitespace-nowrap">{monthLabel(r.time, true)} {timeHM(r.time, tz)}</td>
                    <td><span className="text-xs capitalize" style={{ color: RUN_COLOR[r.status] ?? 'var(--ink2)' }}>{r.status}</span></td>
                    <td className="text-xs text-ink3 [overflow-wrap:anywhere]">{r.detail || <Missing />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : !c.reported ? (
        <Empty>This book doesn&rsquo;t report its decisions.</Empty>
      ) : (
        <>
          <div className="text-xs text-ink2 mt-2">{countsText(c)}</div>
          <div className="table-scroll overflow-y-auto mt-2" style={{ maxHeight: 340 }}>
            <table className="tbl" style={{ '--row': '36px', minWidth: 520 } as CSSProperties}>
              <thead><tr><th>When</th><th>What</th><th>Symbol</th><th className="r">Reading</th><th>Detail</th></tr></thead>
              <tbody>
                {c.rows.map((d, i) => {
                  const look = KIND[d.kind]
                  return (
                    <tr key={`${d.time}-${d.kind}-${d.symbol}-${i}`}>
                      <td className="num text-xs text-ink2 whitespace-nowrap">{timeHM(d.time, tz)}</td>
                      <td>
                        <span className="inline-flex items-center gap-1.5 text-xs" style={{ color: look.color }}>
                          <Icon name={look.icon} size={13} />{look.word}{d.side && <span className="text-ink3"> · {d.side}</span>}
                        </span>
                      </td>
                      <td className="num font-semibold text-sm">{d.symbol || <Missing />}</td>
                      <td className="r num text-xs">{d.value == null ? <Missing /> : `${d.label ? `${d.label} ` : ''}${num(d.value, 2)}`}</td>
                      <td className="text-xs text-ink3 [overflow-wrap:anywhere]">{d.detail || <Missing />}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  )
}
