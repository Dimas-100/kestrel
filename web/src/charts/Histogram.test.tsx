import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { bucketLabel, Histogram, HistogramTable } from './Histogram'

const buckets = Array.from({ length: 20 }, (_, i) => ({
  low: i - 10, count: i === 12 ? 3 : i === 0 ? 1 : 0, share: i === 12 ? 75 : i === 0 ? 25 : 0, expected: 5,
}))

describe('Histogram', () => {
  it('names its buckets, the end ones holding everything beyond', () => {
    expect([bucketLabel(-10), bucketLabel(-1), bucketLabel(2), bucketLabel(9)])
      .toEqual(['under −9%', '−1% to 0%', '+2% to +3%', '+9% or more'])
  })

  it('draws the backtest behind the trades and reads out a bucket from the keyboard', () => {
    const { container } = render(<Histogram buckets={buckets} money="real" ariaLabel="Trade returns" />)
    expect(container.querySelectorAll('[data-mark="expected"]')).toHaveLength(20)
    expect(container.querySelectorAll('[data-mark="real"]')).toHaveLength(2) // the empty buckets draw nothing
    const chart = screen.getByRole('img', { name: 'Trade returns' })
    fireEvent.keyDown(chart, { key: 'Home' })
    const tip = screen.getByRole('status')
    expect(tip.textContent).toContain('Trades returning under −9%')
    expect(tip.textContent).toContain('Real1 trade · 25%')
    expect(tip.textContent).toContain('Backtest5% of trades')
    fireEvent.keyDown(chart, { key: 'Escape' })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('hatches a paper book', () => {
    const { container } = render(<Histogram buckets={buckets} money="paper" ariaLabel="Trade returns" />)
    expect(container.querySelectorAll('[data-mark="paper"]')).toHaveLength(2)
    expect(container.querySelector('pattern')).not.toBeNull()
  })

  it('has a table view with every bucket', () => {
    render(<HistogramTable buckets={buckets} money="real" />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(21)
    expect(rows[13].textContent).toBe('+2% to +3%375%5%')
  })

  it('says so when there is nothing to draw', () => {
    const empty = buckets.map((b) => ({ ...b, count: 0, share: 0, expected: null }))
    render(<Histogram buckets={empty} money="real" ariaLabel="Trade returns" />)
    expect(screen.getByText('No closed trades yet.')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
