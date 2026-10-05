// The goals in time: a line from today to the furthest goal with each dated goal on it, the next three in full
// under it, the undated ones as ongoing rows, and a table of every goal (spec 2026-10-05 plan page §2.1).
import { type CSSProperties, type PointerEvent, useState } from 'react'
import { clampTip, nearestIndex } from '../../charts/geometry'
import { useIndex, useWidth } from '../../charts/hooks'
import { Empty, Tip } from '../../charts/marks'
import { Missing, Panel, Seg } from '../../components/bits'
import type { GoalRow } from '../../lib/api'
import { longDate, money, num } from '../../lib/format'
import { ProgressRing } from './ProgressRing'
import { monthlyText, monthsBetween, nextDated, timelinePosition, yearTicks } from './timeline'

const VIEWS = ['Chart', 'Table'] as const
const NEXT = 3
const HORIZON_MONTHS = 50 * 12 // a goal further out than this (a placeholder date, say) sits at the line's end
const PAD = 8
const LINE_Y = 30
const HEIGHT = 56
const TICK_LABEL_PX = 36 // a four-digit year at 10 px, with air: ticks closer than this are thinned

function whenText(g: GoalRow): string {
  if (g.reached) return 'Reached'
  if (g.overdue && g.by) return `was due ${longDate(g.by)}`
  if (g.by) return `by ${longDate(g.by)}${g.months_left != null ? ` · ${g.months_left} months` : ''}`
  return 'ongoing'
}

/** Why a goal's progress is unknown, worded for a person. */
function unknownText(g: GoalRow): string {
  return g.missing_accounts.length > 0 ? `account not in any source: ${g.missing_accounts.join(', ')}`
    : g.unknown_reason || 'not known yet'
}

function Timeline({ goals, today }: { goals: GoalRow[]; today: string }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(900)
  const dated = goals.filter((g): g is GoalRow & { by: string } => g.by != null && g.current != null)
  const months = dated.map((g) => Math.min(HORIZON_MONTHS, monthsBetween(today, g.by)))
  const furthest = Math.max(0, ...months)
  const items = dated.map((g, i) => ({ g, pos: g.overdue ? 0 : timelinePosition(months[i], furthest) }))
    .sort((a, b) => a.pos - b.pos)
  const { index: hover, set: setHover, onKey } = useIndex(items.length)
  if (items.length === 0 || furthest <= 0) return null
  const furthestIso = dated[months.indexOf(furthest)].by
  const ticks = yearTicks(today, furthestIso, TICK_LABEL_PX / Math.max(1, width - 2 * PAD))
  const x = (pos: number) => PAD + pos * (width - 2 * PAD)
  const xs = items.map((it) => x(it.pos))
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  const dotColor = (g: GoalRow) => (g.reached ? 'var(--good)' : g.overdue ? 'var(--warn)' : 'var(--acc)')
  const h = hover == null ? null : items[hover]
  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      {/* drawn at the measured width; the viewBox lets it scale down, never overflow, should the panel narrow first */}
      <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} role="img" aria-label="Your goals in time"
        tabIndex={0} style={{ display: 'block', maxWidth: '100%', height: 'auto', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer}
        onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <line x1={PAD} x2={width - PAD} y1={LINE_Y} y2={LINE_Y} stroke="var(--line2)" />
        <line x1={PAD} x2={PAD} y1={LINE_Y - 6} y2={LINE_Y + 6} stroke="var(--ink2)" />
        <text x={PAD} y={HEIGHT - 6} fontSize={10} fill="var(--ink3)">today</text>
        {ticks.map((t) => (
          <g key={t.label}>
            <line x1={x(t.pos)} x2={x(t.pos)} y1={LINE_Y - 4} y2={LINE_Y + 4} stroke="var(--line2)" />
            <text x={x(t.pos)} y={HEIGHT - 6} fontSize={10} fill="var(--ink3)" textAnchor="middle">{t.label}</text>
          </g>
        ))}
        {items.map((it, i) => (
          <g key={it.g.id}>
            {it.g.overdue && !it.g.reached && (
              <text x={xs[i]} y={12} fontSize={10} fill="var(--warn)" textAnchor="start">overdue</text>
            )}
            <circle cx={xs[i]} cy={LINE_Y} r={hover === i ? 7 : 6} fill={dotColor(it.g)} stroke="var(--panel)"
              strokeWidth={2} />
          </g>
        ))}
      </svg>
      {h != null && hover != null && (
        <Tip left={clampTip(xs[hover], width)} top={-4} title={h.g.label} rows={[
          ['Progress', h.g.progress_pct == null ? '—' : `${num(h.g.progress_pct, 0)}%`],
          ['Now', h.g.current == null ? '—' : money(h.g.current, false)],
          ['Target', money(h.g.target, false)],
          ['When', whenText(h.g)],
        ]} />
      )}
    </div>
  )
}

function GoalCard({ g }: { g: GoalRow }) {
  const monthly = monthlyText(g)
  return (
    <article aria-labelledby={`goal-${g.id}`} className="flex gap-4">
      <ProgressRing pct={g.progress_pct ?? 0} label={g.label} reached={g.reached} />
      <div className="min-w-0">
        <h3 id={`goal-${g.id}`} className="text-sm font-semibold leading-snug">{g.label}</h3>
        <div className="text-xs text-ink3 mt-0.5">{g.scope_text}</div>
        <div className="num text-[13px] mt-2">{money(g.current ?? 0, false)} / {money(g.target, false)}</div>
        <div className="text-xs text-ink3 mt-1">{whenText(g)}</div>
        {!g.reached && !g.overdue && monthly && <p className="text-xs text-ink3 mt-1">{monthly}</p>}
      </div>
    </article>
  )
}

function OngoingRow({ g }: { g: GoalRow }) {
  const known = g.current != null && g.progress_pct != null
  return (
    <li className="py-2.5 border-t border-line">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className="text-sm font-medium">{g.label}</span>
        <span className="text-xs text-ink3">{g.scope_text}</span>
      </div>
      {known ? (
        <>
          <div role="progressbar" aria-label={g.label} aria-valuemin={0} aria-valuemax={100}
            aria-valuenow={g.progress_pct ?? 0} className="relative h-2 rounded mt-2 bg-panel2 overflow-hidden"
            style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
            <span className="absolute inset-y-0 left-0 rounded"
              style={{ width: `${g.progress_pct ?? 0}%`, background: g.reached ? 'var(--good)' : 'var(--acc)' }} />
          </div>
          <div className="flex items-center justify-between text-xs text-ink3 mt-1.5 gap-3">
            <span className="num">{money(g.current ?? 0, false)} / {money(g.target, false)}</span>
            <span>{g.reached ? 'Reached' : `${num(g.progress_pct ?? 0, 0)}%`}</span>
          </div>
        </>
      ) : (
        <div className="text-xs text-ink3 mt-2"><span className="num">—</span> · {unknownText(g)}</div>
      )}
    </li>
  )
}

function GoalsTable({ goals }: { goals: GoalRow[] }) {
  return (
    <div className="table-scroll mt-3.5">
      <table className="tbl" style={{ minWidth: 760, '--row': '40px' } as CSSProperties}>
        <thead>
          <tr>
            <th>Goal</th><th>Scope</th><th className="r">Progress</th><th className="r">Now</th><th className="r">Target</th>
            <th>By</th><th className="r">Months left</th><th className="r">A month</th>
          </tr>
        </thead>
        <tbody>
          {goals.map((g) => (
            <tr key={g.id}>
              <td className="font-medium">{g.label}</td>
              <td className="text-ink2">{g.scope_text}</td>
              <td className="r">
                {g.progress_pct == null ? <span className="text-xs text-ink3">— · {unknownText(g)}</span>
                  : <span className="num">{g.reached ? 'Reached' : `${num(g.progress_pct, 0)}%`}</span>}
              </td>
              <td className="r num">{g.current == null ? <Missing /> : money(g.current, false)}</td>
              <td className="r num">{money(g.target, false)}</td>
              <td className="text-ink2 whitespace-nowrap">{g.by ? (g.overdue ? `was due ${longDate(g.by)}` : longDate(g.by)) : <Missing />}</td>
              <td className="r num">{g.months_left == null ? <Missing /> : g.months_left}</td>
              <td className="r num">{g.monthly_needed == null ? <Missing /> : money(g.monthly_needed, false)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function MilestonesPanel({ goals, today }: { goals: GoalRow[]; today: string }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const next = nextDated(goals, NEXT)
  const ongoing = goals.filter((g) => g.by == null)
  return (
    <Panel id="milestones" title="Milestones" span={12}
      subtitle={goals.length > 0 ? 'Your goals in time: the next ones in full, the rest on the line' : undefined}
      actions={goals.length > 0 && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {goals.length === 0 ? (
        <Empty>No goals yet. An investing feed sends what you&rsquo;re saving toward.</Empty>
      ) : view === 'Table' ? (
        <GoalsTable goals={goals} />
      ) : (
        <>
          <div className="mt-3"><Timeline goals={goals} today={today} /></div>
          {next.length > 0 && (
            <div className="goal-cards mt-5">{next.map((g) => <GoalCard key={g.id} g={g} />)}</div>
          )}
          {ongoing.length > 0 && (
            <div className="mt-5">
              <div className="label mb-1">Ongoing</div>
              <ul>{ongoing.map((g) => <OngoingRow key={g.id} g={g} />)}</ul>
            </div>
          )}
        </>
      )}
    </Panel>
  )
}
