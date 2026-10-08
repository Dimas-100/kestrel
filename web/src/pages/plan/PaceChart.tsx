// A goal's progress against the pace it needs (spec 2026-10-08 plan §4.2): time from the window's first day to the
// goal's date on a linear axis, the actual since then as a solid accent line (real money), the straight line from
// where it started to the target dotted (the expected convention), today's point ringed. ← → or hover walk the
// actual's points; the sentence under it says ahead or behind in words, and the Milestones table carries the figure.
import { type PointerEvent } from 'react'
import { clampTip, nearestIndex } from '../../charts/geometry'
import { useIndex, useWidth } from '../../charts/hooks'
import { Tip } from '../../charts/marks'
import type { GoalPace } from '../../lib/api'
import { longDate, money } from '../../lib/format'

const H = 64
const PAD_X = 4
const PAD_Y = 6
const DAY_MS = 86_400_000

const at = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00Z`).getTime()

/** Where the straight line stands on a day: from the start value on the window's first day to the target on `by`. */
export function requiredOn(pace: GoalPace, target: number, by: string, iso: string): number {
  const span = (at(by) - at(pace.start)) / DAY_MS || 1
  const done = (at(iso) - at(pace.start)) / DAY_MS
  return pace.start_value + (target - pace.start_value) * (done / span)
}

/** "Ahead of the straight line by $250.00", "Behind the straight line by $1,300.00", or "On the line". */
export function paceText(pace: GoalPace): string {
  if (Math.abs(pace.ahead) < 0.5) return 'On the straight line'
  return `${pace.ahead > 0 ? 'Ahead of' : 'Behind'} the straight line by ${money(Math.abs(pace.ahead))}`
}

export function PaceChart({ pace, target, by, label }: { pace: GoalPace; target: number; by: string; label: string }) {
  const [ref, width] = useWidth<HTMLDivElement>(260)
  const pts = pace.points
  const { index: hover, set: setHover, onKey } = useIndex(pts.length)
  const t0 = at(pace.start)
  const t1 = at(by)
  const values = [pace.start_value, target, ...pts.map((p) => p.value)]
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const pad = (hi - lo) * 0.06 || 1
  const x = (iso: string) => PAD_X + ((at(iso) - t0) / (t1 - t0 || 1)) * (width - 2 * PAD_X)
  const y = (v: number) => PAD_Y + (1 - (v - (lo - pad)) / (hi - lo + 2 * pad)) * (H - 2 * PAD_Y)
  const xs = pts.map((p) => x(p.date))
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${xs[i].toFixed(1)},${y(p.value).toFixed(1)}`).join(' ')
  const area = pts.length > 1 ? `${line} L${xs[xs.length - 1].toFixed(1)},${H - PAD_Y} L${xs[0].toFixed(1)},${H - PAD_Y} Z` : ''
  const last = pts[pts.length - 1]
  const h = hover == null ? null : pts[hover]
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  return (
    <div ref={ref} className="mt-3" style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={H} viewBox={`0 0 ${width} ${H}`} role="img" tabIndex={0}
        aria-label={`${label}: ${paceText(pace)}, since ${longDate(pace.start)}`}
        style={{ display: 'block', maxWidth: '100%', height: 'auto', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <line x1={PAD_X} x2={width - PAD_X} y1={H - PAD_Y} y2={H - PAD_Y} stroke="var(--line)" />
        <line x1={x(pace.start)} y1={y(pace.start_value)} x2={x(by)} y2={y(target)} stroke="var(--ref)" strokeWidth={1.5}
          strokeDasharray="1.5 3.5" strokeLinecap="round" />
        {area && <path d={area} fill="var(--acc)" opacity={0.08} />}
        <path d={line} fill="none" stroke="var(--acc)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={x(by)} cy={y(target)} r={3.5} fill="var(--panel)" stroke="var(--ref)" strokeWidth={1.5} />
        {last && <circle cx={xs[xs.length - 1]} cy={y(last.value)} r={4} fill="var(--acc)" stroke="var(--panel)" strokeWidth={2} />}
        {h != null && hover != null && (
          <line x1={xs[hover]} x2={xs[hover]} y1={PAD_Y} y2={H - PAD_Y} stroke="var(--line2)" />
        )}
      </svg>
      <div className="flex justify-between text-[10px] text-ink3 mt-0.5">
        <span>{longDate(pace.start)}</span><span>{longDate(by)}</span>
      </div>
      {h != null && hover != null && (
        <Tip left={clampTip(xs[hover], width)} top={-8} title={longDate(h.date)} rows={[
          ['Actual', money(h.value, false)],
          ['Straight line', money(requiredOn(pace, target, by, h.date), false)],
        ]} />
      )}
    </div>
  )
}
