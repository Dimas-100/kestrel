// Every target, grouped by the account it scopes to (off plan first inside each group), then the rest.
import { Link } from '@tanstack/react-router'
import { Empty } from '../../charts/marks'
import { Missing, Panel } from '../../components/bits'
import type { AccountTargets, TargetRow } from '../../lib/api'
import { money, num } from '../../lib/format'
import { PlanBar } from './PlanBar'

const STATUS_WORD: Record<TargetRow['status'], string> = {
  on: 'On plan', over: 'Over', under: 'Under', unknown: 'Unknown',
}
const STATUS_COLOR: Record<TargetRow['status'], string> = {
  on: 'var(--ink3)', over: 'var(--warn)', under: 'var(--warn)', unknown: 'var(--ink3)',
}

function shape(value: number, unit: TargetRow['unit']): string {
  return unit === '%' ? `${num(value, 1)}%` : `${num(value, 1)}x`
}

/** The gap, worded for a person. `moneyGap` is true only for a row scoped to a real account (the accounts[] list) —
 *  an unscoped row's gap is in percentage points or ratio units, never money kestrel can't compute. */
function gapLine(row: TargetRow, moneyGap: boolean): string | null {
  if (row.gap == null) return null
  if (row.status === 'on') return 'On plan'
  const amount = row.unit === 'x' ? shape(Math.abs(row.gap), 'x')
    : moneyGap ? money(Math.abs(row.gap)) : `${num(Math.abs(row.gap), 1)} pts`
  return `${amount} ${row.gap_text}`
}

function TargetRows({ rows, moneyGap }: { rows: TargetRow[]; moneyGap: boolean }) {
  return (
    <ul>
      {rows.map((row) => (
        <li key={row.id} className="py-3 border-t border-line">
          <div className="flex items-baseline justify-between gap-3">
            <div className="min-w-0">
              <span className="text-sm font-medium">{row.label}</span>
              {row.symbols.length > 0 && <span className="text-xs text-ink3 ml-1.5">{row.symbols.join(', ')}</span>}
            </div>
            <span className="text-xs whitespace-nowrap" style={{ color: STATUS_COLOR[row.status] }}>
              {STATUS_WORD[row.status]}
            </span>
          </div>
          <PlanBar row={row} />
          <div className="flex items-center justify-between text-xs text-ink3 mt-1 gap-3">
            <span>
              {row.actual == null ? <Missing /> : shape(row.actual, row.unit)} actual
              {row.target != null && <> · {shape(row.target, row.unit)} aim</>}
            </span>
            <span className="text-right">{gapLine(row, moneyGap) ?? <Missing />}</span>
          </div>
          {row.note && <p className="text-xs text-ink3 mt-1">{row.note}</p>}
        </li>
      ))}
    </ul>
  )
}

export function TargetsPanel({ accounts, unscoped }: { accounts: AccountTargets[]; unscoped: TargetRow[] }) {
  const empty = accounts.length === 0 && unscoped.length === 0
  return (
    <Panel id="targets" title="Targets" subtitle={empty ? undefined : 'Off plan first, in each account'} span={12}>
      {empty ? (
        <Empty>No targets yet. An investing feed sends what each account should hold.</Empty>
      ) : (
        <>
          {accounts.map((a) => (
            <div key={a.account_id} className="mt-3.5 first:mt-2.5">
              <Link to="/accounts/$accountId" params={{ accountId: a.account_id }}
                className="label" style={{ color: 'var(--ink2)' }}>
                {a.name}
              </Link>
              <TargetRows rows={a.rows} moneyGap />
            </div>
          ))}
          {unscoped.length > 0 && (
            <div className="mt-3.5 first:mt-2.5">
              <div className="label">Across every account</div>
              <TargetRows rows={unscoped} moneyGap={false} />
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
