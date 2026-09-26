import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MonthGrid, MonthTable } from './MonthGrid'

const months = [
  { month: '2025-11', book: null, long_term: null, ahead: null },
  { month: '2025-12', book: 1.2, long_term: -0.8, ahead: true },
  { month: '2026-01', book: 0.3, long_term: 2.9, ahead: false },
]

describe('MonthGrid', () => {
  it('washes each month by the size of its move and prints the value', () => {
    const { container } = render(<MonthGrid months={months} bookLabel="Real" money="real" ariaLabel="Months" />)
    const cells = [...container.querySelectorAll<HTMLElement>('[data-cell="book"]')]
    expect(cells.map((c) => c.textContent)).toEqual(['—', '+1.2', '+0.3'])
    expect(cells[1].style.background).toContain('var(--up) 22%')
    expect(cells[2].style.background).toBe('var(--panel2)') // a small move stays neutral
    const lt = [...container.querySelectorAll<HTMLElement>('[data-cell="long_term"]')]
    expect(lt[1].style.background).toContain('var(--down) 18%')
    expect(screen.getByText('2025')).toBeTruthy()
    expect(screen.getByText('2026')).toBeTruthy()
  })

  it('says whether the book was ahead in words as well as marks', () => {
    const { container } = render(<MonthGrid months={months} bookLabel="Real" money="real" ariaLabel="Months" />)
    const ahead = [...container.querySelectorAll('[data-cell="ahead"]')].map((c) => c.textContent)
    expect(ahead).toEqual(['', 'yes', '−no'])
  })

  it('reads out a month from the keyboard', () => {
    render(<MonthGrid months={months} bookLabel="Real" money="real" ariaLabel="Months" />)
    const group = screen.getByRole('group', { name: 'Months' })
    fireEvent.keyDown(group, { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe('Jan 2026Real+0.3%Long-term+2.9%Ahead?no')
    // scrolled sideways (a narrow panel), the tooltip still follows the month, not the unscrolled grid
    const before = parseFloat(screen.getByRole('status').style.left)
    fireEvent.scroll(group.parentElement!, { target: { scrollLeft: 100 } })
    expect(parseFloat(screen.getByRole('status').style.left)).toBeCloseTo(before - 100)
  })

  it('has a table view', () => {
    render(<MonthTable months={months} bookLabel="Real" />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows.map((r) => r.textContent)).toEqual([
      'MonthRealLong-termAhead?', 'Nov 2025———', 'Dec 2025+1.2%−0.8%yes', 'Jan 2026+0.3%+2.9%no',
    ])
  })

  it('says so when there is no monthly history', () => {
    render(<MonthGrid months={[months[0]]} bookLabel="Real" money="real" ariaLabel="Months" />)
    expect(screen.getByText('No monthly history yet.')).toBeTruthy()
  })
})
