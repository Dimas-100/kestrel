import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Missing, Panel, type Sort, SortHeader, toggleSort } from '../../components/bits'
import { Icon } from '../../components/Icon'
import { type StrategyView, type TradeRow, useShell } from '../../lib/api'
import { monthLabel, num, pct, signedMoney } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'
import { reasonWord } from './Anatomy'

type SortKey = 'closed' | 'return' | 'pnl'

const VALUE: Record<SortKey, (t: TradeRow) => string | number> = {
  closed: (t) => `${t.closed}|${t.opened}|${t.symbol}`,
  return: (t) => t.return_pct,
  pnl: (t) => t.pnl,
}

/** "system" · "hand" · "—" */
export const byWord = (by: TradeRow['entry_by']) => by ?? '—'

/** The desk's own verdict, as a mark with hidden text: a check for followed, a warning for off-plan, a dash for
 *  not scored */
export function Plan({ t }: { t: TradeRow }) {
  if (t.plan_followed == null) return <span className="text-ink3" title="not scored">—<span className="sr-only">not scored</span></span>
  const ok = t.plan_followed
  return (
    <span className="inline-flex items-center gap-1" style={{ color: ok ? 'var(--good)' : 'var(--warn)' }}
      title={t.note || (ok ? 'followed the plan' : 'off-plan')}>
      <Icon name={ok ? 'check' : 'alert'} size={14} />
      <span className="sr-only">{ok ? 'followed the plan' : `off-plan${t.note ? `: ${t.note}` : ''}`}</span>
    </span>
  )
}

/** "18 Sep" this year, "26 Nov 2025" before it */
function day(iso: string, year: number): string {
  return Number(iso.slice(0, 4)) === year ? monthLabel(iso, true) : `${monthLabel(iso, true)} ${iso.slice(0, 4)}`
}

/** Every closed trade in the primary book, newest first; sortable by closed date, return and P/L. */
export function TradesPanel({ v }: { v: StrategyView }) {
  const [sort, setSort] = useState<Sort<SortKey>>({ key: 'closed', dir: 'desc' })
  const shell = useShell()
  const year = new Date(shell.data?.now ?? Date.now()).getUTCFullYear()
  const word = MONEY_WORD[v.book ?? 'real']
  const onSort = (key: SortKey) => setSort((s) => toggleSort(s, key))
  const sorted = [...v.trades].sort((a, b) => {
    const [x, y] = [VALUE[sort.key](a), VALUE[sort.key](b)]
    const order = x < y ? -1 : x > y ? 1 : 0
    return sort.dir === 'desc' ? -order : order
  })
  const origin = v.trades.some((t) => t.entry_by != null)
  const scored = v.trades.some((t) => t.plan_followed != null)
  return (
    <Panel id="trades" title="All trades" span={12}
      subtitle={`${word} book · ${v.trades.length} closed trades${origin ? ' · hand-placed and system-placed together' : ''}`}>
      {v.trades.length === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 560 }}>
          <table className="tbl" style={{ minWidth: origin ? 980 : 760, '--row': '44px' } as CSSProperties}>
            <thead>
              <tr>
                <th>Symbol</th><th>Opened</th>
                <SortHeader label="Closed" k="closed" sort={sort} onSort={onSort} />
                <th className="r">Days held</th>
                <SortHeader label="Return" k="return" sort={sort} onSort={onSort} right />
                <th className="r">R</th>
                <SortHeader label="P/L" k="pnl" sort={sort} onSort={onSort} right />
                <th style={{ paddingLeft: 16 }}>Why it closed</th>
                {origin && <><th>Entry</th><th>Exit</th><th>Rules</th></>}
                {scored && <th>Plan</th>}
              </tr>
            </thead>
            <tbody>
              {sorted.map((t, i) => (
                <tr key={`${t.symbol}-${t.opened}-${t.closed}-${i}`}>
                  <td>
                    <div className="flex items-center gap-2.5">
                      <BookMark kind={t.money} color="var(--s2)" />
                      <span className="num font-semibold">{t.symbol}</span>
                      <span className="sr-only">{t.money}</span>
                    </div>
                  </td>
                  <td className="num text-ink2">{day(t.opened, year)}</td>
                  <td className="num text-ink2">{day(t.closed, year)}</td>
                  <td className="r num">{t.days_held}</td>
                  <td className="r"><Delta value={t.return_pct}>{pct(t.return_pct, 2)}</Delta></td>
                  <td className="r num">{t.r_multiple == null ? <Missing /> : num(t.r_multiple, 2)}</td>
                  <td className="r"><Delta value={t.pnl}>{signedMoney(t.pnl)}</Delta></td>
                  <td style={{ paddingLeft: 16 }}>{reasonWord(t.exit_reason)}</td>
                  {origin && <>
                    <td className="text-xs text-ink2">{byWord(t.entry_by)}</td>
                    <td className="text-xs text-ink2">{byWord(t.exit_by)}</td>
                    <td className="text-xs text-ink2 whitespace-nowrap">{t.rules_version || <Missing />}</td>
                  </>}
                  {scored && <td><Plan t={t} /></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
