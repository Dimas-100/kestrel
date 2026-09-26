// Is it worth it? Yearly return (up) against the worst drop along the way (right is worse), one labelled point per
// line of money, with a dotted "return = worst drop" guide.
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import type { CSSProperties, PointerEvent } from 'react'
import { MINUS, pct } from '../lib/format'
import { clampTip, placeLabels } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Hatch, Tip, useSvgId } from './marks'

export interface ScatterPoint {
  key: string
  label: string
  sub: string // the figure and period printed under the label
  period: string
  x: number // worst drop, a positive magnitude
  y: number // yearly return
  color: string
  style: 'solid' | 'hatched' | 'dotted' // real · paper · backtest or benchmark
}

const LEFT = 44
const BOTTOM = 22
const drop = (v: number) => (v === 0 ? '0%' : `${MINUS}${v}%`)

export function Scatter({ points, height = 262, ariaLabel }: { points: ScatterPoint[]; height?: number; ariaLabel: string }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(points.length)
  const hatch = useSvgId('worth')
  if (points.length === 0) return <Empty>Not enough history yet. A yearly figure needs at least 90 days.</Empty>

  const right = width - 8
  // headroom on the right of the points, where their labels go
  const x = scaleLinear().domain([0, Math.max(5, (max(points, (p) => p.x) ?? 0) * 1.4)]).nice(3).range([LEFT, right])
  const y = scaleLinear()
    .domain([Math.min(0, min(points, (p) => p.y) ?? 0), Math.max(5, (max(points, (p) => p.y) ?? 0) * 1.15)])
    .nice(3)
    .range([height - BOTTOM, 10])
  const guide = Math.min(x.domain()[1], y.domain()[1])
  // labels stay inside the plot, clear of the y axis on the left
  const labels = placeLabels(points.map((p) => ({
    x: x(p.x) - LEFT, y: y(p.y), w: Math.max(p.label.length * 6.8, p.sub.length * 6.6),
  })), right - LEFT, height - BOTTOM).map((l) => ({ ...l, x: l.x + LEFT }))
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    const px = event.clientX - box.left
    const py = event.clientY - box.top
    const distances = points.map((p) => Math.hypot(x(p.x) - px, y(p.y) - py))
    setHover(distances.indexOf(Math.min(...distances))) // the closest point
  }
  const p = hover == null ? null : points[hover]
  const direct = labels.every((l) => l.clear) // labels that would collide go in a key under the chart instead

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <Hatch id={hatch} color="var(--s2)" />
        {y.ticks(3).map((t) => (
          <g key={`y${t}`}>
            <line x1={LEFT} x2={right} y1={y(t)} y2={y(t)} stroke={t === 0 ? 'var(--line2)' : 'var(--line)'} />
            <text x={LEFT - 8} y={y(t) + 4} textAnchor="end" fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
              {pct(t, 0)}
            </text>
          </g>
        ))}
        {x.ticks(3).map((t) => (
          <text key={`x${t}`} x={x(t)} y={height - 4} textAnchor="middle" fill="var(--ink3)"
            style={{ font: '11px var(--k-mono)' }}>
            {drop(t)}
          </text>
        ))}
        <line x1={x(0)} y1={y(0)} x2={x(guide)} y2={y(guide)} stroke="var(--ref)" strokeDasharray="1.5 3"
          strokeLinecap="round" />
        <text x={x(guide) - 4} y={y(guide) + 16} textAnchor="end" fill="var(--ink3)"
          style={{ font: '11px var(--k-sans)' }}>
          return = worst drop
        </text>
        <text x={LEFT + 8} y={22} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}>↖ better</text>
        {points.map((pt, i) => (
          <g key={pt.key}>
            {hover === i && <circle cx={x(pt.x)} cy={y(pt.y)} r={10} fill="none" stroke="var(--ink3)" />}
            {direct && labels[i].leader && (
              <line x1={x(pt.x)} y1={y(pt.y)} x2={labels[i].x + (labels[i].anchor === 'end' ? 3 : -3)}
                y2={labels[i].y + 14} stroke="var(--line2)" />
            )}
            <circle data-point={pt.style} cx={x(pt.x)} cy={y(pt.y)} r={6} strokeWidth={2}
              fill={pt.style === 'solid' ? pt.color : pt.style === 'hatched' ? `url(#${hatch})` : 'var(--panel)'}
              stroke={pt.style === 'solid' ? 'var(--panel)' : pt.color}
              strokeDasharray={pt.style === 'dotted' ? '2 2' : undefined} />
            {direct && (
              <>
                <text x={labels[i].x} y={labels[i].y + 11} textAnchor={labels[i].anchor} fill="var(--ink1)"
                  style={{ font: '500 12px var(--k-sans)' }}>
                  {pt.label}
                </text>
                <text x={labels[i].x} y={labels[i].y + 25} textAnchor={labels[i].anchor} fill="var(--ink3)"
                  style={{ font: '11px var(--k-mono)' }}>
                  {pt.sub}
                </text>
              </>
            )}
          </g>
        ))}
      </svg>
      {!direct && (
        <ul aria-label="Key" className="flex flex-wrap gap-x-4 gap-y-1.5 mt-2 text-xs">
          {points.map((pt) => (
            <li key={pt.key} className="inline-flex items-center gap-1.5">
              <svg width={12} height={12} aria-hidden="true" style={{ flex: 'none' }}>
                <circle cx={6} cy={6} r={4.5} strokeWidth={1.5}
                  fill={pt.style === 'solid' ? pt.color : pt.style === 'hatched' ? `url(#${hatch})` : 'var(--panel)'}
                  stroke={pt.color} strokeDasharray={pt.style === 'dotted' ? '1.5 1.5' : undefined} />
              </svg>
              <span className="font-medium">{pt.label}</span>
              <span className="num text-ink3">{pt.sub}</span>
            </li>
          ))}
        </ul>
      )}
      {p != null && (
        <Tip left={clampTip(x(p.x), width)} title={`${p.label} · ${p.period}`}
          rows={[['Yearly return', pct(p.y, 1)], ['Worst drop', pct(-p.x, 1)]]} />
      )}
    </div>
  )
}

export function ScatterTable({ points }: { points: ScatterPoint[] }) {
  return (
    <div className="table-scroll">
      <table className="tbl" style={{ '--row': '40px' } as CSSProperties}>
        <thead>
          <tr><th>Line</th><th className="r">Yearly return</th><th className="r">Worst drop</th><th>Over</th></tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.key}>
              <td>{p.label}</td><td className="r num">{pct(p.y, 1)}</td><td className="r num">{pct(-p.x, 1)}</td>
              <td>{p.period}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
