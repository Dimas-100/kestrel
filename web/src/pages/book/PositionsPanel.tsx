import { Empty } from '../../charts/marks'
import { Delta, Missing, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { BookView } from '../../lib/api'
import { num, signedMoney } from '../../lib/format'

/** This book's open positions. A missing stop is flagged in words (never colour alone). */
export function PositionsPanel({ v }: { v: BookView }) {
  const positions = v.positions
  return (
    <Panel id="positions" title="Open positions" subtitle={`${positions.length} open`} span={6} height={300}>
      {positions.length === 0 ? (
        <Empty>No open positions.</Empty>
      ) : (
        <div className="table-scroll overflow-y-auto mt-3.5" style={{ maxHeight: 230 }}>
          <table className="tbl" style={{ minWidth: 640 }}>
            <thead>
              <tr>
                <th>Symbol</th><th className="r">Qty</th><th className="r">Entry</th><th className="r">Last</th>
                <th style={{ paddingLeft: 12 }}>Stop</th><th className="r">Room</th><th className="r">Days</th>
                <th className="r">P/L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.symbol}>
                  <td className="num font-semibold">{p.symbol}</td>
                  <td className="r num">{num(p.quantity, 0)}</td>
                  <td className="r num">{num(p.entry_price)}</td>
                  <td className="r num">{num(p.last_price)}</td>
                  <td style={{ paddingLeft: 12 }}>
                    {p.flag === 'no_stop' ? (
                      <span className="inline-flex items-center gap-1.5 text-xs whitespace-nowrap"
                        style={{ color: 'var(--serious)' }}>
                        <Icon name="shield" size={13} />No stop
                      </span>
                    ) : p.stop_price == null ? (
                      <span className="text-xs text-ink3 whitespace-nowrap">resting (level not reported)</span>
                    ) : (
                      <span className="num">{num(p.stop_price)}</span>
                    )}
                  </td>
                  <td className="r num">{p.room_pct == null ? <Missing /> : `${num(p.room_pct, 1)}%`}</td>
                  <td className="r num">{p.days}</td>
                  <td className="r"><Delta value={p.pnl}>{signedMoney(p.pnl)}</Delta></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
