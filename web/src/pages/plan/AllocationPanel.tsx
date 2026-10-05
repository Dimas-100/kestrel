// How each account sits against its plan: a bar of what is held and a dotted bar of the aims, one block per account,
// off-plan accounts first; the legend says each target's gap in words; a table of every target behind the toggle
// (spec 2026-10-05 plan page §2.3). A ratio target, or one with no account, keeps its band bar.
import { Link } from '@tanstack/react-router'
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { CATEGORY_COLOR, Missing, Panel, Seg } from '../../components/bits'
import type { AccountTargets, TargetRow } from '../../lib/api'
import { money, num } from '../../lib/format'
import { allocationSegments, type Segment } from './allocation'
import { PlanBar, unitText } from './PlanBar'

const VIEWS = ['Chart', 'Table'] as const
const LABEL_MIN_PCT = 12 // a segment narrower than this carries its label in the legend only

export const STATUS_WORD: Record<TargetRow['status'], string> = {
  on: 'On plan', over: 'Over', under: 'Under', unknown: 'Unknown',
}
const STATUS_COLOR: Record<TargetRow['status'], string> = {
  on: 'var(--ink3)', over: 'var(--warn)', under: 'var(--warn)', unknown: 'var(--ink3)',
}

/** The gap, worded for a person, formatted strictly by `gap_unit` — never inferred from which list the row came
 *  from. A zero-value account grouped under a real account still reports points, not a bogus dollar figure. */
export function gapLine(row: TargetRow): string | null {
  if (row.gap == null || row.gap_unit == null) return null
  if (row.status === 'on') return 'On plan'
  if (row.gap_unit === 'money') return `${money(Math.abs(row.gap))} ${row.gap_text}`
  // a points/ratio gap under 0.1 would round to "0.0" at one decimal and read as no gap at all: show two then
  const digits = Math.abs(row.gap) < 0.1 ? 2 : 1
  const amount = `${num(Math.abs(row.gap), digits)}${row.gap_unit === 'x' ? 'x' : ' pts'}`
  return `${amount} ${row.gap_text}`
}

const offPlan = (rows: TargetRow[]) => rows.filter((r) => r.status === 'over' || r.status === 'under').length

function bandText(row: TargetRow): string {
  const short = (v: number) => num(v, Number.isInteger(v) ? 0 : 1)
  const suffix = row.unit === '%' ? '%' : 'x'
  if (row.low != null && row.high != null) return `${short(row.low)}–${short(row.high)}${suffix}`
  if (row.low != null) return `from ${short(row.low)}${suffix}`
  if (row.high != null) return `up to ${short(row.high)}${suffix}`
  return '—'
}

/** One bar: segments abreast with 2 px of panel between them, a filled one for what is held, a dotted one for the
 *  aim (the expected convention), the remainder of the held bar in the neutral cash grey as Other. */
function Bar({ segments, other, color, dotted, label }: {
  segments: Segment[]; other: number; color: string; dotted: boolean; label: string
}) {
  const seg = (s: Segment, fill: string, text: string): CSSProperties => ({
    width: `${s.pct}%`, minWidth: s.pct > 0 ? 3 : 0, background: dotted ? 'transparent' : fill,
    border: dotted ? '1.5px dotted var(--ref)' : 'none', color: text, borderRadius: 3,
  })
  return (
    <div role="img" aria-label={label} className="flex h-5" style={{ gap: 2 }}>
      {segments.map((s) => (
        <div key={s.id} className="flex items-center overflow-hidden" style={seg(s, color, dotted ? 'var(--ink2)' : 'var(--on-acc)')}>
          {s.pct >= LABEL_MIN_PCT && (
            <span className="text-[10px] font-medium px-1.5 whitespace-nowrap">{s.label} {num(s.pct, 0)}%</span>
          )}
        </div>
      ))}
      {!dotted && other > 0 && (
        <div className="flex items-center overflow-hidden" style={{ width: `${other}%`, minWidth: 3, background: 'var(--s3)',
          opacity: 0.55, borderRadius: 3, color: 'var(--on-acc)' }}>
          {other >= LABEL_MIN_PCT && <span className="text-[10px] font-medium px-1.5 whitespace-nowrap">Other {num(other, 0)}%</span>}
        </div>
      )}
    </div>
  )
}

function LegendRow({ row, aim }: { row: TargetRow; aim: { pct: number; fromBand: boolean } | null }) {
  const off = row.status === 'over' || row.status === 'under'
  const gap = gapLine(row)
  return (
    <li className="flex items-baseline justify-between gap-3 py-1 text-xs flex-wrap">
      <span className="min-w-0">
        <span className="font-medium text-ink1">{row.label}</span>
        {row.symbols.length > 0 && <span className="text-ink3 ml-1.5">{row.symbols.join(', ')}</span>}
      </span>
      <span className="num text-ink2 whitespace-nowrap">
        {row.actual == null ? '—' : unitText(row.actual, row.unit)}
        {' → '}
        {row.target != null ? unitText(row.target, row.unit) : aim?.fromBand ? `band ${bandText(row)}` : '—'}
        {row.target != null && (row.low != null || row.high != null) && <span className="text-ink3"> ({bandText(row)})</span>}
      </span>
      <span className="whitespace-nowrap" style={{ color: STATUS_COLOR[row.status] }}>
        {STATUS_WORD[row.status]}{off && gap && <><span className="text-ink3"> · </span><span className="text-ink3">{gap}</span></>}
      </span>
    </li>
  )
}

function AccountBlock({ a, category }: { a: AccountTargets; category: string }) {
  const alloc = allocationSegments(a.rows)
  const shares = a.rows.filter((r) => r.unit === '%' && r.actual != null)
  const ratios = a.rows.filter((r) => !(r.unit === '%' && r.actual != null))
  const color = CATEGORY_COLOR[category] ?? 'var(--s1)'
  const known = a.rows.filter((r) => r.status !== 'unknown').length
  return (
    <section role="group" aria-label={a.name} className="py-4 border-t border-line first:border-t-0 first:pt-2">
      <div className="flex items-baseline justify-between gap-3">
        {a.known ? (
          <Link to="/accounts/$accountId" params={{ accountId: a.account_id }} className="text-sm font-semibold"
            style={{ color: 'var(--ink1)' }}>{a.name}</Link>
        ) : <span className="text-sm font-semibold">{a.name}</span>}
        <span className="text-xs text-ink3 whitespace-nowrap">
          {known > 0 ? `${known - offPlan(a.rows)} of ${known} on plan` : 'nothing measured yet'}
        </span>
      </div>
      {shares.length > 0 && (
        <div className="mt-3 flex flex-col gap-1.5">
          <Bar segments={alloc.actual} other={alloc.other} color={color} dotted={false} label={`${a.name}, what is held`} />
          <Bar segments={alloc.aim} other={0} color={color} dotted label={`${a.name}, the aim`} />
          <div className="flex justify-between text-[10px] text-ink3"><span>held</span><span>aim, dotted</span></div>
        </div>
      )}
      <ul className="mt-2">
        {a.rows.map((row) => {
          const aim = alloc.aim.find((s) => s.id === row.id) ?? null
          return <LegendRow key={row.id} row={row} aim={aim} />
        })}
      </ul>
      {ratios.filter((r) => r.unit === 'x').map((row) => (
        <div key={row.id} className="mt-2"><PlanBar row={row} /></div>
      ))}
    </section>
  )
}

function OtherTargets({ rows }: { rows: TargetRow[] }) {
  return (
    <section role="group" aria-label="Other targets" className="py-4 border-t border-line">
      <div className="label">Other targets</div>
      <ul>
        {rows.map((row) => (
          <li key={row.id} className="py-2">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-sm font-medium">{row.label}</span>
              <span className="text-xs whitespace-nowrap" style={{ color: STATUS_COLOR[row.status] }}>{STATUS_WORD[row.status]}</span>
            </div>
            <PlanBar row={row} />
            <div className="flex items-center justify-between text-xs text-ink3 mt-1 gap-3">
              <span>
                {row.actual == null ? <Missing /> : unitText(row.actual, row.unit)} actual
                {row.target != null && <> · {unitText(row.target, row.unit)} aim</>}
              </span>
              <span className="text-right">{gapLine(row) ?? <Missing />}</span>
            </div>
            {row.note && <p className="text-xs text-ink3 mt-1">{row.note}</p>}
          </li>
        ))}
      </ul>
    </section>
  )
}

function TargetsTable({ accounts, unscoped }: { accounts: AccountTargets[]; unscoped: TargetRow[] }) {
  const all = [...accounts.flatMap((a) => a.rows.map((row) => ({ row, where: a.name }))),
               ...unscoped.map((row) => ({ row, where: '' }))]
  return (
    <div className="table-scroll mt-3.5">
      <table className="tbl" style={{ minWidth: 720, '--row': '40px' } as CSSProperties}>
        <thead>
          <tr>
            <th>Target</th><th>Account</th><th className="r">Actual</th><th className="r">Aim</th><th className="r">Band</th>
            <th>Status</th><th>Gap</th>
          </tr>
        </thead>
        <tbody>
          {all.map(({ row, where }) => (
            <tr key={row.id}>
              <td className="font-medium">{row.label}{row.symbols.length > 0 && <span className="text-xs text-ink3 ml-1.5">{row.symbols.join(', ')}</span>}</td>
              <td className="text-ink2">{where || <Missing />}</td>
              <td className="r num">{row.actual == null ? <Missing /> : unitText(row.actual, row.unit)}</td>
              <td className="r num">{row.target == null ? <Missing /> : unitText(row.target, row.unit)}</td>
              <td className="r num">{bandText(row)}</td>
              <td style={{ color: STATUS_COLOR[row.status] }}>{STATUS_WORD[row.status]}</td>
              <td className="text-ink2">{gapLine(row) ?? <Missing />}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function AllocationPanel({ accounts, unscoped }: { accounts: AccountTargets[]; unscoped: TargetRow[] }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const empty = accounts.length === 0 && unscoped.length === 0
  const ordered = [...accounts].sort((a, b) => offPlan(b.rows) - offPlan(a.rows))
  return (
    <Panel id="allocation" title="Allocation against plan" span={7}
      subtitle={empty ? undefined : 'What each account holds against its aim, off plan first'}
      actions={!empty && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {empty ? (
        <Empty>No targets yet. An investing feed sends what each account should hold.</Empty>
      ) : view === 'Table' ? (
        <TargetsTable accounts={ordered} unscoped={unscoped} />
      ) : (
        <div className="mt-1">
          {ordered.map((a) => <AccountBlock key={a.account_id} a={a} category="long_term" />)}
          {unscoped.length > 0 && <OtherTargets rows={unscoped} />}
        </div>
      )}
    </Panel>
  )
}
