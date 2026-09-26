// Where each closed trade landed, in 1-point return buckets, over the backtest's spread of outcomes.
import { max } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import type { CSSProperties, PointerEvent } from 'react'
import type { Money } from '../lib/api'
import { MINUS } from '../lib/format'
import { bandLayout, clampTip, indexAt } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Hatch, Tip, useSvgId } from './marks'

export interface HistogramBucket {
  low: number
  count: number
  share: number
  expected: number | null
}

const whole = (v: number) => (v === 0 ? '0%' : `${v > 0 ? '+' : MINUS}${Math.abs(v)}%`)

/** "+2% to +3%"; the end buckets also hold everything beyond them: "under −9%", "+9% or more". */
export function bucketLabel(low: number): string {
  if (low <= -10) return `under ${whole(-9)}`
  if (low >= 9) return `${whole(9)} or more`
  return `${whole(low)} to ${whole(low + 1)}`
}

/** A share of trades: whole percents, with one decimal under 1%. */
export function shareText(value: number): string {
  return value > 0 && value < 1 ? `${value.toFixed(1)}%` : `${Math.round(value)}%`
}

const tradesText = (n: number) => `${n} trade${n === 1 ? '' : 's'}`
const moneyWord = (money: Money) => (money === 'real' ? 'Real' : 'Paper')

/** A bar with a 4 px rounded data end and a square baseline. */
function barPath(x: number, w: number, top: number, base: number): string {
  const r = Math.min(4, w / 2, base - top)
  return `M${x} ${base}V${top + r}Q${x} ${top} ${x + r} ${top}H${x + w - r}Q${x + w} ${top} ${x + w} ${top + r}V${base}Z`
}

export function Histogram({ buckets, money, height = 236, ariaLabel }: {
  buckets: HistogramBucket[]; money: Money; height?: number; ariaLabel: string
}) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(buckets.length)
  const hatch = useSvgId('hatch')
  if (!buckets.some((b) => b.count > 0 || (b.expected ?? 0) > 0)) return <Empty>No closed trades yet.</Empty>

  const axisW = 40
  const base = height - 20
  const plotW = Math.max(40, width - axisW)
  const layout = bandLayout(buckets.length, plotW)
  const inner = layout.mark * 0.5
  const peak = max(buckets.flatMap((b) => [b.share, b.expected ?? 0])) ?? 1
  const y = scaleLinear().domain([0, Math.max(1, peak)]).nice(4).range([base, 16])
  const every = width < 480 ? 5 : 2
  const edges = Array.from({ length: buckets.length + 1 }, (_, i) => i).filter((i) => i % every === 0)
  const zero = buckets.findIndex((b) => b.low === 0)
  const fill = money === 'real' ? 'var(--s2)' : `url(#${hatch})`

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(indexAt(event.clientX - box.left, buckets.length, plotW))
  }
  const b = hover == null ? null : buckets[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {money === 'paper' && <Hatch id={hatch} color="var(--s2)" />}
        {y.ticks(4).map((t) => (
          <g key={t}>
            <line x1={0} x2={plotW} y1={y(t)} y2={y(t)} stroke={t === 0 ? 'var(--line2)' : 'var(--line)'} />
            <text x={plotW + 8} y={y(t) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>{t}%</text>
          </g>
        ))}
        {edges.map((i) => (
          <text key={i} x={i * layout.step} y={height - 4} textAnchor="middle" fill="var(--ink3)"
            style={{ font: '11px var(--k-mono)' }}>
            {whole(buckets[0].low + i)}
          </text>
        ))}
        {hover != null && (
          <rect x={hover * layout.step} y={8} width={layout.step} height={base - 8} fill="var(--ink1)" fillOpacity={0.04} />
        )}
        {buckets.map((bucket, i) => bucket.expected == null ? null : (
          <rect key={`e${i}`} data-mark="expected" x={layout.left(i)} y={y(bucket.expected)} width={layout.mark}
            height={Math.max(0, base - y(bucket.expected))} rx={3} fill="var(--ink1)" fillOpacity={0.05}
            stroke="var(--ref)" strokeDasharray="1.5 2.5" />
        ))}
        {buckets.map((bucket, i) => bucket.count === 0 ? null : (
          <path key={`a${i}`} data-mark={money} d={barPath(layout.center(i) - inner / 2, inner, y(bucket.share), base)}
            fill={fill} stroke={money === 'paper' ? 'var(--s2)' : undefined}
            strokeWidth={money === 'paper' ? 1.25 : undefined} />
        ))}
        {zero >= 0 && (
          <g>
            <line x1={zero * layout.step} x2={zero * layout.step} y1={14} y2={base} stroke="var(--ink3)" />
            <text x={zero * layout.step + 6} y={12} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}>
              break-even
            </text>
          </g>
        )}
      </svg>
      {b != null && hover != null && (
        <Tip left={clampTip(layout.center(hover), width)} title={`Trades returning ${bucketLabel(b.low)}`} rows={[
          [moneyWord(money), `${tradesText(b.count)} · ${shareText(b.share)}`],
          ...(b.expected == null ? [] : [['Backtest', `${shareText(b.expected)} of trades`] as [string, string]]),
        ]} />
      )}
    </div>
  )
}

export function HistogramTable({ buckets, money }: { buckets: HistogramBucket[]; money: Money }) {
  const backtest = buckets.some((b) => b.expected != null)
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 260 }}>
      <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
        <thead>
          <tr>
            <th>Return</th><th className="r">{moneyWord(money)} trades</th><th className="r">Share</th>
            {backtest && <th className="r">Backtest</th>}
          </tr>
        </thead>
        <tbody>
          {buckets.map((b) => (
            <tr key={b.low}>
              <td>{bucketLabel(b.low)}</td>
              <td className="r num">{b.count}</td>
              <td className="r num">{shareText(b.share)}</td>
              {backtest && <td className="r num">{b.expected == null ? '—' : shareText(b.expected)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
