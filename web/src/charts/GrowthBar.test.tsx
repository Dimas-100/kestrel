import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { GrowthBar, GrowthTable, segments } from './GrowthBar'

const growth = { start: 1000, deposits: 500, market: 250, end: 1750 }
const width = (el: Element | null) => Number(el?.getAttribute('width'))
const left = (el: Element | null) => Number(el?.getAttribute('x'))

describe('GrowthBar', () => {
  it('puts the start, what you put in and the market end to end, with a tick at now', () => {
    const { container } = render(<GrowthBar growth={growth} ariaLabel="Growth" />)
    const [start, put, gain] = ['start', 'deposits', 'gain'].map((m) => container.querySelector(`[data-mark="${m}"]`))
    expect(width(start)).toBeCloseTo((1000 / 1750) * 640, 1) // jsdom charts are 640 wide
    expect(left(put)).toBeCloseTo(left(start) + width(start), 1)
    expect(left(gain) + width(gain)).toBeCloseTo(640, 1)
    expect(put?.getAttribute('stroke-dasharray')).toBe('1.5 2.5') // the reference money is dotted
    expect(container.querySelector('line')?.getAttribute('x1')).toBe('640')
  })

  it('runs a loss or a withdrawal back over the part before it', () => {
    expect(segments({ start: 1000, deposits: -200, market: -300, end: 500 })).toEqual([
      { key: 'start', from: 0, to: 1000 }, { key: 'deposits', from: 1000, to: 800 },
      { key: 'market', from: 800, to: 500 },
    ])
    const { container } = render(<GrowthBar growth={{ start: 1000, deposits: 500, market: -300, end: 1200 }}
      ariaLabel="Growth" />)
    const loss = container.querySelector('[data-mark="loss"]')
    expect(loss?.getAttribute('fill')).toBe('var(--down)')
    expect([left(loss), width(loss)].map((v) => Math.round(v))).toEqual([512, 128]) // 1200 to 1500 of 1500
  })

  it('reads out each part from the keyboard', () => {
    render(<GrowthBar growth={growth} ariaLabel="Growth" />)
    const chart = screen.getByRole('img', { name: 'Growth' })
    fireEvent.keyDown(chart, { key: 'Home' })
    expect(screen.getByRole('status').textContent).toBe('Started atAmount$1,000.00')
    fireEvent.keyDown(chart, { key: 'ArrowRight' })
    expect(screen.getByRole('status').textContent).toBe('You put inAmount$500.00')
    fireEvent.keyDown(chart, { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe('The market addedAmount+$250.00')
    fireEvent.keyDown(chart, { key: 'Escape' })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('has a table view', () => {
    render(<GrowthTable growth={{ ...growth, market: -250, end: 1250 }} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row').map((r) => r.textContent)
    expect(rows).toEqual(['PartAmount', 'Started at$1,000.00', 'You put in$500.00',
      'The market added▼ down −$250.00', 'Now$1,250.00'])
  })

  it('says so when there is nothing to show', () => {
    render(<GrowthBar growth={{ start: 0, deposits: 0, market: 0, end: 0 }} ariaLabel="Growth" />)
    expect(screen.getByText('Nothing to show yet.')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
