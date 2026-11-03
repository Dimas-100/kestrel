// Money in and out of the cash accounts, moves between them left out: the last three months as a pair of bars each, in
// solid in the cash grey, out the same grey washed with a hairline; the figures above, and under each pair the month,
// "to date" or "from 10 Jul" when the window covers only part of it, and the month's net. A table lists every month
// with its days, net and what moved between your accounts (spec 2026-10-08 reserves estimates §3.4).
import { type CSSProperties, type PointerEvent, useState } from 'react'
import { clampTip, indexAt } from '../../charts/geometry'
import { useIndex, useWidth } from '../../charts/hooks'
import { Empty, Tip } from '../../charts/marks'
import { Panel, Seg } from '../../components/bits'
import type { MonthFlow } from '../../lib/api'
import { compactMoney, MINUS, money, monthLabel, signedMoney } from '../../lib/format'

const VIEWS = ['Chart', 'Table'] as const
const SHOWN = 3
const HEIGHT = 222
const TOP = 22 // room for the figures above the tallest bar
const BOTTOM = 54 // room for the month, its part, and its net

export const monthText = (month: string) => `${monthLabel(`${month}-01`)} ${month.slice(0, 4)}`

/** "to date" for the current month, "from 10 Jul" for a first month the window starts inside, null when whole. */
export function partText(f: MonthFlow): string | null {
  if (!f.partial) return null
  return f.start.slice(8) !== '01' ? `from ${monthLabel(f.start, true)}` : 'to date'
}

/** "$982" / "$4.5K": a figure above a bar, whole dollars under a thousand so a pair never collides */
const barFigure = (v: number) => (v < 1000 ? money(v, false) : compactMoney(v))

/** "+$133" / "−$87" / "+$1.2K" / "$0": the net in a chart label, whole dollars under a thousand, signed so it never
 *  rests on colour */
const signedCompact = (v: number) => {
  const abs = Math.abs(v)
  if (Math.round(abs) === 0) return money(0, false)
  return `${v > 0 ? '+' : MINUS}${abs < 1000 ? money(abs, false) : compactMoney(abs)}`
}

function Bars({ flows }: { flows: MonthFlow[] }) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(420)
  const { index: hover, set: setHover, onKey } = useIndex(flows.length)
  const top = Math.max(1, ...flows.flatMap((f) => [f.money_in, f.money_out]))
  const plotH = HEIGHT - TOP - BOTTOM
  const y = (v: number) => TOP + plotH - (v / top) * plotH
  const step = width / flows.length
  const barW = Math.min(24, step * 0.3)
  const gap = 14 // room for the two figures above the bars to sit apart
  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(indexAt(event.clientX - box.left, flows.length, width))
  }
  const h = hover == null ? null : flows[hover]
  const moved = flows.reduce((sum, f) => sum + f.moved, 0)
  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} role="img"
        aria-label={`Money in and out by month: ${flows.map((f) => `${monthText(f.month)}${partText(f) ? ` (${partText(f)})` : ''}, in ${money(f.money_in)}, out ${money(f.money_out)}, net ${signedMoney(f.net)}`).join('; ')}`}
        tabIndex={0} style={{ display: 'block', maxWidth: '100%', height: 'auto', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        <line x1={0} x2={width} y1={TOP + plotH} y2={TOP + plotH} stroke="var(--line2)" />
        {flows.map((f, i) => {
          const cx = (i + 0.5) * step
          const inX = cx - barW - gap / 2
          const outX = cx + gap / 2
          const part = partText(f)
          return (
            <g key={f.month}>
              {hover === i && <rect x={i * step} y={TOP - 4} width={step} height={plotH + BOTTOM} fill="var(--ink1)" fillOpacity={0.05} rx={3} />}
              <rect x={inX} y={y(f.money_in)} width={barW} height={TOP + plotH - y(f.money_in)} rx={3} fill="var(--s3)" />
              <rect x={outX} y={y(f.money_out)} width={barW} height={TOP + plotH - y(f.money_out)} rx={3} fill="var(--s3)"
                fillOpacity={0.4} stroke="var(--s3)" strokeWidth={1} />
              <text x={inX + barW / 2} y={y(f.money_in) - 5} fontSize={10} textAnchor="middle" fill="var(--ink2)"
                style={{ fontFamily: 'var(--k-mono)' }}>{barFigure(f.money_in)}</text>
              <text x={outX + barW / 2} y={y(f.money_out) - 5} fontSize={10} textAnchor="middle" fill="var(--ink3)"
                style={{ fontFamily: 'var(--k-mono)' }}>{barFigure(f.money_out)}</text>
              <text x={cx} y={TOP + plotH + 16} fontSize={11} textAnchor="middle" fill="var(--ink2)" fontWeight={500}>
                {monthLabel(`${f.month}-01`)}
              </text>
              {part && <text x={cx} y={TOP + plotH + 30} fontSize={10} textAnchor="middle" fill="var(--ink3)">{part}</text>}
              <text x={cx} y={TOP + plotH + 46} fontSize={10} textAnchor="middle" fill="var(--ink2)"
                style={{ fontFamily: 'var(--k-mono)' }}>net {signedCompact(f.net)}</text>
            </g>
          )
        })}
      </svg>
      {h != null && hover != null && (
        <Tip left={clampTip((hover + 0.5) * step, width)} top={0}
          title={`${monthText(h.month)}${partText(h) ? `, ${partText(h)}` : ''} · ${h.days} days`} rows={[
            ['In', money(h.money_in)], ['Out', money(h.money_out)], ['Net', signedMoney(h.net)],
            ['Moved, left out', money(h.moved)],
          ]} />
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink3 mt-1">
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-2.5 rounded-sm" style={{ background: 'var(--s3)' }} />in</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-2.5 rounded-sm" style={{ background: 'color-mix(in srgb, var(--s3) 40%, transparent)', boxShadow: 'inset 0 0 0 1px var(--s3)' }} />out</span>
        {moved > 0 && <span className="prose">left out: <span className="num">{money(moved)}</span> moved between your accounts</span>}
      </div>
    </div>
  )
}

function FlowsTable({ flows }: { flows: MonthFlow[] }) {
  return (
    <div className="table-scroll mt-3.5">
      <table className="tbl" style={{ '--row': '38px' } as CSSProperties}>
        <thead>
          <tr><th>Month</th><th className="r">Days</th><th className="r">In</th><th className="r">Out</th><th className="r">Net</th>
            <th className="r">Moved</th></tr>
        </thead>
        <tbody>
          {flows.map((f) => (
            <tr key={f.month}>
              <td className="whitespace-nowrap">
                {monthText(f.month)}
                {partText(f) && <div className="text-xs text-ink3">{partText(f)}</div>}
              </td>
              <td className="r num">{f.days}</td>
              <td className="r num">{money(f.money_in)}</td>
              <td className="r num">{money(f.money_out)}</td>
              <td className="r num">{signedMoney(f.net)}</td>
              <td className="r num text-ink3">{money(f.moved)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function FlowsPanel({ flows }: { flows: MonthFlow[] }) {
  const [view, setView] = useState<(typeof VIEWS)[number]>('Chart')
  const shown = flows.slice(-SHOWN)
  return (
    <Panel id="flows" title="Money in and out" span={5}
      subtitle={flows.length > 0 ? 'Your bank accounts by month, moves between them left out' : undefined}
      actions={flows.length > 0 && <Seg label="View" options={VIEWS} value={view} onChange={setView} />}>
      {flows.length === 0 ? <Empty>No bank transactions yet.</Empty>
        : view === 'Table' ? <FlowsTable flows={flows} />
          : <div className="mt-4"><Bars flows={shown} /></div>}
    </Panel>
  )
}
