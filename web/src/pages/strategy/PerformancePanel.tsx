// How the money is doing: realized and unrealized P&L, the return on a documented capital basis, what is deployed
// against that capital, stop coverage, and the drawdown now and at its worst. What can't be shown says why.
import type { ReactNode } from 'react'
import { Delta, Missing, Panel } from '../../components/bits'
import type { Performance } from '../../lib/api'
import { money, monthLabel, pct, signedMoney } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'

function Tile({ label, sub, children }: { label: string; sub?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2.5 min-w-0">
      <div className="label">{label}</div>
      <div className="num text-lg mt-1">{children}</div>
      {sub && <div className="text-[11px] text-ink3 mt-0.5 [overflow-wrap:anywhere]">{sub}</div>}
    </div>
  )
}

/** "4 of 5 covered" · "none to cover" · "paper: the runner's" */
export function stopsText(p: Performance): string {
  if (p.money === 'paper') return 'paper: the runner holds them'
  if (p.stops_total == null) return '—'
  if (p.stops_total === 0) return 'no open positions'
  return `${p.stops_covered} of ${p.stops_total} covered`
}

export function PerformancePanel({ p }: { p: Performance }) {
  const word = p.money ? MONEY_WORD[p.money] : ''
  return (
    <Panel id="performance" title="How the money is doing" span={12}
      subtitle={p.book_id ? `${word} book · P&L is gross of fees; the return takes deposits out` : undefined}>
      {p.book_id == null ? (
        <p className="text-ink2 mt-4">No book trades this strategy yet.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3.5">
            <Tile label="Realized P&L" sub="closed trades"><Delta value={p.realized_pnl}>{signedMoney(p.realized_pnl)}</Delta></Tile>
            <Tile label="Unrealized P&L" sub={`${p.positions} open position${p.positions === 1 ? '' : 's'} at the last price`}>
              <Delta value={p.unrealized_pnl}>{signedMoney(p.unrealized_pnl)}</Delta>
            </Tile>
            <Tile label="Total P&L"><Delta value={p.total_pnl}>{signedMoney(p.total_pnl)}</Delta></Tile>
            <Tile label="Return since start"
              sub={p.since ? `${p.capital_basis || 'deposit-adjusted'} · since ${monthLabel(p.since, true)}` : p.capital_basis}>
              {p.return_pct == null ? <Missing /> : <Delta value={p.return_pct} digits={1}>{pct(p.return_pct, 1)}</Delta>}
            </Tile>
            <Tile label="Deployed" sub={p.capital != null ? `of ${money(p.capital, false)} capital` : 'capital not reported'}>
              {money(p.deployed, false)}{p.deployed_pct != null && <span className="text-xs text-ink3"> · {Math.round(p.deployed_pct)}%</span>}
            </Tile>
            <Tile label="Stop coverage" sub="a stop on record at the broker">{stopsText(p)}</Tile>
            <Tile label="Drawdown now" sub="below the running peak">
              {p.drawdown_now_pct == null ? <Missing /> : pct(p.drawdown_now_pct, 1)}
            </Tile>
            <Tile label="Worst drawdown" sub={p.days != null ? `over ${p.days} days of history` : undefined}>
              {p.drawdown_worst_pct == null ? <Missing /> : pct(p.drawdown_worst_pct, 1)}
            </Tile>
          </div>
          {p.unavailable.length > 0 && (
            <ul className="mt-3 text-xs text-ink3 flex flex-col gap-1">
              {p.unavailable.map((line) => <li key={line}>{line}</li>)}
            </ul>
          )}
        </>
      )}
    </Panel>
  )
}
