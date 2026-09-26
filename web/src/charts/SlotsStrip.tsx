// How much of a book's money is working: one column of slots per session, filled from the bottom.
import type { CSSProperties, PointerEvent } from 'react'
import type { Money } from '../lib/api'
import { monthLabel, shortDate } from '../lib/format'
import { bandLayout, clampTip, indexAt } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Hatch, Tip, useSvgId } from './marks'

const GAP = 2
const MAX_CELL = 16

export function SlotsStrip({ days, used, total, money, height = 108, ariaLabel }: {
  days: string[]; used: number[]; total: number; money: Money; height?: number; ariaLabel: string
}) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const { index: hover, set: setHover, onKey } = useIndex(days.length)
  const hatch = useSvgId('slots')
  if (days.length === 0 || total <= 0) return <Empty>No sessions yet.</Empty>

  const plotH = height - 20
  const cell = Math.min(MAX_CELL, (plotH - (total - 1) * GAP) / total)
  const layout = bandLayout(days.length, width, Infinity, 0.84)
  const rowY = (r: number) => plotH - (r + 1) * cell - r * GAP // row 0 is the bottom one
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(indexAt(event.clientX - box.left, days.length, width))
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {money === 'paper' && <Hatch id={hatch} color="var(--s2)" />}
        {hover != null && (
          <rect x={hover * layout.step} y={rowY(total - 1) - 3} width={layout.step} height={plotH - rowY(total - 1) + 3}
            fill="var(--ink1)" fillOpacity={0.06} rx={2} />
        )}
        {days.map((day, i) => Array.from({ length: total }, (_, r) => r < used[i]
          ? (
            <rect key={`${day}-${r}`} data-mark={money} x={layout.left(i)} y={rowY(r)} width={layout.mark} height={cell}
              rx={2} fill={money === 'real' ? 'var(--s2)' : `url(#${hatch})`}
              stroke={money === 'paper' ? 'var(--s2)' : undefined} strokeWidth={money === 'paper' ? 1 : undefined} />
          ) : (
            <rect key={`${day}-${r}`} data-mark="free" x={layout.left(i) + 0.5} y={rowY(r) + 0.5}
              width={Math.max(0, layout.mark - 1)} height={Math.max(0, cell - 1)} rx={2} fill="none"
              stroke="var(--line2)" />
          )))}
        <text x={0} y={height - 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
          {monthLabel(days[0], true)}
        </text>
        <text x={width} y={height - 4} textAnchor="end" fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
          {monthLabel(days[days.length - 1], true)}
        </text>
      </svg>
      {hover != null && (
        <Tip left={clampTip(layout.center(hover), width)} title={shortDate(days[hover])}
          rows={[['In use', `${used[hover]} of ${total}`]]} />
      )}
    </div>
  )
}

export function SlotsTable({ days, used, total }: { days: string[]; used: number[]; total: number }) {
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 180 }}>
      <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
        <thead><tr><th>Session</th><th className="r">In use</th></tr></thead>
        <tbody>
          {days.map((day, i) => (
            <tr key={day}><td>{shortDate(day)}</td><td className="r num">{used[i]} of {total}</td></tr>
          )).reverse()}
        </tbody>
      </table>
    </div>
  )
}
