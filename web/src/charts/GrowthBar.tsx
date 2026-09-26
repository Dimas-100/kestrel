// Where the money came from, as one bar: what you started with, what you put in since, and what the market added.
import { scaleLinear } from 'd3-scale'
import type { CSSProperties, PointerEvent } from 'react'
import { Delta } from '../components/bits'
import { money, signedMoney } from '../lib/format'
import { clampTip } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Tip } from './marks'

export interface GrowthSteps {
  start: number
  deposits: number // deposits minus withdrawals
  market: number
  end: number
}

export type GrowthPart = 'start' | 'deposits' | 'market'
export const PART_LABEL: Record<GrowthPart, string> = {
  start: 'Started at', deposits: 'You put in', market: 'The market added',
}

interface Segment { key: GrowthPart; from: number; to: number }

/** The parts end to end: the start from zero, then what you put in, then the market up to the end. A negative part
 *  runs back over the one before it (money taken out, or lost). */
export function segments(g: GrowthSteps): Segment[] {
  const put = g.start + g.deposits
  return [
    { key: 'start', from: 0, to: g.start }, { key: 'deposits', from: g.start, to: put },
    { key: 'market', from: put, to: g.end },
  ]
}

const amount = (key: GrowthPart, value: number) => (key === 'market' ? signedMoney(value) : money(value))

/** The part under a position: the last one drawn there, as a later part draws over an earlier one. */
function partAt(parts: Segment[], value: number): number | null {
  for (let i = parts.length - 1; i >= 0; i -= 1) {
    const { from, to } = parts[i]
    if (from !== to && value >= Math.min(from, to) && value <= Math.max(from, to)) return i
  }
  return null
}

export function GrowthBar({ growth, height = 40, ariaLabel }: { growth: GrowthSteps; height?: number; ariaLabel: string }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const parts = segments(growth)
  const { index: hover, set: setHover, onKey } = useIndex(parts.length)
  const ends = parts.flatMap((p) => [p.from, p.to])
  const lo = Math.min(0, ...ends)
  const hi = Math.max(0, ...ends)
  if (hi === lo) return <Empty>Nothing to show yet.</Empty>

  const x = scaleLinear().domain([lo, hi]).range([0, width])
  const top = 6
  const barH = height - 2 * top
  const box = (p: Segment) => ({ x: x(Math.min(p.from, p.to)), width: Math.abs(x(p.to) - x(p.from)) })
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    setHover(partAt(parts, x.invert(event.clientX - rect.left)))
  }
  const [start, deposits, market] = parts
  const shown = hover == null ? null : parts[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <rect data-mark="start" {...box(start)} y={top} height={barH} rx={3} fill="var(--s3)" />
        {/* what you put in is the reference money, drawn like the "Start + deposits" line: dotted, with a wash */}
        <rect data-mark="deposits" {...box(deposits)} y={top + 0.75} height={barH - 1.5} rx={3} fill="var(--ink1)"
          fillOpacity={0.05} stroke="var(--ref)" strokeWidth={1.5} strokeDasharray="1.5 2.5" />
        <rect data-mark={growth.market >= 0 ? 'gain' : 'loss'} {...box(market)} y={top} height={barH} rx={3}
          fill={growth.market >= 0 ? 'var(--up)' : 'var(--down)'} />
        <line x1={x(growth.end)} x2={x(growth.end)} y1={1} y2={height - 1} stroke="var(--ink1)" strokeWidth={2} />
        {shown && (
          <rect {...box(shown)} y={top - 3} height={barH + 6} rx={4} fill="none" stroke="var(--ink1)" strokeWidth={1.5} />
        )}
      </svg>
      {shown && hover != null && (
        <Tip left={clampTip(x((shown.from + shown.to) / 2), width)} top={height + 4} title={PART_LABEL[shown.key]}
          rows={[['Amount', amount(shown.key, shown.to - shown.from)]]} />
      )}
    </div>
  )
}

export function GrowthTable({ growth }: { growth: GrowthSteps }) {
  return (
    <table className="tbl" style={{ '--row': '36px' } as CSSProperties}>
      <thead><tr><th>Part</th><th className="r">Amount</th></tr></thead>
      <tbody>
        <tr><td>{PART_LABEL.start}</td><td className="r num">{money(growth.start)}</td></tr>
        <tr><td>{PART_LABEL.deposits}</td><td className="r num">{money(growth.deposits)}</td></tr>
        <tr>
          <td>{PART_LABEL.market}</td>
          <td className="r"><Delta value={growth.market}>{signedMoney(growth.market)}</Delta></td>
        </tr>
        <tr><td>Now</td><td className="r num">{money(growth.end)}</td></tr>
      </tbody>
    </table>
  )
}
