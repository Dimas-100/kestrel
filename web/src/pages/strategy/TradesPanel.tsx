import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { BookMark, Delta, Missing, Panel } from '../../components/bits'
import { type StrategyView, type TradeRow, useShell } from '../../lib/api'
import { monthLabel, num, pct, signedMoney } from '../../lib/format'
import { MONEY_WORD } from '../strategies/Strategies'
import { reasonWord } from './Anatomy'

type SortKey = 'closed' | 'return' | 'pnl'
interface Sort { key: SortKey; dir: 'desc' | 'asc' }

const VALUE: Record<SortKey, (t: TradeRow) => string | number> = {
  closed: (t) => `${t.closed}|${t.opened}|${t.symbol}`,
  return: (t) => t.return_pct,
  pnl: (t) => t.pnl,
}

/** "18 Sep" this year, "26 Nov 2025" before it */
function day(iso: string, year: number): string {
  return Number(iso.slice(0, 4)) === year ? monthLabel(iso, true) : `${monthLabel(iso, true)} ${iso.slice(0, 4)}`
}

function SortHeader({ label, k, sort, onSort, right = false }: {
  label: string; k: SortKey; sort: Sort; onSort: (key: SortKey) => void; right?: boolean
}) {
  const active = sort.key === k
  return (
    <th className={right ? 'r' : undefined} aria-sort={active ? (sort.dir === 'desc' ? 'descending' : 'ascending') : 'none'}>
      <button type="button" onClick={() => onSort(k)} className="uppercase tracking-[0.08em] font-medium"
        style={{ color: active ? 'var(--ink1)' : 'inherit', background: 'none', border: 0, padding: 0, cursor: 'pointer',
          font: 'inherit' }}>
        {label}
      </button>
      {active && <span aria-hidden="true"> {sort.dir === 'desc' ? '↓' : '↑'}</span>}
    </th>
  )
}

/** Every closed trade in the primary book, newest first; sortable by closed date, return and P/L. */
export function TradesPanel({ v }: { v: StrategyView }) {
  const [sort, setSort] = useState<Sort>({ key: 'closed', dir: 'desc' })
  const shell = useShell()
  const year = new Date(shell.data?.now ?? Date.now()).getUTCFullYear()
  const word = MONEY_WORD[v.book ?? 'real']
  const onSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'desc' ? 'asc' : 'desc' } : { key, dir: 'desc' }))
  const sorted = [...v.trades].sort((a, b) => {
    const [x, y] = [VALUE[sort.key](a), VALUE[sort.key](b)]
    const order = x < y ? -1 : x > y ? 1 : 0
    return sort.dir === 'desc' ? -order : order
  })
  return (
    <Panel id="trades" title="All trades" span={12} subtitle={`${word} book · ${v.trades.length} closed trades`}>
      {v.trades.length === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 560 }}>
          <table className="tbl" style={{ minWidth: 760, '--row': '44px' } as CSSProperties}>
            <thead>
              <tr>
                <th>Symbol</th><th>Opened</th>
                <SortHeader label="Closed" k="closed" sort={sort} onSort={onSort} />
                <th className="r">Days held</th>
                <SortHeader label="Return" k="return" sort={sort} onSort={onSort} right />
                <th className="r">R</th>
                <SortHeader label="P/L" k="pnl" sort={sort} onSort={onSort} right />
                <th style={{ paddingLeft: 16 }}>Why it closed</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((t) => (
                <tr key={`${t.symbol}-${t.opened}`}>
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
