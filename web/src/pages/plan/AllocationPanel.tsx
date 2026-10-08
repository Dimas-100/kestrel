// How each account sits against its plan (spec 2026-10-08 plan §4.3): one block per account, two abreast when there
// is room, each target one row on the account's shared scale: the band as a wash, the aim as a dotted tick (the
// expected convention), what is held as a solid bar (real money). Never stacked or normalised, so every share reads
// at its own width. A sleeve's members sit indented under it; the status word and the plan's policy are in words.
// A table of every target behind the toggle.
import { Link } from '@tanstack/react-router'
import { type CSSProperties, useState } from 'react'
import { Empty } from '../../charts/marks'
import { CATEGORY_COLOR, Missing, Panel, Seg } from '../../components/bits'
import type { AccountTargets, Rebalance, TargetRow } from '../../lib/api'
import { money, num } from '../../lib/format'
import { axisTicks, domainFor, nestRows, percentDomain, rowGeometry } from './allocation'
import { unitText } from './PlanBar'

const VIEWS = ['Chart', 'Table'] as const

export const STATUS_WORD: Record<TargetRow['status'], string> = {
  on: 'On plan', over: 'Over', under: 'Under', unknown: 'Unknown',
}
const STATUS_COLOR: Record<TargetRow['status'], string> = {
  on: 'var(--ink3)', over: 'var(--warn)', under: 'var(--warn)', unknown: 'var(--ink3)',
}
export const POLICY_WORD: Record<Rebalance, string> = {
  trades: 'Trades', contributions: 'New money only', hold: 'Hold and dilute',
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

/** What the plan does about a row off its band, in words; nothing for a trade (its gap says it) or a row on plan. */
export function policyPhrase(row: TargetRow): string | null {
  if (row.status === 'under' && row.rebalance === 'contributions') return 'steer new money here'
  if (row.status === 'under' && row.rebalance === 'hold') return 'a decision to revisit, not a buy'
  if (row.status === 'over' && row.rebalance !== 'trades') return 'dilutes with new money, no sale'
  return null
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

const pct = (f: number) => `${(f * 100).toFixed(2)}%`

/** One target on its scale: the band washed, the held share a solid bar from zero with a rounded data end, the aim
 *  a dotted tick; an actual past the scale's end stops at the edge with an arrow. */
function RangeBar({ row, domain, color }: { row: TargetRow; domain: [number, number]; color: string }) {
  const g = rowGeometry(row, domain)
  const aim = row.target != null ? `, aim ${unitText(row.target, row.unit)}` : ''
  const label = row.actual == null ? `${row.label}: not measured, band ${bandText(row)}${aim}`
    : `${row.label}: ${unitText(row.actual, row.unit)} ${row.unit === 'x' ? 'actual' : 'held'}, band ${bandText(row)}${aim}`
  const hasBand = row.low != null || row.high != null
  return (
    <div className="range-bar" role="img" aria-label={label}>
      <span className="range-track" />
      {hasBand && <span className="range-band" style={{ left: pct(g.bandStart), width: pct(Math.max(0, g.bandEnd - g.bandStart)) }} />}
      {g.actual != null && (
        <span className="range-held" style={{ width: pct(g.actual), background: color }} />
      )}
      {g.actual != null && g.clamped && (
        <span aria-hidden="true" className="range-arrow" style={{ color }}>{g.actual === 1 ? '→' : '←'}</span>
      )}
      {g.target != null && <span className="range-aim" style={{ left: pct(g.target) }} />}
    </div>
  )
}

function StatusLine({ row }: { row: TargetRow }) {
  const off = row.status === 'over' || row.status === 'under'
  const gap = off && row.rebalance === 'trades' ? gapLine(row) : null
  const phrase = policyPhrase(row)
  return (
    <div className="range-status text-xs text-ink3">
      <span style={{ color: STATUS_COLOR[row.status] }} className={off ? 'font-medium' : undefined}>
        {STATUS_WORD[row.status]}
      </span>
      {row.status === 'unknown' && <> · can&rsquo;t be measured yet</>}
      {row.target != null && <> · aim <span className="num">{unitText(row.target, row.unit)}</span></>}
      {(row.low != null || row.high != null) && <> · band <span className="num">{bandText(row)}</span></>}
      {gap && <> · <span className="num">{gap}</span></>}
      {phrase && <> · {phrase}</>}
      {row.unit === 'x' && <> · a ratio, on its own scale</>}
    </div>
  )
}

function RangeRow({ row, depth, parentLabel, domain, color }: {
  row: TargetRow; depth: 0 | 1; parentLabel: string | null; domain: [number, number]; color: string
}) {
  return (
    <li id={`target-${row.id}`} tabIndex={-1} className="range-row" data-depth={depth}>
      <div className="range-label min-w-0">
        <div className="text-sm font-medium truncate">
          {row.label}{parentLabel && <span className="sr-only">, in {parentLabel}</span>}
        </div>
        {row.symbols.length > 1 && <div className="text-[11px] text-ink3 truncate">{row.symbols.join(' · ')}</div>}
      </div>
      <RangeBar row={row} domain={domainFor(row, domain)} color={color} />
      <div className="range-figure num text-sm text-right">
        {row.actual == null ? <Missing /> : unitText(row.actual, row.unit)}
      </div>
      <StatusLine row={row} />
    </li>
  )
}

function Axis({ domain }: { domain: [number, number] }) {
  return (
    <div className="range-row range-axis" aria-hidden="true">
      <span />
      <div className="range-ticks">
        {axisTicks(domain).map((t, i) => (
          <span key={t} className="num text-[10px] text-ink3" style={{ left: `${i * 50}%` }}>{num(t, 0)}%</span>
        ))}
      </div>
      <span />
    </div>
  )
}

function AccountBlock({ a, category }: { a: AccountTargets; category: string }) {
  const domain = percentDomain(a.rows)
  const placed = nestRows(a.rows)
  const labels = new Map(a.rows.map((r) => [r.id, r.label]))
  const color = CATEGORY_COLOR[category] ?? 'var(--s1)'
  const known = a.rows.filter((r) => r.status !== 'unknown').length
  return (
    <section role="group" aria-label={a.name} className="alloc-account">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        {a.known ? (
          <Link to="/accounts/$accountId" params={{ accountId: a.account_id }} className="text-sm font-semibold"
            style={{ color: 'var(--ink1)' }}>{a.name}</Link>
        ) : <span className="text-sm font-semibold">{a.name}</span>}
        <span className="text-xs text-ink3 whitespace-nowrap">
          {known > 0 ? `${known - offPlan(a.rows)} of ${known} on plan` : 'nothing measured yet'}
          {known < a.rows.length && known > 0 && ` · ${a.rows.length - known} not measured`}
        </span>
      </div>
      <ul className="mt-2">
        {placed.map(({ row, depth }) => (
          <RangeRow key={row.id} row={row} depth={depth} domain={domain} color={color}
            parentLabel={row.parent ? labels.get(row.parent) ?? null : null} />
        ))}
      </ul>
      {a.rows.some((r) => r.unit === '%') && <Axis domain={domain} />}
      {a.untargeted_pct != null && (
        <p className="text-xs text-ink3 mt-2">
          <span className="num">{num(a.untargeted_pct, 1)}%</span> of {a.name} sits in no target, cash included.
        </p>
      )}
    </section>
  )
}

function OtherTargets({ rows }: { rows: TargetRow[] }) {
  return (
    <section role="group" aria-label="Other targets" className="alloc-account">
      <div className="text-sm font-semibold">Other targets</div>
      <ul className="mt-2">
        {rows.map((row) => (
          <RangeRow key={row.id} row={row} depth={0} parentLabel={null} domain={percentDomain([row])}
            color="var(--s3)" />
        ))}
      </ul>
    </section>
  )
}

function Key() {
  return (
    <div className="range-key text-xs text-ink3" aria-hidden="true">
      <span><i className="key-held" style={{ background: CATEGORY_COLOR.long_term }} />held</span>
      <span><i className="key-band" />band</span>
      <span><i className="key-aim" />aim</span>
    </div>
  )
}

function TargetsTable({ accounts, unscoped }: { accounts: AccountTargets[]; unscoped: TargetRow[] }) {
  const all = [...accounts.flatMap((a) => a.rows.map((row) => ({ row, where: a.name }))),
               ...unscoped.map((row) => ({ row, where: '' }))]
  return (
    <div className="table-scroll mt-3.5">
      <table className="tbl" style={{ minWidth: 860, '--row': '40px' } as CSSProperties}>
        <thead>
          <tr>
            <th>Target</th><th>Account</th><th className="r">Actual</th><th className="r">Aim</th><th className="r">Band</th>
            <th>Status</th><th>Gap</th><th>Policy</th>
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
              <td className="text-ink2">{POLICY_WORD[row.rebalance]}</td>
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
    <Panel id="allocation" title="Allocation against plan" span={12}
      subtitle={empty ? undefined : 'Each target on its account’s scale, off plan first'}
      actions={!empty && <>{view === 'Chart' && <Key />}<Seg label="View" options={VIEWS} value={view} onChange={setView} /></>}>
      {empty ? (
        <Empty>No targets yet. An investing feed sends what each account should hold.</Empty>
      ) : view === 'Table' ? (
        <TargetsTable accounts={ordered} unscoped={unscoped} />
      ) : (
        <div className="alloc-accounts mt-3">
          {ordered.map((a) => <AccountBlock key={a.account_id} a={a} category="long_term" />)}
          {unscoped.length > 0 && <OtherTargets rows={unscoped} />}
        </div>
      )}
    </Panel>
  )
}
