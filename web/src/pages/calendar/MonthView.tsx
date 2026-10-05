// The month as a grid: a cell per day with its events as kind marks beside symbols, walkable from the keyboard,
// with Previous / Next / Today in the panel's corner. Another arrangement of the rows the lists show (spec
// 2026-10-05 §3–§4): nothing here is fetched, and the server computes nothing for it.
import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { CalendarView, EventKind, EventRow } from '../../lib/api'
import { shortDate } from '../../lib/format'
import { eventKey, KIND_LABEL } from './EventItem'

export interface DayCell {
  iso: string // "2026-10-05"
  inMonth: boolean // false for the neighbouring months' days that fill the first and last rows
}

const DAY_MS = 86_400_000
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const SHOWN = 3 // events printed in a cell before "+n"
const KIND_LETTER: Record<EventKind, string> = { earnings: 'E', filing: 'F', insider: 'I', dividend: 'D', other: 'O' }

const at = (iso: string) => new Date(`${iso}T00:00:00Z`)
const toIso = (d: Date) => d.toISOString().slice(0, 10)
const shift = (iso: string, days: number) => toIso(new Date(at(iso).getTime() + days * DAY_MS))
const weekday = (iso: string) => (at(iso).getUTCDay() + 6) % 7 // Monday 0 … Sunday 6
const dayNumber = (iso: string) => Number(iso.slice(8, 10))
const pad2 = (n: number) => String(n).padStart(2, '0')

/** "2026-10" for a date in October 2026 */
export const monthOf = (iso: string): string => iso.slice(0, 7)

/** The month `n` months after `ym` (negative steps back), across year ends. */
export function addMonths(ym: string, n: number): string {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(Date.UTC(y, m - 1 + n, 1))
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}`
}

const lastDay = (ym: string) => shift(`${addMonths(ym, 1)}-01`, -1)

/** The month's days from the Monday on or before the 1st to the Sunday on or after its last day. */
export function monthGrid(ym: string): DayCell[] {
  const first = `${ym}-01`
  const last = lastDay(ym)
  const start = shift(first, -weekday(first))
  const end = shift(last, 6 - weekday(last))
  const cells: DayCell[] = []
  for (let iso = start; iso <= end; iso = shift(iso, 1)) cells.push({ iso, inMonth: monthOf(iso) === ym })
  return cells
}

/** Every event the page has, ahead and behind. */
export const allEvents = (view: CalendarView): EventRow[] => [...view.upcoming.flatMap((w) => w.items), ...view.recent]

/** The months the grid can turn to: from the earlier of the first event's month and today's to the later of the
 *  last event's month and today's. */
export function monthRange(events: EventRow[], today: string): [string, string] {
  let lo = monthOf(today)
  let hi = lo
  for (const e of events) {
    const m = monthOf(e.date)
    if (m < lo) lo = m
    if (m > hi) hi = m
  }
  return [lo, hi]
}

/** Events by day, each day keeping the order given. */
export function byDay(events: EventRow[]): Map<string, EventRow[]> {
  const out = new Map<string, EventRow[]>()
  for (const e of events) {
    const list = out.get(e.date)
    if (list) list.push(e)
    else out.set(e.date, [e])
  }
  return out
}

const monthTitle = (ym: string) =>
  `${at(`${ym}-01`).toLocaleString('en-US', { month: 'long', timeZone: 'UTC' })} ${ym.slice(0, 4)}`
const countWords = (n: number) => (n === 0 ? '' : n === 1 ? ', 1 event' : `, ${n} events`)
/** The same day number a month away, or that month's last day when it is shorter. */
const sameDayIn = (ym: string, iso: string) => `${ym}-${pad2(Math.min(dayNumber(iso), dayNumber(lastDay(ym))))}`
const chunk = <T,>(items: T[], size: number): T[][] =>
  Array.from({ length: Math.ceil(items.length / size) }, (_, i) => items.slice(i * size, (i + 1) * size))

/** A kind letter in a small mark (filled when held) beside the symbol; the words for a screen reader. */
function Mark({ e }: { e: EventRow }) {
  return (
    <span className={e.held ? 'ev held' : 'ev'}>
      <span aria-hidden="true" className="ev-mark">{KIND_LETTER[e.kind]}</span>
      {e.symbol && <span className="ev-sym">{e.symbol}</span>}
      <span className="sr-only">{KIND_LABEL[e.kind]}{e.held ? ', held' : ''}{e.symbol ? ` ${e.symbol}` : ''}</span>
    </span>
  )
}

export function MonthView({ events, today, selected, onSelect }: {
  events: EventRow[]; today: string; selected: string; onSelect: (iso: string) => void
}) {
  const [lo, hi] = monthRange(events, today)
  const [month, setMonth] = useState(() => monthOf(selected))
  const shown = month < lo ? lo : month > hi ? hi : month // a filter can shrink the range under the month shown
  const [focused, setFocused] = useState(selected)
  const anchor = monthOf(focused) === shown ? focused : `${shown}-01` // the one day in the tab order
  const gridRef = useRef<HTMLTableElement>(null)
  const moved = useRef(false)
  useEffect(() => {
    // a day reached from the keys takes focus once it is on the page (the month may have just turned)
    if (!moved.current) return
    moved.current = false
    gridRef.current?.querySelector<HTMLButtonElement>(`[data-day="${focused}"]`)?.focus()
  })

  const days = byDay(events)
  const turn = (ym: string) => setMonth(ym)
  const move = (target: string) => {
    const ym = monthOf(target)
    if (ym < lo || ym > hi) return // the edge of the range: stay put
    if (ym !== shown) turn(ym)
    setFocused(target)
    moved.current = true
  }
  const choose = (iso: string) => {
    setFocused(iso)
    onSelect(iso)
  }
  const onKey = (event: KeyboardEvent<HTMLTableElement>) => {
    const steps: Record<string, () => string> = {
      ArrowLeft: () => shift(anchor, -1),
      ArrowRight: () => shift(anchor, 1),
      ArrowUp: () => shift(anchor, -7),
      ArrowDown: () => shift(anchor, 7),
      Home: () => shift(anchor, -weekday(anchor)),
      End: () => shift(anchor, 6 - weekday(anchor)),
      PageUp: () => sameDayIn(addMonths(shown, -1), anchor),
      PageDown: () => sameDayIn(addMonths(shown, 1), anchor),
    }
    if (event.key in steps) {
      event.preventDefault()
      move(steps[event.key]())
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      choose(anchor)
    }
  }
  const toToday = () => {
    turn(monthOf(today))
    setFocused(today)
    onSelect(today)
  }

  const nav = (
    <div className="flex items-center gap-2">
      <button type="button" className="icon-btn" aria-label="Previous month" disabled={shown <= lo}
        onClick={() => turn(addMonths(shown, -1))}>
        <Icon name="chevron" size={16} style={{ transform: 'rotate(180deg)' }} />
      </button>
      <button type="button" className="icon-btn" aria-label="Next month" disabled={shown >= hi}
        onClick={() => turn(addMonths(shown, 1))}>
        <Icon name="chevron" size={16} />
      </button>
      <button type="button" className="icon-btn cal-today" onClick={toToday}>Today</button>
    </div>
  )

  return (
    <Panel id="calendar-month" title={monthTitle(shown)} subtitle="Monday to Sunday. Pick a day to see its events."
      span={8} actions={nav}>
      <table ref={gridRef} role="grid" aria-label={monthTitle(shown)} className="cal" onKeyDown={onKey}>
        <thead>
          <tr>{WEEKDAYS.map((d) => <th key={d} scope="col">{d}</th>)}</tr>
        </thead>
        <tbody>
          {chunk(monthGrid(shown), 7).map((row) => (
            <tr key={row[0].iso}>
              {row.map((cell) => {
                if (!cell.inMonth) {
                  return <td key={cell.iso} className="cal-out"><span aria-hidden="true">{dayNumber(cell.iso)}</span></td>
                }
                const list = days.get(cell.iso) ?? []
                const more = Math.max(0, list.length - SHOWN)
                const isToday = cell.iso === today
                const isSelected = cell.iso === selected
                return (
                  <td key={cell.iso} role="gridcell" aria-selected={isSelected}>
                    <button type="button" data-day={cell.iso} tabIndex={cell.iso === anchor ? 0 : -1}
                      aria-label={`${shortDate(cell.iso)}${countWords(list.length)}`}
                      aria-current={isToday ? 'date' : undefined}
                      className={`cal-day${isSelected ? ' sel' : ''}${isToday ? ' today' : ''}`}
                      onClick={() => choose(cell.iso)}>
                      <span className="num cal-num">
                        {dayNumber(cell.iso)}
                        {isToday && <span className="sr-only"> today</span>}
                      </span>
                      {list.length > 0 && (
                        <span className="cal-evs">
                          {list.slice(0, SHOWN).map((e) => <Mark key={eventKey(e)} e={e} />)}
                          {more > 0 && <span className="cal-more">+{more}</span>}
                        </span>
                      )}
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  )
}
