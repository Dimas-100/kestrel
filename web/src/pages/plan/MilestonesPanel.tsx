// The goals in time (spec 2026-10-05 plan page §2.1, amended by 2026-10-08 §4.2): a line from today to the furthest
// goal, goals due together drawn as one labelled cluster; the next three as cards grouped under their date, each with
// its ring, the goals it counts toward, its pace against the straight line when the history can be trusted, and a
// what-if that opens on demand; the later and the undated goals as compact rows; the newest of what was passed, the
// rest closed; and a table of every goal.
import { type CSSProperties, Fragment, type PointerEvent, useId, useState } from 'react'
import { clampTip, nearestIndex } from '../../charts/geometry'
import { useIndex, useWidth } from '../../charts/hooks'
import { Empty, Tip } from '../../charts/marks'
import { Missing, Panel, Seg } from '../../components/bits'
import type { GoalRow, Passed } from '../../lib/api'
import { longDate, money, num } from '../../lib/format'
import { PaceChart, paceText } from './PaceChart'
import { ProgressRing } from './ProgressRing'
import {
  clusterByX, clusterLabel, groupByDay, monthlyText, monthsBetween, nextDated, timelinePosition, yearTicks,
} from './timeline'
import { monthsToReach, reachDate } from './whatif'

const VIEWS = ['Chart', 'Table'] as const
const NEXT = 3
const PASSED_SHOWN = 3
const HORIZON_MONTHS = 50 * 12 // a goal further out than this (a placeholder date, say) sits at the line's end
const PAD = 8
const LINE_Y = 34
const HEIGHT = 60
const TICK_LABEL_PX = 36 // a four-digit year at 10 px, with air: ticks closer than this are thinned
const CLUSTER_PX = 14 // dots closer than this would overlap: they join one cluster

function whenText(g: GoalRow): string {
  if (g.reached) return g.reached_on ? `Reached ${longDate(g.reached_on)}` : 'Reached'
  if (g.overdue && g.by) return `was due ${longDate(g.by)}`
  if (g.by) return `by ${longDate(g.by)}${g.months_left != null ? ` · ${g.months_left} months` : ''}`
  return 'ongoing'
}

/** Why a goal's progress is unknown, worded for a person. */
function unknownText(g: GoalRow): string {
  return g.missing_accounts.length > 0 ? `account not in any source: ${g.missing_accounts.join(', ')}`
    : g.unknown_reason || 'not known yet'
}

type Dated = GoalRow & { by: string }

function Timeline({ goals, today }: { goals: GoalRow[]; today: string }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(900)
  const dated = goals.filter((g): g is Dated => g.by != null && g.current != null)
  const months = dated.map((g) => Math.min(HORIZON_MONTHS, monthsBetween(today, g.by)))
  const furthest = Math.max(0, ...months)
  const x = (pos: number) => PAD + pos * (width - 2 * PAD)
  const clusters = clusterByX(dated.map((g, i) => ({ item: g, x: x(g.overdue ? 0 : timelinePosition(months[i], furthest)) })),
    CLUSTER_PX)
  const { index: hover, set: setHover, onKey } = useIndex(clusters.length)
  if (clusters.length === 0 || furthest <= 0) return null
  const furthestIso = dated[months.indexOf(furthest)].by
  const ticks = yearTicks(today, furthestIso, TICK_LABEL_PX / Math.max(1, width - 2 * PAD))
  const xs = clusters.map((c) => c.x)
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  const dotColor = (g: GoalRow) => (g.reached ? 'var(--good)' : g.overdue ? 'var(--warn)' : 'var(--acc)')
  const anchorAt = (cx: number) => (cx < 90 ? 'start' : cx > width - 90 ? 'end' : 'middle')
  const h = hover == null ? null : clusters[hover]
  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      {/* drawn at the measured width; the viewBox lets it scale down, never overflow, should the panel narrow first */}
      <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} role="img" aria-label="Your goals in time"
        tabIndex={0} style={{ display: 'block', maxWidth: '100%', height: 'auto', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer}
        onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <line x1={PAD} x2={width - PAD} y1={LINE_Y} y2={LINE_Y} stroke="var(--line2)" />
        <line x1={PAD} x2={PAD} y1={LINE_Y - 6} y2={LINE_Y + 6} stroke="var(--ink2)" />
        <text x={PAD} y={HEIGHT - 4} fontSize={10} fill="var(--ink3)">today</text>
        {ticks.map((t) => (
          <g key={t.label}>
            <line x1={x(t.pos)} x2={x(t.pos)} y1={LINE_Y - 4} y2={LINE_Y + 4} stroke="var(--line2)" />
            <text x={x(t.pos)} y={HEIGHT - 4} fontSize={10} fill="var(--ink3)" textAnchor="middle">{t.label}</text>
          </g>
        ))}
        {clusters.map((c, i) => {
          const one = c.items.length === 1 ? c.items[0] : null
          if (one) {
            return (
              <g key={one.id}>
                {one.overdue && !one.reached && (
                  <text x={c.x} y={14} fontSize={10} fill="var(--warn)" textAnchor={anchorAt(c.x)}>overdue</text>
                )}
                <circle cx={c.x} cy={LINE_Y} r={hover === i ? 7 : 6} fill={dotColor(one)} stroke="var(--panel)" strokeWidth={2} />
              </g>
            )
          }
          return (
            <g key={c.items.map((g) => g.id).join('|')} data-cluster={c.items.length}>
              <text x={c.x} y={14} fontSize={10.5} fontWeight={500} fill="var(--ink2)" textAnchor={anchorAt(c.x)}>
                {clusterLabel(c.items)}
              </text>
              <line x1={c.x} x2={c.x} y1={18} y2={LINE_Y - 10} stroke="var(--line2)" />
              <circle cx={c.x} cy={LINE_Y} r={hover === i ? 11 : 10} fill="var(--acc)" stroke="var(--panel)" strokeWidth={2} />
              <text x={c.x} y={LINE_Y} fontSize={11} fontWeight={600} fill="var(--on-acc)" textAnchor="middle"
                dominantBaseline="central">{c.items.length}</text>
            </g>
          )
        })}
      </svg>
      {h != null && hover != null && (h.items.length === 1 ? (
        <Tip left={clampTip(xs[hover], width)} top={-4} title={h.items[0].label} rows={[
          ['Progress', h.items[0].progress_pct == null ? '—' : `${num(h.items[0].progress_pct, 0)}%`],
          ['Now', h.items[0].current == null ? '—' : money(h.items[0].current, false)],
          ['Target', money(h.items[0].target, false)],
          ['When', whenText(h.items[0])],
        ]} />
      ) : (
        <Tip left={clampTip(xs[hover], width)} top={-4} title={clusterLabel(h.items)}
          rows={h.items.map((g) => [g.label, g.progress_pct == null ? '—' : `${num(g.progress_pct, 0)}%`])} />
      ))}
    </div>
  )
}

/** "reaches $1,800 by 25 Nov 2026" at a monthly amount, or "never at this pace" at zero; a value goal keeps its caveat. */
function WhatIf({ g, today }: { g: GoalRow & { current: number; monthly_needed: number }; today: string }) {
  const [monthly, setMonthly] = useState(Math.round(g.monthly_needed))
  const max = Math.max(1, Math.round(g.monthly_needed * 3))
  const months = monthsToReach(g.current, g.target, monthly)
  return (
    <div className="mt-2">
      <div className="flex items-center gap-2 text-xs text-ink3">
        <input type="range" min={0} max={max} step={1} value={monthly} aria-label={`${g.label}: a month`}
          onChange={(e) => setMonthly(Number(e.target.value))} className="flex-1 min-w-0" style={{ accentColor: 'var(--acc)' }} />
        <span className="num whitespace-nowrap">{money(monthly, false)} a month</span>
      </div>
      <p className="text-xs text-ink3 mt-1">
        {months == null ? 'never at this pace'
          : <>reaches <span className="num">{money(g.target, false)}</span> by {longDate(reachDate(today, months))}
            {g.measure === 'value' && ', before any market growth'}</>}
      </p>
    </div>
  )
}

function TryIt({ g, today }: { g: GoalRow & { current: number; monthly_needed: number }; today: string }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <div className="mt-2">
      <button type="button" className="text-xs font-medium" style={{ color: 'var(--acc-ink)' }} aria-expanded={open}
        aria-controls={id} onClick={() => setOpen((o) => !o)}>
        {open ? 'Close the what-if' : 'Try a monthly amount'}
      </button>
      {open && <div id={id}><WhatIf g={g} today={today} /></div>}
    </div>
  )
}

function GoalCard({ g, today, labels }: { g: GoalRow; today: string; labels: Map<string, string> }) {
  const tryable = !g.reached && !g.overdue && g.current != null && g.monthly_needed != null
  const towards = g.part_of.map((id) => labels.get(id)).filter((l): l is string => l != null)
  return (
    <article id={`goal-${g.id}`} tabIndex={-1} aria-labelledby={`goal-${g.id}-label`} className="goal-card">
      <div className="flex gap-4">
        <ProgressRing pct={g.progress_pct ?? 0} label={g.label} reached={g.reached} />
        <div className="min-w-0 flex-1">
          <h3 id={`goal-${g.id}-label`} className="text-sm font-semibold leading-snug">{g.label}</h3>
          <div className="text-xs text-ink3 mt-0.5">{g.scope_text}</div>
          <div className="num text-[13px] mt-2">{money(g.current ?? 0, false)} / {money(g.target, false)}</div>
          <div className="text-xs text-ink3 mt-1">{whenText(g)}</div>
          {!g.reached && !g.overdue && monthlyText(g) && <p className="text-xs text-ink3 mt-1">{monthlyText(g)}</p>}
        </div>
      </div>
      {towards.length > 0 && (
        <p className="text-xs text-ink2 mt-2.5">Counts toward {towards.join(', ')} too.</p>
      )}
      {g.pace && g.by ? (
        <>
          <PaceChart pace={g.pace} target={g.target} by={g.by} label={g.label} />
          <p className="text-xs text-ink2 mt-1">{paceText(g.pace)}{g.measure === 'value' && ', before any market growth'}.</p>
        </>
      ) : g.pace_note ? <p className="text-xs text-ink3 mt-2.5">{g.pace_note}</p> : null}
      {tryable && <TryIt g={g as GoalRow & { current: number; monthly_needed: number }} today={today} />}
    </article>
  )
}

function PassedList({ passed }: { passed: Passed[] }) {
  if (passed.length === 0) return null
  const item = (m: Passed) => (
    <li key={`${m.kind}-${m.label}-${m.date}`} className="flex items-baseline justify-between gap-3 py-1.5 border-t border-line text-sm">
      <span className="font-medium">{m.label}</span>
      <span className="text-xs text-ink3 whitespace-nowrap">{m.kind === 'round' ? 'passed' : 'reached'} {longDate(m.date)}</span>
    </li>
  )
  const earlier = passed.slice(PASSED_SHOWN)
  return (
    <div className="mt-5">
      <div className="label mb-1">Passed</div>
      <ul aria-label="Passed">{passed.slice(0, PASSED_SHOWN).map(item)}</ul>
      {earlier.length > 0 && (
        <details className="also mt-1">
          <summary className="text-xs font-medium cursor-pointer text-ink2">{earlier.length} earlier</summary>
          <ul aria-label="Passed earlier">{earlier.map(item)}</ul>
        </details>
      )}
    </div>
  )
}

/** A goal as one compact row: a later dated goal, or an undated (ongoing) one. */
function CompactRow({ g }: { g: GoalRow }) {
  const known = g.current != null && g.progress_pct != null
  return (
    <li id={`goal-${g.id}`} tabIndex={-1} className="py-2.5 border-t border-line">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <span className="text-sm font-medium">{g.label}</span>
        <span className="text-xs text-ink3">{g.scope_text}{g.by && <> · {whenText(g)}</>}</span>
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

function paceCell(g: GoalRow) {
  if (!g.pace) return <Missing />
  const ahead = g.pace.ahead
  if (Math.abs(ahead) < 0.5) return <span>on the line</span>
  return <span>{ahead > 0 ? 'ahead' : 'behind'} <span className="num">{money(Math.abs(ahead), false)}</span></span>
}

function GoalsTable({ goals }: { goals: GoalRow[] }) {
  return (
    <div className="table-scroll mt-3.5">
      <table className="tbl" style={{ minWidth: 860, '--row': '40px' } as CSSProperties}>
        <thead>
          <tr>
            <th>Goal</th><th>Scope</th><th className="r">Progress</th><th className="r">Now</th><th className="r">Target</th>
            <th>By</th><th className="r">Months left</th><th className="r">A month</th><th>Pace</th>
          </tr>
        </thead>
        <tbody>
          {goals.map((g) => (
            <tr key={g.id}>
              <td className="font-medium">{g.label}</td>
              <td className="text-ink2">{g.scope_text}</td>
              <td className="r">
                {g.progress_pct == null ? <span className="text-xs text-ink3">— · {unknownText(g)}</span>
                  : <span className="num">{g.reached ? whenText(g) : `${num(g.progress_pct, 0)}%`}</span>}
              </td>
              <td className="r num">{g.current == null ? <Missing /> : money(g.current, false)}</td>
              <td className="r num">{money(g.target, false)}</td>
              <td className="text-ink2 whitespace-nowrap">{g.by ? (g.overdue ? `was due ${longDate(g.by)}` : longDate(g.by)) : <Missing />}</td>
              <td className="r num">{g.months_left == null ? <Missing /> : g.months_left}</td>
              <td className="r num">{g.monthly_needed == null ? <Missing /> : money(g.monthly_needed, false)}</td>
              <td className="text-ink2 whitespace-nowrap">{paceCell(g)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function MilestonesPanel({ goals, passed, today }: { goals: GoalRow[]; passed: Passed[]; today: string }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const next = nextDated(goals, NEXT)
  const shown = new Set(next.map((g) => g.id))
  const later = goals.filter((g) => g.by != null && !g.reached && !shown.has(g.id))
    .sort((a, b) => ((a.by as string) < (b.by as string) ? -1 : 1))
  const ongoing = goals.filter((g) => g.by == null)
  const labels = new Map(goals.map((g) => [g.id, g.label]))
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
            <div className="goal-cards mt-5">
              {groupByDay(next).map((group) => (
                <Fragment key={group.by ?? 'undated'}>
                  <div className="goal-group label">
                    Due {group.by ? longDate(group.by) : ''}{group.goals.length > 1 && ` · ${group.goals.length} goals`}
                  </div>
                  {group.goals.map((g) => <GoalCard key={g.id} g={g} today={today} labels={labels} />)}
                </Fragment>
              ))}
            </div>
          )}
          {later.length > 0 && (
            <div className="mt-5">
              <div className="label mb-1">Later</div>
              <ul>{later.map((g) => <CompactRow key={g.id} g={g} />)}</ul>
            </div>
          )}
          {ongoing.length > 0 && (
            <div className="mt-5">
              <div className="label mb-1">Ongoing</div>
              <ul>{ongoing.map((g) => <CompactRow key={g.id} g={g} />)}</ul>
            </div>
          )}
          <PassedList passed={passed} />
        </>
      )}
    </Panel>
  )
}
