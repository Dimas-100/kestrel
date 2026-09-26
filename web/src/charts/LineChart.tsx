// One line chart for the whole app: hairline grid, right-hand value axis, crosshair tooltip on hover or keys.
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import { area, curveLinear, curveStepAfter, line } from 'd3-shape'
import { type KeyboardEvent, type PointerEvent, useLayoutEffect, useRef, useState } from 'react'
import { nearestIndex, tickIndices } from './geometry'

export interface ChartSeries {
  key: string
  label: string
  values: (number | null)[]
  color: string // a CSS colour token, e.g. 'var(--s2)'
  style: 'solid' | 'dashed' | 'dotted' // real · paper · expected/benchmark
  area?: boolean
  step?: boolean
}

interface Props {
  dates: string[]
  series: ChartSeries[]
  height: number
  ariaLabel: string
  yFormat: (value: number) => string
  valueFormat: (value: number) => string
  xLabel: (iso: string) => string
  tipTitle: (iso: string) => string
  zeroLine?: boolean
  compact?: boolean
}

const DASH = { solid: undefined, dashed: '5 3.5', dotted: '1.5 3.5' } as const

function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(fallback)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth || fallback)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [fallback])
  return [ref, width] as const
}

export function LineChart(props: Props) {
  const { dates, series, height, compact = false } = props
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const [hover, setHover] = useState<number | null>(null)
  const axisW = compact ? 0 : 56
  const bottom = compact ? 4 : 24
  const plotW = Math.max(40, width - axisW)
  const all = series.flatMap((s) => s.values).filter((v): v is number => v != null)
  const y = scaleLinear()
    .domain([min(all) ?? 0, max(all) ?? 1])
    .nice(4)
    .range([height - bottom, 8])
  const x = scaleLinear().domain([0, Math.max(1, dates.length - 1)]).range([0, plotW])
  const xs = dates.map((_, i) => x(i))
  const yTicks = compact ? [] : y.ticks(4)
  const xTicks = compact ? [] : tickIndices(dates.length, width < 480 ? 4 : 6)

  const pathOf = (s: ChartSeries) =>
    line<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y((v) => y(v as number))
      .curve(s.step ? curveStepAfter : curveLinear)(s.values) ?? ''
  const areaOf = (s: ChartSeries) =>
    area<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y0(height - bottom)
      .y1((v) => y(v as number))(s.values) ?? ''

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  const onKey = (event: KeyboardEvent<SVGSVGElement>) => {
    const last = dates.length - 1
    const moves: Record<string, number> = {
      ArrowLeft: Math.max(0, (hover ?? last) - 1),
      ArrowRight: Math.min(last, (hover ?? last - 1) + 1),
      Home: 0,
      End: last,
    }
    if (event.key in moves) {
      event.preventDefault()
      setHover(moves[event.key])
    } else if (event.key === 'Escape') setHover(null)
  }

  const tipLeft = hover == null ? 0 : xs[hover] + 12 + 190 > plotW ? xs[hover] - 202 : xs[hover] + 12

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={props.ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={0} x2={plotW} y1={y(t)} y2={y(t)}
              stroke={props.zeroLine && t === 0 ? 'var(--line2)' : 'var(--line)'} />
            <text x={plotW + 10} y={y(t) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
              {props.yFormat(t)}
            </text>
          </g>
        ))}
        {xTicks.map((i) => (
          <text key={i} x={xs[i]} y={height - 6} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}
            textAnchor={i === 0 ? 'start' : i === dates.length - 1 ? 'end' : 'middle'}>
            {props.xLabel(dates[i])}
          </text>
        ))}
        {series.filter((s) => s.area).map((s) => (
          <path key={`${s.key}-area`} d={areaOf(s)} fill={s.color} fillOpacity={0.06} />
        ))}
        {series.map((s) => (
          <path key={s.key} d={pathOf(s)} fill="none" stroke={s.color} strokeWidth={s.style === 'dotted' ? 1.5 : 2}
            strokeDasharray={DASH[s.style]} strokeLinecap="round" strokeLinejoin="round" />
        ))}
        {hover == null && series.filter((s) => s.style === 'solid').map((s) => {
          const lastI = s.values.length - 1
          const v = s.values[lastI]
          return v == null ? null : (
            <circle key={`${s.key}-end`} cx={xs[lastI]} cy={y(v)} r={4} fill={s.color} stroke="var(--panel)" strokeWidth={2} />
          )
        })}
        {hover != null && (
          <g>
            <line x1={xs[hover]} x2={xs[hover]} y1={8} y2={height - bottom} stroke="var(--line2)" />
            {series.map((s) => {
              const v = s.values[hover]
              return v == null ? null : (
                <circle key={`${s.key}-hover`} cx={xs[hover]} cy={y(v)} r={4} fill={s.color} stroke="var(--panel)"
                  strokeWidth={2} />
              )
            })}
          </g>
        )}
      </svg>
      {hover != null && (
        <div className="tip" style={{ left: tipLeft, top: 4 }} role="status">
          <div style={{ color: 'var(--ink3)', fontSize: 11 }}>{props.tipTitle(dates[hover])}</div>
          {series.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-4" style={{ marginTop: 4 }}>
              <span style={{ color: 'var(--ink2)' }}>{s.label}</span>
              <span className="num" style={{ fontWeight: 500 }}>
                {s.values[hover] == null ? '—' : props.valueFormat(s.values[hover] as number)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** The small legend key drawn beside a series name: the line in its real/paper/expected style. */
export function LineKey({ color, style }: { color: string; style: ChartSeries['style'] }) {
  return (
    <svg width="18" height="10" aria-hidden="true" style={{ flex: 'none' }}>
      <line x1="1" x2="17" y1="5" y2="5" stroke={color} strokeWidth={style === 'dotted' ? 1.5 : 2}
        strokeDasharray={style === 'dotted' ? '1.5 3' : style === 'dashed' ? '5 3' : undefined} strokeLinecap="round" />
    </svg>
  )
}
