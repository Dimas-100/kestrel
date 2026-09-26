// One line chart for the whole app: hairline grid, right-hand value axis, crosshair tooltip on hover or keys, and
// an optional expected band (the funnel on the Strategy page).
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import { area, curveLinear, curveStepAfter, line } from 'd3-shape'
import type { PointerEvent } from 'react'
import { clampTip, nearestIndex, tickDecimals, tickIndices } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Tip } from './marks'

export interface ChartSeries {
  key: string
  label: string
  values: (number | null)[]
  color: string // a CSS colour token, e.g. 'var(--s2)'
  style: 'solid' | 'dashed' | 'dotted' // real · paper · expected/benchmark
  area?: boolean
  step?: boolean
  endLabel?: string // a direct label at the line's last point
}

/** An expected range drawn as a dotted-edge wash: lo[i] to hi[i], skipped where either is null. */
export interface Band {
  lo: (number | null)[]
  hi: (number | null)[]
  label: string
}

interface Props {
  dates: string[]
  series: ChartSeries[]
  height: number
  ariaLabel: string
  yFormat: (value: number, decimals: number) => string
  valueFormat: (value: number) => string
  xLabel: (iso: string) => string
  tipTitle: (iso: string) => string
  zeroLine?: boolean
  compact?: boolean
  band?: Band
}

const DASH = { solid: undefined, dashed: '5 3.5', dotted: '1.5 3.5' } as const

/** The index of a series' last value (a shorter book's line ends before the chart does); -1 when it has none. */
function lastDefined(values: (number | null)[]): number {
  for (let i = values.length - 1; i >= 0; i -= 1) if (values[i] != null) return i
  return -1
}

export function LineChart(props: Props) {
  const { dates, series, height, compact = false, band } = props
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(dates.length)
  const axisW = compact ? 0 : 56
  const bottom = compact ? 4 : 24
  const plotW = Math.max(40, width - axisW)
  const all = [...series.flatMap((s) => s.values), ...(band ? [...band.lo, ...band.hi] : [])]
    .filter((v): v is number => v != null)
  const y = scaleLinear()
    .domain([min(all) ?? 0, max(all) ?? 1])
    .nice(4)
    .range([height - bottom, 8])
  const x = scaleLinear().domain([0, Math.max(1, dates.length - 1)]).range([0, plotW])
  const xs = dates.map((_, i) => x(i))
  const yTicks = compact ? [] : y.ticks(4)
  const xTicks = compact ? [] : tickIndices(dates.length, width < 480 ? 4 : 6)

  const pathOf = (values: (number | null)[], step = false) =>
    line<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y((v) => y(v as number))
      .curve(step ? curveStepAfter : curveLinear)(values) ?? ''
  const areaOf = (s: ChartSeries) =>
    area<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y0(height - bottom)
      .y1((v) => y(v as number))(s.values) ?? ''
  const bandArea = band
    ? area<number>()
      .defined((i) => band.lo[i] != null && band.hi[i] != null)
      .x((i) => x(i))
      .y0((i) => y(band.lo[i] as number))
      .y1((i) => y(band.hi[i] as number))(band.lo.map((_, i) => i)) ?? ''
    : ''

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  const labelled = series.filter((s) => s.endLabel)

  const tipRows: [string, string][] = series.map((s) => [
    s.label, hover == null || s.values[hover] == null ? '—' : props.valueFormat(s.values[hover] as number),
  ])
  if (band && hover != null) {
    const lo = band.lo[hover]
    const hi = band.hi[hover]
    tipRows.push([band.label, lo == null || hi == null ? '—' : `${props.valueFormat(lo)} to ${props.valueFormat(hi)}`])
  }

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
              {props.yFormat(t, tickDecimals(yTicks))}
            </text>
          </g>
        ))}
        {xTicks.map((i) => (
          <text key={i} x={xs[i]} y={height - 6} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}
            textAnchor={i === 0 ? 'start' : i === dates.length - 1 ? 'end' : 'middle'}>
            {props.xLabel(dates[i])}
          </text>
        ))}
        {band && (
          <g>
            <path data-band="wash" d={bandArea} fill="var(--ink1)" fillOpacity={0.05} />
            {[band.lo, band.hi].map((edge, k) => (
              <path key={k} d={pathOf(edge)} fill="none" stroke="var(--ref)" strokeWidth={1} strokeDasharray="1.5 3"
                strokeLinecap="round" />
            ))}
          </g>
        )}
        {series.filter((s) => s.area).map((s) => (
          <path key={`${s.key}-area`} d={areaOf(s)} fill={s.color} fillOpacity={0.06} />
        ))}
        {series.map((s) => (
          <path key={s.key} d={pathOf(s.values, s.step)} fill="none" stroke={s.color}
            strokeWidth={s.style === 'dotted' ? 1.5 : 2} strokeDasharray={DASH[s.style]} strokeLinecap="round"
            strokeLinejoin="round" />
        ))}
        {hover == null && series.filter((s) => s.style === 'solid' || s.endLabel).map((s) => {
          const lastI = lastDefined(s.values)
          const v = s.values[lastI]
          return v == null ? null : (
            <circle key={`${s.key}-end`} cx={xs[lastI]} cy={y(v)} r={4} strokeWidth={2}
              fill={s.style === 'solid' ? s.color : 'var(--panel)'} stroke={s.style === 'solid' ? 'var(--panel)' : s.color} />
          )
        })}
        {labelled.map((s, k) => {
          const lastI = lastDefined(s.values)
          const v = s.values[lastI]
          if (v == null) return null
          const cx = xs[lastI]
          const anchor = cx > plotW - 60 ? 'end' : cx < 60 ? 'start' : 'middle'
          return (
            <text key={`${s.key}-label`} x={cx} y={y(v) + (k === 0 ? -10 : 18)} textAnchor={anchor}
              fill={k === 0 ? 'var(--ink1)' : 'var(--ink2)'} style={{ font: '500 11px var(--k-sans)' }}>
              {s.endLabel}
            </text>
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
      {hover != null && <Tip left={clampTip(xs[hover], width)} title={props.tipTitle(dates[hover])} rows={tipRows} />}
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
