// Every cash account: balance and rate.
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import type { CashLine } from '../../lib/api'
import { money, num } from '../../lib/format'

export function CashPanel({ cash }: { cash: CashLine[] }) {
  return (
    <Panel id="cash" title="Cash" subtitle={cash.length > 0 ? 'Largest first' : undefined} span={6}>
      {cash.length === 0 ? (
        <Empty>No cash accounts yet.</Empty>
      ) : (
        <div className="table-scroll mt-3.5">
          <table className="tbl">
            <thead><tr><th>Account</th><th className="r">Value</th><th className="r">Rate</th></tr></thead>
            <tbody>
              {cash.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div className="font-medium">{c.name}</div>
                    {c.institution && <div className="text-xs text-ink3">{c.institution}</div>}
                  </td>
                  <td className="r num">{money(c.value)}</td>
                  <td className="r num">{c.rate_pct == null ? <Missing /> : `${num(c.rate_pct, 1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
