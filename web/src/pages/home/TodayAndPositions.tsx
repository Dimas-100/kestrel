import { Link } from '@tanstack/react-router'
import { Fragment } from 'react'
import { BookMark, Delta, Panel } from '../../components/bits'
import { Icon, type IconName } from '../../components/Icon'
import type { PositionRow, TodayRun } from '../../lib/api'
import { num, shortDate, signedMoney, timeHM } from '../../lib/format'

export const RUN_ICON: Record<TodayRun['status'], { name: IconName; color: string }> = {
  done: { name: 'checkCircle', color: 'var(--good)' },
  due: { name: 'circle', color: 'var(--ink3)' },
  late: { name: 'clock', color: 'var(--warn)' },
  failed: { name: 'alert', color: 'var(--serious)' },
  paused: { name: 'circle', color: 'var(--ink3)' },
}

export function TodayPanel({ runs, now, tz }: { runs: TodayRun[]; now: string; tz: string }) {
  const nowMs = new Date(now).getTime() // compare instants, never ISO strings with different offsets
  const nowIndex = runs.findIndex((r) => new Date(r.time).getTime() > nowMs)
  const nowLine = (
    <li className="flex items-center gap-2.5 h-[26px]" aria-label={`Now, ${timeHM(now, tz)}`}>
      <span className="num w-11 text-[11px] font-semibold" style={{ color: 'var(--acc-ink)' }}>{timeHM(now, tz)}</span>
      <span className="flex-1 h-px" style={{ background: 'var(--acc)' }} />
      <span className="label" style={{ color: 'var(--acc-ink)' }}>Now</span>
    </li>
  )
  return (
    <Panel id="today" title="Today" span={5} height={372}
      actions={<span className="num text-xs text-ink3">{shortDate(now, tz)}</span>}>
      {runs.length === 0 ? (
        <p className="text-ink3 mt-6">Nothing is scheduled today.</p>
      ) : (
        <ul className="mt-2.5">
          {runs.map((run, i) => {
            const icon = RUN_ICON[run.status]
            return (
              <Fragment key={`${run.time}-${run.label}`}>
                {i === nowIndex && nowLine}
                <li className="flex items-center gap-2.5 h-10">
                  <span className="num w-11 text-xs text-ink2">{timeHM(run.time, tz)}</span>
                  <Icon name={icon.name} size={16} style={{ color: icon.color }} />
                  <span className="sr-only">{run.status}</span>
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium truncate"
                      style={{ color: run.status === 'done' ? 'var(--ink2)' : 'var(--ink1)' }}>{run.label}</div>
                    <div className="text-[11px] text-ink3 truncate">{run.detail}</div>
                  </div>
                </li>
              </Fragment>
            )
          })}
          {nowIndex === -1 && nowLine}
        </ul>
      )}
    </Panel>
  )
}

const SHOWN = 5

export function PositionsPanel({ positions }: { positions: PositionRow[] }) {
  const real = positions.filter((p) => p.money === 'real').length
  return (
    <Panel id="positions" title="Open positions" span={7} height={372}
      actions={<span className="text-xs text-ink3">{positions.length} open · {real} real, {positions.length - real} paper</span>}>
      {positions.length === 0 ? (
        <p className="text-ink3 mt-6">No open positions.</p>
      ) : (
        <div className="table-scroll mt-3.5">
          <table className="tbl" style={{ minWidth: 560, '--row': '50px' } as React.CSSProperties}>
            <thead>
              <tr><th>Symbol</th><th className="r">Qty</th><th className="r">Entry</th><th className="r">Last</th>
                <th className="r">Stop</th><th style={{ paddingLeft: 16 }}>Room to stop</th><th className="r">P/L</th></tr>
            </thead>
            <tbody>
              {positions.slice(0, SHOWN).map((p, i) => (
                <tr key={`${p.book_id}-${p.symbol}-${i}`}>
                  <td>
                    <div className="flex items-center gap-2.5">
                      <BookMark kind={p.money} />
                      <span className="num font-semibold">{p.symbol}</span>
                      <span className="sr-only">{p.money} · {p.book}</span>
                    </div>
                  </td>
                  <td className="r num">{num(p.quantity, 0)}</td>
                  <td className="r num">{num(p.entry_price)}</td>
                  <td className="r num">{num(p.last_price)}</td>
                  <td className="r num">{p.stop_price == null ? <span className="text-ink3">—</span> : num(p.stop_price)}</td>
                  <td style={{ paddingLeft: 16 }}>
                    {p.room_pct != null ? (
                      <div className="flex items-center gap-2">
                        <span className="relative w-14 h-1.5 rounded-full overflow-hidden bg-panel2"
                          style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
                          <span className="absolute inset-y-0 left-0" style={{
                            width: `${Math.max(0, Math.min(100, (p.room_pct / 12) * 100))}%`, // below the stop: empty
                            background: p.room_pct < 8 ? 'var(--warn)' : 'var(--ink3)',
                          }} />
                        </span>
                        <span className="num text-xs">{num(p.room_pct, 1)}%</span>
                      </div>
                    ) : p.money === 'real' ? (
                      <span className="flex items-center gap-1.5 text-xs">
                        <Icon name="shield" size={14} style={{ color: 'var(--serious)' }} />No stop
                      </span>
                    ) : (
                      <span className="text-xs text-ink3">{p.note || '—'}</span>
                    )}
                  </td>
                  <td className="r"><Delta value={p.pnl}>{signedMoney(p.pnl)}</Delta></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {positions.length > SHOWN && (
        <Link to="/books" className="mt-auto text-xs pt-2" style={{ color: 'var(--acc-ink)' }}>
          {positions.length - SHOWN} more in Books
        </Link>
      )}
    </Panel>
  )
}
