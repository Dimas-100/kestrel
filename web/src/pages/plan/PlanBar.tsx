// The plan bar: the band shaded, the aim as a tick, the actual as a dot (an arrow when it sits outside the domain).
import { bandGeometry } from '../../charts/geometry'
import type { TargetRow } from '../../lib/api'
import { num } from '../../lib/format'

/** A "%" target always plots on the same 0–100 scale, so a band's width is comparable across rows (an out-of-range
 *  actual still clamps to the edge with an arrow, via bandGeometry). A ratio ("x") target has no natural bound, so
 *  it gets its own domain wide enough to show the band, the aim and the actual, with a little air on each side. */
function domainFor(row: TargetRow): [number, number] {
  if (row.unit === '%') return [0, 100]
  const known = [row.low, row.high, row.target, row.actual].filter((v): v is number => v != null)
  if (known.length === 0) return [0, 1]
  const lo = Math.min(...known)
  const hi = Math.max(...known)
  const pad = (hi - lo) * 0.2 || Math.max(Math.abs(hi), 1) * 0.2
  return [lo - pad, hi + pad]
}

const DOT_COLOR: Record<TargetRow['status'], string> = {
  on: 'var(--ink1)', over: 'var(--warn)', under: 'var(--warn)', unknown: 'var(--ink3)',
}

export function PlanBar({ row }: { row: TargetRow }) {
  const g = bandGeometry(row.low, row.high, row.target, row.actual, domainFor(row))
  const pct = (f: number) => `${(f * 100).toFixed(2)}%`
  const shape = row.unit === '%' ? `${num(row.actual ?? 0, 0)}%` : `${num(row.actual ?? 0, 1)}x`
  const label = row.actual == null ? `${row.label}: actual unknown` : `${row.label}: actual ${shape}`
  return (
    <div className="relative h-2 rounded-full bg-panel2 my-1" role="img" aria-label={label}
      style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
      <span className="absolute inset-y-0 rounded-full bg-line2"
        style={{ left: pct(g.bandStart), right: `${(100 - g.bandEnd * 100).toFixed(2)}%` }} />
      {g.target != null && (
        <span className="absolute rounded-full bg-ink2" style={{ left: pct(g.target), top: -2, bottom: -2, width: 2 }} />
      )}
      {g.actual != null && !g.clamped && (
        <span className="absolute w-2.5 h-2.5 rounded-full" style={{
          left: pct(g.actual), top: '50%', transform: 'translate(-50%, -50%)', background: DOT_COLOR[row.status],
          boxShadow: '0 0 0 2px var(--panel)',
        }} />
      )}
      {g.actual != null && g.clamped && (
        <span aria-hidden="true" className="absolute text-xs leading-none" style={{
          left: pct(g.actual), top: '50%', transform: `translate(${g.actual === 1 ? '-100%' : '0%'}, -50%)`,
          color: DOT_COLOR[row.status],
        }}>
          {g.actual === 1 ? '→' : '←'}
        </span>
      )}
    </div>
  )
}
