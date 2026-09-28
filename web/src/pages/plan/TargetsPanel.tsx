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

/** The gap, worded for a person, formatted strictly by `gap_unit` — never inferred from which list the row came
 *  from. A zero-value account grouped under a real account still reports points, not a bogus dollar figure. */
function gapLine(row: TargetRow): string | null {
  if (row.gap == null || row.gap_unit == null) return null
  if (row.status === 'on') return 'On plan'
  const amount = row.gap_unit === 'money' ? money(Math.abs(row.gap)) : `${num(Math.abs(row.gap), 1)}${
    row.gap_unit === 'x' ? 'x' : ' pts'}`
  return `${amount} ${row.gap_text}`
}

function TargetRows({ rows }: { rows: TargetRow[] }) {
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
            <span className="text-right">{gapLine(row) ?? <Missing />}</span>
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
              {a.known ? (
                <Link to="/accounts/$accountId" params={{ accountId: a.account_id }}
                  className="label" style={{ color: 'var(--ink2)' }}>
                  {a.name}
                </Link>
              ) : (
                <div className="label">{a.name} <span className="normal-case text-ink3">· no source sent this account</span></div>
              )}
              <TargetRows rows={a.rows} />
            </div>
          ))}
          {unscoped.length > 0 && (
            <div className="mt-3.5 first:mt-2.5">
              <div className="label">Across every account</div>
              <TargetRows rows={unscoped} />
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
