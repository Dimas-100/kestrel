import { BookMark, Delta, Missing, MoneyBadge, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { BookRow } from '../../lib/api'
import { money, pct, shortDate, signedMoney, sinceLabel, timeHM } from '../../lib/format'

/** The per-trade result against its expected 95% band: dotted band, zero tick, a dot for the actual. */
export function BandBar({ lo, hi, actual }: { lo: number; hi: number; actual: number }) {
  const W = 110
  const low = Math.min(lo, actual, 0)
  const high = Math.max(hi, actual, 0)
  const pad = (high - low) * 0.15 || 1
  const x = (v: number) => ((v - (low - pad)) / (high + pad - (low - pad))) * W
  return (
    <svg width={W} height={14} aria-hidden="true" style={{ display: 'block', overflow: 'visible' }}>
      <line x1={0} x2={W} y1={7} y2={7} stroke="var(--line2)" />
      <rect x={x(lo)} y={2} width={Math.max(2, x(hi) - x(lo))} height={10} rx={3} fill="var(--ink1)" fillOpacity={0.06}
        stroke="var(--ref)" strokeDasharray="1.5 2.5" />
      <line x1={x(0)} x2={x(0)} y1={0} y2={14} stroke="var(--ink3)" />
      <circle cx={x(actual)} cy={7} r={4} fill="var(--ink1)" stroke="var(--panel)" strokeWidth={2} />
    </svg>
  )
}

function Slots({ used, total, money: kind }: { used: number; total: number; money: BookRow['money'] }) {
  return (
    <div className="flex gap-[3px]" role="img" aria-label={`${used} of ${total} slots in use`}>
      {Array.from({ length: total }, (_, i) => i < used
        ? <BookMark key={i} kind={kind} size={10} />
        : <span key={i} className="w-2.5 h-2.5 rounded-sm" style={{ boxShadow: 'inset 0 0 0 1px var(--line2)' }} />)}
    </div>
  )
}

const VERDICT: Record<BookRow['verdict'], string> = {
  in_band: 'In band', below: 'Below band', above: 'Above band', early: 'Too early', none: '—',
}

export function BooksPanel({ books, tz, now }: { books: BookRow[]; tz: string; now: string }) {
  return (
    <Panel id="books" title="Books" subtitle="Every strategy, real and paper, side by side" span={12}
      actions={<div className="hidden md:flex items-center gap-4 text-xs text-ink2">
        <span className="inline-flex items-center gap-1.5"><BookMark kind="real" />Real money</span>
        <span className="inline-flex items-center gap-1.5"><BookMark kind="paper" />Paper</span>
        <span className="inline-flex items-center gap-1.5"><BookMark kind="expected" />Expected range</span>
      </div>}>
      <div className="table-scroll mt-4">
        <table className="tbl" style={{ minWidth: 900 }}>
          <thead>
            <tr>
              <th>Book</th><th>Money</th><th className="r">Value</th><th className="r">Today</th>
              <th className="r">Since start</th><th style={{ paddingLeft: 28 }}>Per trade vs expected</th>
              <th>Slots</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {books.map((b) => (
              <tr key={b.id}>
                <td>
                  <div className="flex items-center gap-3">
                    <BookMark kind={b.money} size={14} />
                    <div>
                      <div className="font-medium">{b.name}</div>
                      <div className="text-xs text-ink3 mt-0.5">{b.trades} trades · since {sinceLabel(b.started, now)}</div>
                    </div>
                  </div>
                </td>
                <td><MoneyBadge money={b.money} /></td>
                <td className="r num">{money(b.value)}</td>
                <td className="r">{b.day_change == null ? <Missing /> : <Delta value={b.day_change}>{signedMoney(b.day_change)}</Delta>}</td>
                <td className="r">{b.since_pct == null ? <Missing /> : <Delta value={b.since_pct} digits={1}>{pct(b.since_pct)}</Delta>}</td>
                <td style={{ paddingLeft: 28 }}>
                  {b.band_lo != null && b.band_hi != null && b.per_trade_pct != null && (
                    <BandBar lo={b.band_lo} hi={b.band_hi} actual={b.per_trade_pct} />
                  )}
                  <div className="text-[11px] mt-1.5 flex items-center gap-1.5 whitespace-nowrap"
                    style={{ color: b.verdict === 'below' ? 'var(--ink1)' : 'var(--ink3)' }}>
                    {b.verdict === 'below' && <Icon name="alert" size={12} style={{ color: 'var(--warn)' }} />}
                    {VERDICT[b.verdict]}
                    {b.verdict === 'early' && ` · ${b.trades} trades`}
                    {b.per_trade_pct != null && b.verdict !== 'early' && b.verdict !== 'none' && (
                      <span className="num"> · <Delta value={b.per_trade_pct}>{pct(b.per_trade_pct, 2)}</Delta></span>
                    )}
                  </div>
                </td>
                <td>
                  {b.slots_total ? <><Slots used={b.slots_used} total={b.slots_total} money={b.money} />
                    <div className="num text-[11px] text-ink3 mt-1.5">{b.slots_used} of {b.slots_total}</div></> : <Missing />}
                </td>
                <td>
                  <div className="flex items-center gap-2 text-[13px] capitalize">
                    <span className="w-2 h-2 rounded-full" style={b.status === 'running'
                      ? { background: 'var(--good)' } : { boxShadow: 'inset 0 0 0 1.5px var(--ink3)' }} />
                    {b.status}
                  </div>
                  <div className="num text-[11px] text-ink3 mt-1">
                    {b.next_run ? `${shortDate(b.next_run, tz).slice(0, 3)} ${timeHM(b.next_run, tz)}` : '—'}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
