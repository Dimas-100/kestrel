// Month by month: the book's monthly returns over the long-term accounts', as a diverging grid with an
// "ahead?" row. Colour is never alone: every cell prints its value and the ahead row says yes or no.
import type { CSSProperties, PointerEvent } from 'react'
import { BookMark } from '../components/bits'
import { Icon } from '../components/Icon'
import type { Money } from '../lib/api'
import { monthLabel, pct } from '../lib/format'
import { cellWash, clampTip, yearSpans } from './geometry'
import { useIndex, useWidth } from './hooks'
import { Empty, Tip } from './marks'

export interface MonthCell {
  month: string // "2026-09"
  book: number | null
  long_term: number | null
  ahead: boolean | null
}

const LABEL_W = 76
const MIN_W = 400 // narrower than this, the grid scrolls sideways inside its panel

const monthName = (m: string) => `${monthLabel(`${m}-01`)} ${m.slice(0, 4)}`
const cellText = (v: number) => pct(v, 1).replace('%', '')
const aheadText = (a: boolean | null) => (a == null ? '—' : a ? 'yes' : 'no')

function wash(value: number | null): string {
  const strength = cellWash(value)
  if (value == null) return 'transparent'
  if (strength == null) return 'var(--panel2)'
  return `color-mix(in srgb, var(${value > 0 ? '--up' : '--down'}) ${strength}%, transparent)`
}

function Cell({ kind, value, i }: { kind: 'book' | 'long_term'; value: number | null; i: number }) {
  return (
    <div data-cell={kind} data-i={i} className="num flex items-center justify-center rounded"
      style={{ height: 36, fontSize: 10, background: wash(value), color: value == null ? 'var(--ink3)' : 'var(--ink1)' }}>
      {value == null ? '—' : cellText(value)}
    </div>
  )
}

export function MonthGrid({ months, bookLabel, money, ariaLabel }: {
  months: MonthCell[]; bookLabel: string; money: Money; ariaLabel: string
}) {
  const [wrapRef, width] = useWidth<HTMLDivElement>(480)
  const { index: hover, set: setHover, onKey } = useIndex(months.length)
  if (!months.some((m) => m.book != null || m.long_term != null)) return <Empty>No monthly history yet.</Empty>

  const grid: CSSProperties = {
    display: 'grid', gridTemplateColumns: `${LABEL_W}px repeat(${months.length}, minmax(0, 1fr))`, gap: 3,
    alignItems: 'center', minWidth: MIN_W,
  }
  const inner = Math.max(width, MIN_W)
  const col = (inner - LABEL_W) / months.length
  const onPointer = (event: PointerEvent<HTMLDivElement>) => {
    const cell = (event.target as HTMLElement).closest<HTMLElement>('[data-i]')
    setHover(cell ? Number(cell.dataset.i) : null)
  }
  const m = hover == null ? null : months[hover]

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <div className="table-scroll">
        <div role="group" aria-label={ariaLabel} tabIndex={0} style={grid} onKeyDown={onKey}
          onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onBlur={() => setHover(null)}>
          <div />
          {yearSpans(months.map((x) => x.month)).map((y) => (
            <div key={y.year} className="text-ink3" style={{ gridColumn: `span ${y.span}`, fontSize: 10,
              borderBottom: '1px solid var(--line)', paddingBottom: 3 }}>
              {y.year}
            </div>
          ))}
          <div />
          {months.map((x) => (
            <div key={x.month} className="text-ink3 text-center" style={{ fontSize: 10 }}>{monthLabel(`${x.month}-01`)}</div>
          ))}
          <div className="flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
            <BookMark kind={money} color="var(--s2)" size={9} />{bookLabel}
          </div>
          {months.map((x, i) => <Cell key={x.month} kind="book" value={x.book} i={i} />)}
          <div className="flex items-center gap-1.5 text-xs text-ink2 whitespace-nowrap">
            <BookMark kind="real" color="var(--s1)" size={9} />Long-term
          </div>
          {months.map((x, i) => <Cell key={x.month} kind="long_term" value={x.long_term} i={i} />)}
          <div className="text-xs text-ink3">Ahead?</div>
          {months.map((x, i) => (
            <div key={x.month} data-cell="ahead" data-i={i} className="flex justify-center"
              style={{ color: x.ahead ? 'var(--good)' : 'var(--ink3)' }}>
              {x.ahead === true && <Icon name="check" size={14} />}
              {x.ahead === false && <span aria-hidden="true" className="text-xs">−</span>}
              {x.ahead != null && <span className="sr-only">{aheadText(x.ahead)}</span>}
            </div>
          ))}
        </div>
      </div>
      {m != null && hover != null && (
        <Tip left={clampTip(LABEL_W + (hover + 0.5) * col, width)} top={-8} title={monthName(m.month)} rows={[
          [bookLabel, m.book == null ? '—' : pct(m.book, 1)],
          ['Long-term', m.long_term == null ? '—' : pct(m.long_term, 1)],
          ['Ahead?', aheadText(m.ahead)],
        ]} />
      )}
    </div>
  )
}

export function MonthTable({ months, bookLabel }: { months: MonthCell[]; bookLabel: string }) {
  return (
    <div className="table-scroll overflow-y-auto" style={{ maxHeight: 220 }}>
      <table className="tbl" style={{ '--row': '34px' } as CSSProperties}>
        <thead>
          <tr><th>Month</th><th className="r">{bookLabel}</th><th className="r">Long-term</th><th>Ahead?</th></tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={m.month}>
              <td>{monthName(m.month)}</td>
              <td className="r num">{m.book == null ? '—' : pct(m.book, 1)}</td>
              <td className="r num">{m.long_term == null ? '—' : pct(m.long_term, 1)}</td>
              <td>{aheadText(m.ahead)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
