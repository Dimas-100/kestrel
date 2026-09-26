import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SlotsStrip, SlotsTable } from './SlotsStrip'

const days = ['2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25']
const used = [0, 2, 5, 7, 3] // more in use than there are slots still draws a full column

describe('SlotsStrip', () => {
  it('fills a column of slots per session from the bottom up', () => {
    const { container } = render(<SlotsStrip days={days} used={used} total={5} money="real" ariaLabel="Slots" />)
    expect(container.querySelectorAll('[data-mark="real"]')).toHaveLength(0 + 2 + 5 + 5 + 3)
    expect(container.querySelectorAll('[data-mark="free"]')).toHaveLength(5 + 3 + 0 + 0 + 2)
  })

  it('hatches a paper book', () => {
    const { container } = render(<SlotsStrip days={days} used={used} total={5} money="paper" ariaLabel="Slots" />)
    expect(container.querySelectorAll('[data-mark="paper"]')).toHaveLength(15)
    expect(container.querySelector('pattern')).not.toBeNull()
  })

  it('reads out a session from the keyboard, with the true count', () => {
    render(<SlotsStrip days={days} used={used} total={5} money="real" ariaLabel="Slots" />)
    const chart = screen.getByRole('img', { name: 'Slots' })
    fireEvent.keyDown(chart, { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe('Fri 25 SepIn use3 of 5')
    fireEvent.keyDown(chart, { key: 'ArrowLeft' })
    expect(screen.getByRole('status').textContent).toBe('Thu 24 SepIn use7 of 5')
  })

  it('has a table view', () => {
    render(<SlotsTable days={days} used={used} total={5} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(6)
    expect(rows[1].textContent).toBe('Fri 25 Sep3 of 5') // newest first
  })

  it('says so when there are no sessions', () => {
    render(<SlotsStrip days={[]} used={[]} total={5} money="real" ariaLabel="Slots" />)
    expect(screen.getByText('No sessions yet.')).toBeTruthy()
  })
})
