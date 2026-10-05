// Every cash account, largest first: name and institution, its share of all the cash as a bar, the balance and the
// rate. A balance older than a week says when it is from: a manual balance can sit for months.
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import type { CashLine } from '../../lib/api'
import { money, monthLabel, num } from '../../lib/format'

const STALE_DAYS = 7

/** "balance from 4 Aug" when the balance is older than a week against the view's day, else null. */
export function staleNote(asOf: string, viewDay: string): string | null {
  const age = (Date.parse(`${viewDay.slice(0, 10)}T00:00:00Z`) - Date.parse(`${asOf.slice(0, 10)}T00:00:00Z`)) / 86_400_000
  return age > STALE_DAYS ? `balance from ${monthLabel(asOf.slice(0, 10), true)}` : null
}

function Share({ name, pct }: { name: string; pct: number | null }) {
  if (pct == null) return <Missing />
  return (
    <div role="img" aria-label={`${name}: ${num(pct, 1)}% of your cash`} className="flex items-center justify-end gap-2">
      <span className="relative w-14 h-1.5 rounded-full overflow-hidden bg-panel2" style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
        <span className="absolute inset-y-0 left-0" style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: 'var(--s3)' }} />
      </span>
      <span className="num text-xs min-w-[46px] text-right">{num(pct, 1)}%</span>
    </div>
  )
}

export function CashPanel({ cash, viewDay }: { cash: CashLine[]; viewDay: string }) {
  return (
    <Panel id="cash" title="Cash" subtitle={cash.length > 0 ? 'Largest first' : undefined} span={6}>
      {cash.length === 0 ? (
        <Empty>No cash accounts yet.</Empty>
      ) : (
        <div className="table-scroll mt-3.5">
          <table className="tbl">
            <thead><tr><th>Account</th><th className="r">Share</th><th className="r">Value</th><th className="r">Rate</th></tr></thead>
            <tbody>
              {cash.map((c) => {
                const stale = staleNote(c.as_of, viewDay)
                return (
                  <tr key={c.id}>
                    <td>
                      <div className="font-medium">{c.name}</div>
                      {(c.institution || stale) && (
                        <div className="text-xs text-ink3">
                          {c.institution}{c.institution && stale && ' · '}{stale}
                        </div>
                      )}
                    </td>
                    <td className="r"><Share name={c.name} pct={c.share_pct} /></td>
                    <td className="r num">{money(c.value)}</td>
                    <td className="r num">{c.rate_pct == null ? <Missing /> : `${num(c.rate_pct, 1)}%`}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  )
}
