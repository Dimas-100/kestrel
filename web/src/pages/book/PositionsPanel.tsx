import { Empty } from '../../charts/marks'
import { Delta, Missing, Panel } from '../../components/bits'
import { StopCell } from '../../components/StopCell'
import type { BookView } from '../../lib/api'
import { monthLabel, num, signedMoney } from '../../lib/format'

/** This book's open positions. A missing stop is flagged in words (never colour alone), a stop that is simply not
 *  on record is told apart from one the source says is missing, and a strategy that exits on a signal says so.
 *  The marks' date and the source's own notes sit under the table. */
export function PositionsPanel({ v }: { v: BookView }) {
  const positions = v.positions
  const marks = v.book.prices_as_of
    ? `marks from ${monthLabel(v.book.prices_as_of, true)} (${v.freshness})` : 'marks: date not reported'
  const protection = v.book.protection === 'signal' ? 'exits on a signal, no resting stop'
    : v.book.protection === 'stop' ? 'a resting stop on every lot' : 'protection not stated'
  return (
    <Panel id="positions" title="Open positions" subtitle={`${positions.length} open · ${protection} · ${marks}`}
      span={6} height={300}>
      {positions.length === 0 ? (
        <Empty>No open positions.</Empty>
      ) : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 230 }}>
          {/* 480, not 640 (screenshot pass, 2026-09-28): 640 was sized for "resting (level not reported)" on one
              line; now that it wraps, this 8-column table's own content is ~488px even at 1440px wide, so the
              taller floor hid Days and P/L behind an unscrolled edge with no visible scrollbar to say so */}
          <table className="tbl" style={{ minWidth: 480 }}>
            <thead>
              <tr>
                <th>Symbol</th><th className="r">Qty</th><th className="r">Entry</th><th className="r">Last</th>
                <th style={{ paddingLeft: 12 }}>Stop</th><th className="r">Room</th><th className="r">Days</th>
                <th className="r">P/L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => (
                // book, symbol and opened day: two lots of one symbol are two rows (the index settles a same-day pair)
                <tr key={`${v.book.id}-${p.symbol}-${p.opened}-${i}`}>
                  <td className="num font-semibold">{p.symbol}</td>
                  <td className="r num">{num(p.quantity, 0)}</td>
                  <td className="r num">{num(p.entry_price)}</td>
                  <td className="r num">{num(p.last_price)}</td>
                  <td style={{ paddingLeft: 12 }}>
                    <StopCell stopPrice={p.stop_price} stopResting={p.stop_resting} flag={p.flag} />
                  </td>
                  <td className="r num">{p.room_pct == null ? <Missing /> : `${num(p.room_pct, 1)}%`}</td>
                  <td className="r num">{p.days}</td>
                  <td className="r" style={{ whiteSpace: 'nowrap' }}><Delta value={p.pnl}>{signedMoney(p.pnl)}</Delta></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {v.notes.length > 0 && (
        <ul className="mt-2 text-xs text-ink3 flex flex-col gap-0.5">
          {v.notes.map((n) => <li key={n}>{n}</li>)}
        </ul>
      )}
    </Panel>
  )
}
