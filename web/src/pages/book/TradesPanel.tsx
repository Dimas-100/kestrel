import type { CSSProperties } from 'react'
import { Empty } from '../../charts/marks'
import { Delta, Missing, Panel } from '../../components/bits'
import type { BookView } from '../../lib/api'
import { monthLabel, num, pct, signedMoney } from '../../lib/format'
import { reasonWord } from '../strategy/Anatomy'

/** "18 Sep" this year, "26 Nov 2025" before it */
function day(iso: string, year: number): string {
  return Number(iso.slice(0, 4)) === year ? monthLabel(iso, true) : `${monthLabel(iso, true)} ${iso.slice(0, 4)}`
}

/** Every closed trade in this book, newest first. */
export function TradesPanel({ v }: { v: BookView }) {
  const year = new Date(v.as_of).getUTCFullYear()
  return (
    <Panel id="book-trades" title="All trades" subtitle={`${v.trades.length} closed trades`} span={12}>
      {v.trades.length === 0 ? (
        <Empty>No closed trades yet.</Empty>
      ) : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 420 }}>
          <table className="tbl" style={{ minWidth: 720, '--row': '44px' } as CSSProperties}>
            <thead>
              <tr>
                <th>Symbol</th><th>Opened</th><th>Closed</th><th className="r">Return</th><th className="r">R</th>
                <th className="r">P/L</th><th style={{ paddingLeft: 16 }}>Why it closed</th>
              </tr>
            </thead>
            <tbody>
              {v.trades.map((t, i) => (
                <tr key={`${t.symbol}-${t.opened}-${t.closed}-${i}`}>
                  <td className="num font-semibold">{t.symbol}</td>
                  <td className="num text-ink2">{day(t.opened, year)}</td>
                  <td className="num text-ink2">{day(t.closed, year)}</td>
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
