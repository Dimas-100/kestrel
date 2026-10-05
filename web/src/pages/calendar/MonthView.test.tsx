import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { EventRow } from '../../lib/api'
import { calendarFixture } from '../../test/renderApp'
import { addMonths, allEvents, byDay, MonthView, monthGrid, monthOf, monthRange } from './MonthView'

const ev = (date: string, symbol: string, kind: EventRow['kind'] = 'earnings', held = true): EventRow =>
  ({ date, symbol, kind, title: 'Earnings', detail: '', url: '', held })

describe('month helpers', () => {
  it('a month grid runs from the Monday on or before the 1st to the Sunday on or after the last day', () => {
    const oct = monthGrid('2026-10') // 1 Oct 2026 is a Thursday, 31 Oct a Saturday: five rows
    expect(oct[0].iso).toBe('2026-09-28')
    expect(oct[oct.length - 1].iso).toBe('2026-11-01')
    expect(oct).toHaveLength(35)
    expect(oct.filter((c) => c.inMonth)).toHaveLength(31)
    const aug = monthGrid('2026-08') // 1 Aug 2026 is a Saturday: six rows
    expect(aug).toHaveLength(42)
    expect(aug[0].iso).toBe('2026-07-27')
    const feb = monthGrid('2027-02') // 1 Feb 2027 is a Monday and the 28th a Sunday: four rows exactly
    expect(feb).toHaveLength(28)
    expect(feb.every((c) => c.inMonth)).toBe(true)
  })

  it('names the month a date is in and steps months across a year end', () => {
    expect(monthOf('2026-10-05')).toBe('2026-10')
    expect(addMonths('2026-12', 1)).toBe('2027-01')
    expect(addMonths('2027-01', -1)).toBe('2026-12')
    expect(addMonths('2026-03', 0)).toBe('2026-03')
  })

  it('the range runs from the first event or today to the last event or today', () => {
    expect(monthRange(allEvents(calendarFixture), '2026-09-25')).toEqual(['2026-07', '2026-11'])
    expect(monthRange([], '2026-09-25')).toEqual(['2026-09', '2026-09'])
    expect(monthRange([ev('2026-03-01', 'AAA')], '2026-01-15')).toEqual(['2026-01', '2026-03'])
  })

  it('groups events by day, keeping each day in the order given', () => {
    const m = byDay([ev('2026-10-05', 'COST'), ev('2026-10-05', 'KO', 'dividend'), ev('2026-10-07', 'JPM')])
    expect([...m.keys()]).toEqual(['2026-10-05', '2026-10-07'])
    expect(m.get('2026-10-05')?.map((e) => e.symbol)).toEqual(['COST', 'KO'])
  })
})

const props = (over: Partial<Parameters<typeof MonthView>[0]> = {}) => ({
  events: allEvents(calendarFixture), today: '2026-09-25', selected: '2026-09-25', onSelect: vi.fn(), ...over,
})
const next = () => fireEvent.click(screen.getByRole('button', { name: 'Next month' }))

describe('MonthView', { timeout: 15_000 }, () => {
  it('is a grid of this month with seven weekday headers; days of other months are muted, not buttons', () => {
    render(<MonthView {...props()} />)
    const grid = screen.getByRole('grid', { name: 'September 2026' })
    expect(within(grid).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(
      ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    const today = within(grid).getByRole('button', { name: 'Fri 25 Sep' })
    expect(today.textContent).toContain('today')
    expect(today.closest('td')?.getAttribute('aria-selected')).toBe('true')
    expect(within(grid).queryByRole('button', { name: /31 Aug/ })).toBeNull()
    expect(grid.textContent).toContain('31') // ... but the day is still printed, muted
  })

  it('turns the month; the demo shows COST on 5 Oct with its kind and held said in words', () => {
    render(<MonthView {...props()} />)
    next()
    const grid = screen.getByRole('grid', { name: 'October 2026' })
    const day = within(grid).getByRole('button', { name: 'Mon 5 Oct, 1 event' })
    expect(day.textContent).toContain('COST')
    expect(day.textContent).toContain('Earnings, held')
    const dividend = within(grid).getByRole('button', { name: 'Tue 6 Oct, 1 event' })
    expect(dividend.textContent).toContain('Dividend')
  })

  it('shows three events on a day and folds the rest into +n', () => {
    const four = ['AAA', 'BBB', 'CCC', 'DDD'].map((s) => ev('2026-09-25', s))
    render(<MonthView {...props({ events: four })} />)
    const day = screen.getByRole('button', { name: 'Fri 25 Sep, 4 events' })
    expect(day.textContent).toContain('CCC')
    expect(day.textContent).not.toContain('DDD')
    expect(day.textContent).toContain('+1')
  })

  it('disables Previous on the first month of the range and Next on the last', () => {
    render(<MonthView {...props()} />)
    const prev = () => screen.getByRole('button', { name: 'Previous month' }) as HTMLButtonElement
    const nxt = () => screen.getByRole('button', { name: 'Next month' }) as HTMLButtonElement
    expect(prev().disabled).toBe(false)
    fireEvent.click(prev())
    fireEvent.click(prev()) // July 2026: the first event's month
    expect(screen.getByRole('grid', { name: 'July 2026' })).toBeTruthy()
    expect(prev().disabled).toBe(true)
    for (let i = 0; i < 4; i++) fireEvent.click(nxt()) // November: the last event's month
    expect(screen.getByRole('grid', { name: 'November 2026' })).toBeTruthy()
    expect(nxt().disabled).toBe(true)
  })

  it('moves with the arrow keys, turns the month past its edge, PageDown steps a month, Enter selects', () => {
    const onSelect = vi.fn()
    render(<MonthView {...props({ onSelect })} />)
    const start = screen.getByRole('button', { name: 'Fri 25 Sep' })
    expect(start.tabIndex).toBe(0)
    start.focus()
    fireEvent.keyDown(start, { key: 'ArrowRight' })
    const sat = screen.getByRole('button', { name: 'Sat 26 Sep' })
    expect(document.activeElement).toBe(sat)
    expect(sat.tabIndex).toBe(0)
    expect(start.tabIndex).toBe(-1)
    fireEvent.keyDown(sat, { key: 'ArrowDown' }) // 3 Oct: the page turns
    expect(screen.getByRole('grid', { name: 'October 2026' })).toBeTruthy()
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Sat 3 Oct')
    fireEvent.keyDown(document.activeElement as Element, { key: 'PageDown' })
    expect(screen.getByRole('grid', { name: 'November 2026' })).toBeTruthy()
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Tue 3 Nov')
    fireEvent.keyDown(document.activeElement as Element, { key: 'Home' })
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Mon 2 Nov')
    fireEvent.keyDown(document.activeElement as Element, { key: 'Enter' })
    expect(onSelect).toHaveBeenCalledWith('2026-11-02')
  })

  it('stays put at the edge of the range', () => {
    render(<MonthView {...props({ selected: '2026-11-30' })} />)
    next()
    next() // November, the last month
    const last = screen.getByRole('button', { name: 'Mon 30 Nov' })
    last.focus()
    fireEvent.keyDown(last, { key: 'ArrowRight' })
    expect(document.activeElement).toBe(last)
    fireEvent.keyDown(last, { key: 'PageDown' })
    expect(screen.getByRole('grid', { name: 'November 2026' })).toBeTruthy()
    expect(document.activeElement).toBe(last)
  })

  it('Today returns to this month and selects today', () => {
    const onSelect = vi.fn()
    render(<MonthView {...props({ onSelect })} />)
    next()
    fireEvent.click(screen.getByRole('button', { name: 'Today' }))
    expect(screen.getByRole('grid', { name: 'September 2026' })).toBeTruthy()
    expect(onSelect).toHaveBeenCalledWith('2026-09-25')
  })
})
