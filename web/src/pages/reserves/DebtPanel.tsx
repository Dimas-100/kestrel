// Every debt account: what is owed, its limit and utilization, and its rate. A negative balance is a credit balance
// (paid past zero), never shown as a negative dollar amount.
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import type { DebtLine } from '../../lib/api'
import { money, num } from '../../lib/format'

function OwedCell({ owed }: { owed: number }) {
  if (owed < 0) return <span className="text-ink2">{money(Math.abs(owed))} credit balance</span>
  return <span className="num">{money(owed)}</span>
}

export function DebtPanel({ debts }: { debts: DebtLine[] }) {
  return (
    <Panel id="debt" title="Debt" subtitle={debts.length > 0 ? 'Largest balance first' : undefined} span={6}>
      {debts.length === 0 ? (
        <Empty>No debt accounts yet.</Empty>
      ) : (
        <div className="table-scroll mt-3.5">
          {/* 480, not the 640-ish a 5-numeric-column table might suggest: at span-6 this panel's own content width
              is ~510px even at 1440px wide, so a taller floor forces a needless horizontal scroll on desktop
              (screenshot pass, 2026-09-28) -- narrower layouts still scroll here, which is `.table-scroll`'s job */}
          <table className="tbl" style={{ minWidth: 480 }}>
            <thead>
              <tr><th>Account</th><th className="r">Owed</th><th className="r">Limit</th><th className="r">Utilization</th>
                <th className="r">Rate</th></tr>
            </thead>
            <tbody>
              {debts.map((d) => (
                <tr key={d.id}>
                  <td>
                    <div className="font-medium">{d.name}</div>
                    {d.institution && <div className="text-xs text-ink3">{d.institution}</div>}
                  </td>
                  <td className="r"><OwedCell owed={d.owed} /></td>
                  <td className="r num">{d.limit == null ? <Missing /> : money(d.limit, false)}</td>
                  <td className="r num">{d.utilization_pct == null ? <Missing /> : `${num(d.utilization_pct, 1)}%`}</td>
                  <td className="r num">{d.rate_pct == null ? <Missing /> : `${num(d.rate_pct, 1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
