// Every debt as a card, largest balance first: what is owed, the utilization as a bar (the word "high" from thirty
// percent) or "No limit on record", the APR with a year of interest or "APR not on record", and the balance's date —
// a warning when it is over a week old. A full-width row of its own: on a desktop every card side by side (at least
// three tracks, so a lone card isn't stretched), wrapping below 240 px a card, one column on a phone (spec 2026-10-08
// reserves estimates §3.6). A negative balance is a credit balance (paid past zero), never shown as a negative dollar amount.
import type { ReactNode } from 'react'
import { Empty } from '../../charts/marks'
import { Icon } from '../../components/Icon'
import { InstitutionTile, Panel } from '../../components/bits'
import type { DebtLine, ReservesTotals } from '../../lib/api'
import { money, monthLabel, num } from '../../lib/format'
import { staleNote } from './CashPanel'

const HIGH_PCT = 30

function Utilization({ d }: { d: DebtLine }) {
  if (d.utilization_pct == null || d.limit == null) {
    return <Fact icon="info">No limit on record</Fact>
  }
  const pct = d.utilization_pct
  const high = pct >= HIGH_PCT
  return (
    <div>
      <div role="img" aria-label={`${d.name}: ${num(pct, 1)}% of its limit`}
        className="relative h-1.5 rounded-full overflow-hidden bg-panel2" style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
        <span className="absolute inset-y-0 left-0" style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: 'var(--ink2)' }} />
      </div>
      <div className="prose flex flex-wrap items-center gap-x-1 gap-y-0.5 text-xs text-ink2 mt-1.5">
        <span className="num">{num(pct, 1)}%</span> of a <span className="num">{money(d.limit, false)}</span> limit
        {high && (
          <span className="inline-flex items-center gap-1" style={{ color: 'var(--warn)' }}>
            <Icon name="alert" size={12} />high
          </span>
        )}
      </div>
    </div>
  )
}

function Fact({ icon, warn = false, children }: { icon: 'info' | 'clock' | 'alert'; warn?: boolean; children: ReactNode }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-ink2">
      <Icon name={icon} size={13} style={{ color: warn ? 'var(--warn)' : 'var(--ink3)' }} />
      <span className="min-w-0">{warn && <span className="sr-only">Warning: </span>}{children}</span>
    </div>
  )
}

function DebtCard({ d, viewDay }: { d: DebtLine; viewDay: string }) {
  const stale = staleNote(d.as_of, viewDay)
  return (
    <li className="rounded-[10px] p-3.5 flex flex-col gap-2.5 min-w-0" style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
      <div className="flex items-start gap-2.5 min-w-0">
        <InstitutionTile institution={d.institution || d.name} category="debt" />
        <div className="min-w-0">
          <div className="font-medium text-[13px] leading-snug">{d.name}</div>
          {d.institution && <div className="text-xs text-ink3">{d.institution}</div>}
        </div>
      </div>
      <div>
        <div className="label">Owed</div>
        <div className="mt-1">
          {d.owed < 0
            ? <span className="text-ink2">{money(Math.abs(d.owed))} credit balance</span>
            : <span className="num text-[20px] font-semibold tracking-[-0.02em]">{money(d.owed)}</span>}
        </div>
      </div>
      <Utilization d={d} />
      {d.rate_pct == null
        ? <Fact icon="info">APR not on record</Fact>
        : (
          <div className="prose text-xs text-ink2">
            <span className="num text-ink1">{num(d.rate_pct, 1)}%</span> APR
            {d.yearly_cost != null && <> · about <span className="num">{money(d.yearly_cost)}</span> a year in interest</>}
          </div>
        )}
      {stale
        ? <Fact icon="clock" warn>{stale}, over a week old</Fact>
        : <Fact icon="clock">balance from {monthLabel(d.as_of.slice(0, 10), true)}</Fact>}
    </li>
  )
}

/** One track per card (three at least, four at most) while each stays 240 px or wider; fewer, wrapping, when not. */
export function cardColumns(count: number): string {
  const n = Math.min(4, Math.max(3, count))
  return `repeat(auto-fill, minmax(max(240px, calc((100% - ${(n - 1) * 12}px) / ${n})), 1fr))`
}

export function DebtPanel({ debts, totals, viewDay }: { debts: DebtLine[]; totals: ReservesTotals; viewDay: string }) {
  const util = totals.utilization_pct
  const subtitle = debts.length === 0 ? undefined
    : util == null ? 'Largest balance first · no limits on record to measure utilization'
      : `${num(util, 1)}% of limits used${totals.limited_count < totals.debt_count
        ? `, over the ${totals.limited_count} with a limit on record` : ''} · largest balance first`
  return (
    <Panel id="debt" title="Debt" subtitle={subtitle} span={12}>
      {debts.length === 0 ? (
        <Empty>No debt accounts yet.</Empty>
      ) : (
        <ul className="grid gap-3 mt-3.5" style={{ gridTemplateColumns: cardColumns(debts.length) }}>
          {debts.map((d) => <DebtCard key={d.id} d={d} viewDay={viewDay} />)}
        </ul>
      )}
    </Panel>
  )
}
