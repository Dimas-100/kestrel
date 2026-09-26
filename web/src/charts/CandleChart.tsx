// One trade, bar by bar: daily candles with the buy, the sell, the holding window and the stop, and an optional
// indicator panel underneath on the same time axis (a small multiple, never a second y axis).
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import { line } from 'd3-shape'
import type { CSSProperties, PointerEvent } from 'react'
import { monthLabel, num, pct, shortDate } from '../lib/format'
import { bandLayout, candleShapes, clampTip, indexAt, tickIndices } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Tip } from './marks'

export interface CandleBar { date: string; open: number; high: number; low: number; close: number }
export interface CandleIndicator { label: string; values: (number | null)[]; lines: { value: number; label: string }[] }

interface Props {
  bars: CandleBar[]
  indicator: CandleIndicator | null
  stop: number | null
  entry: number // index of the entry bar
  exit: number // index of the exit bar
  entryPrice: number
  exitPrice: number
  height?: number // the price panel
  ariaLabel: string
}

const AXIS_W = 52
const STOP_LABEL_W = 120 // "Stop 1,234.56 · −12%" at 11px
const HALO = { stroke: 'var(--panel)', strokeWidth: 3, paintOrder: 'stroke' } as const // text readable over candles
const IND_H = 76
const IND_GAP = 14
const price = (v: number) => num(v, v < 10 ? 2 : 0)

export function CandleChart(props: Props) {
  const { bars, indicator, stop, entry, exit, height = 210 } = props
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(bars.length)
  if (bars.length === 0) return <Empty>No chart for this trade.</Empty>

  const plotW = Math.max(40, width - AXIS_W)
  const layout = bandLayout(bars.length, plotW, 12, 0.6)
  const low = Math.min(min(bars, (b) => b.low) ?? 0, stop ?? Infinity)
  const high = Math.max(max(bars, (b) => b.high) ?? 1, stop ?? -Infinity)
  const pad = (high - low) * 0.16 || 1 // room for the markers and their labels
  const y = scaleLinear().domain([low - pad, high + pad]).nice(4).range([height - 4, 6])
  const candles = candleShapes(bars, plotW, y)
  const panelTop = height + IND_GAP
  const total = height + (indicator ? IND_GAP + IND_H : 0) + 20
  const x0 = entry * layout.step
  const x1 = (exit + 1) * layout.step
  const at = (i: number) => layout.center(i)
  const anchor = (x: number) => (x < 44 ? 'start' : x > plotW - 44 ? 'end' : 'middle')

  const readings = indicator ? [...indicator.values, ...indicator.lines.map((l) => l.value)] : []
  const iy = scaleLinear()
    .domain([min(readings, (v) => v ?? undefined) ?? 0, max(readings, (v) => v ?? undefined) ?? 100])
    .nice(2)
    .range([panelTop + IND_H - 4, panelTop + 4])
  const indicatorPath = indicator
    ? line<number | null>().defined((v) => v != null).x((_, i) => at(i)).y((v) => iy(v as number))(
      indicator.values) ?? ''
    : ''

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(indexAt(event.clientX - box.left, bars.length, plotW))
  }
  const stopBelow = stop != null ? pct((stop / props.entryPrice - 1) * 100, 0) : ''
  // the buy label sits under its bar and the sell label over its bar; when the two bars are close and the price
  // fell (a stop), the sell label moves up so the two never print over each other
  const buyY = y(bars[entry].low) + 30
  const sellY = Math.min(y(bars[exit].high) - 20, Math.abs(at(exit) - at(entry)) < 96 ? buyY - 18 : Infinity)
  // the stop label goes left of the holding window when there's room, else right of it, else inside it under the
  // line: never into the price axis
  const stopSide = x0 > 150 ? 'left' : plotW - x1 >= STOP_LABEL_W + 8 ? 'right' : 'inside'
  const bar = hover == null ? null : bars[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={total} role="img" aria-label={props.ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {y.ticks(4).map((t) => (
          <g key={t}>
            <line x1={0} x2={plotW} y1={y(t)} y2={y(t)} stroke="var(--line)" />
            <text x={plotW + 10} y={y(t) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>{price(t)}</text>
          </g>
        ))}
        <rect data-window="price" x={x0} y={4} width={x1 - x0} height={height - 8} fill="var(--ink1)" fillOpacity={0.045} />
        {stop != null && (
          <g>
            <line x1={x0} x2={x1} y1={y(stop)} y2={y(stop)} stroke="var(--serious)" strokeWidth={1.5} />
            <text x={stopSide === 'left' ? x0 - 8 : stopSide === 'right' ? x1 + 8 : x1 - 6}
              y={y(stop) + (stopSide === 'inside' ? 16 : 4)} textAnchor={stopSide === 'right' ? 'start' : 'end'}
              fill="var(--ink2)" {...HALO} style={{ font: '500 11px var(--k-sans)' }}>
              Stop {num(stop)} · {stopBelow}
            </text>
          </g>
        )}
        {candles.map((c, i) => (
          <g key={bars[i].date} data-candle="">
            <line x1={c.x} x2={c.x} y1={c.wickTop} y2={c.wickBottom} stroke={c.up ? 'var(--ink2)' : 'var(--ink3)'} />
            <rect x={c.x - c.w / 2} y={c.bodyTop} width={c.w} height={c.bodyH} rx={1}
              fill={c.up ? 'var(--panel)' : 'var(--ink3)'} stroke={c.up ? 'var(--ink2)' : 'none'}
              strokeWidth={c.up ? 1.25 : 0} />
          </g>
        ))}
        <g>
          <path d={`M${at(entry)} ${y(bars[entry].low) + 6}l6 9h-12z`} fill="var(--acc)" />
          <text x={at(entry)} y={buyY} textAnchor={anchor(at(entry))} fill="var(--ink1)" {...HALO}
            style={{ font: '500 11px var(--k-mono)' }}>
            Buy {num(props.entryPrice)}
          </text>
          <path d={`M${at(exit)} ${y(bars[exit].high) - 6}l6 -9h-12z`} fill="var(--acc)" />
          <text x={at(exit)} y={sellY} textAnchor={anchor(at(exit))} fill="var(--ink1)" {...HALO}
            style={{ font: '500 11px var(--k-mono)' }}>
            Sell {num(props.exitPrice)}
          </text>
        </g>
        {indicator && (
          <g>
            <line x1={0} x2={width} y1={panelTop - IND_GAP / 2} y2={panelTop - IND_GAP / 2} stroke="var(--line)" />
            <rect data-window="indicator" x={x0} y={panelTop} width={x1 - x0} height={IND_H} fill="var(--ink1)"
              fillOpacity={0.045} />
            {indicator.lines.map((l) => (
              <g key={l.label}>
                <line x1={0} x2={plotW} y1={iy(l.value)} y2={iy(l.value)} stroke="var(--ref)"
                  strokeDasharray="1.5 3" strokeLinecap="round" />
                <text x={plotW + 10} y={iy(l.value) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
                  {l.value}
                </text>
              </g>
            ))}
            <path d={indicatorPath} fill="none" stroke="var(--ink1)" strokeWidth={1.5} strokeLinejoin="round" />
            <text x={plotW + 10} y={panelTop + IND_H / 2 + 4} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}>
              {indicator.label}
            </text>
          </g>
        )}
        {tickIndices(bars.length, width < 480 ? 3 : 5).map((i) => (
          <text key={i} x={at(i)} y={total - 4} textAnchor={anchor(at(i))} fill="var(--ink3)"
            style={{ font: '11px var(--k-mono)' }}>
            {monthLabel(bars[i].date, true)}
          </text>
        ))}
        {hover != null && (
          <line x1={at(hover)} x2={at(hover)} y1={4} y2={total - 20} stroke="var(--line2)" />
        )}
      </svg>
      {bar != null && hover != null && (
        <Tip left={clampTip(at(hover), width)} title={shortDate(bar.date)} rows={[
          ['Open', num(bar.open)], ['High', num(bar.high)], ['Low', num(bar.low)], ['Close', num(bar.close)],
          ...(indicator ? [[indicator.label, indicator.values[hover] == null ? '—'
            : num(indicator.values[hover] as number, 1)] as [string, string]] : []),
        ]} />
      )}
    </div>
  )
}

export function CandleTable({ bars, indicator, entry, exit }: {
  bars: CandleBar[]; indicator: CandleIndicator | null; entry: number; exit: number
}) {
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 300 }}>
      <table className="tbl" style={{ '--row': '34px', minWidth: 460 } as CSSProperties}>
        <thead>
          <tr>
            <th>Date</th><th className="r">Open</th><th className="r">High</th><th className="r">Low</th>
            <th className="r">Close</th>{indicator && <th className="r">{indicator.label}</th>}<th>Trade</th>
          </tr>
        </thead>
        <tbody>
          {bars.map((b, i) => (
            <tr key={b.date}>
              <td>{shortDate(b.date)}</td>
              <td className="r num">{num(b.open)}</td><td className="r num">{num(b.high)}</td>
              <td className="r num">{num(b.low)}</td><td className="r num">{num(b.close)}</td>
              {indicator && (
                <td className="r num">{indicator.values[i] == null ? '—' : num(indicator.values[i] as number, 1)}</td>
              )}
              <td>{[i === entry && 'Buy', i === exit && 'Sell'].filter(Boolean).join(' · ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
