import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CandleChart, CandleTable } from './CandleChart'

const bars = [
  { date: '2026-09-14', open: 101, high: 102, low: 99, close: 100 },
  { date: '2026-09-15', open: 100, high: 101.5, low: 99.2, close: 101 },
  { date: '2026-09-16', open: 101, high: 104, low: 100.5, close: 103.5 },
  { date: '2026-09-17', open: 104, high: 105, low: 103, close: 104.4 },
]
const rsi = { label: 'RSI(2)', values: [null, null, 88.2, 93.1],
  lines: [{ value: 10, label: 'buy under 10' }, { value: 70, label: 'sell over 70' }] }
const trade = { entry: 1, exit: 3, entryPrice: 100, exitPrice: 104 }

describe('CandleChart', () => {
  it('draws the candles, the holding window, both markers and the stop, on the scale and clear of the axis', () => {
    const { container } = render(<CandleChart bars={bars} indicator={rsi} stop={92} {...trade} ariaLabel="HD" />)
    expect(container.querySelectorAll('[data-candle]')).toHaveLength(4)
    expect(container.querySelectorAll('[data-window]')).toHaveLength(2) // price panel and indicator panel
    expect(screen.getByText('Buy 100.00')).toBeTruthy()
    expect(screen.getByText('Sell 104.00')).toBeTruthy()
    expect(screen.getByText('Stop 92.00 · −8%')).toBeTruthy()
    expect(screen.getByText('RSI(2)')).toBeTruthy()
    // the exit is the last bar, so the stop label sits inside the window, clear of the price axis (the plot is 588 wide)
    const label = screen.getByText('Stop 92.00 · −8%')
    expect([label.getAttribute('text-anchor'), Number(label.getAttribute('x')) <= 588]).toEqual(['end', true])
    // a stop above every high still lands on the price panel (210 tall)
    const above = render(<CandleChart bars={bars} indicator={null} stop={110} {...trade} ariaLabel="HD" />)
    const y1 = Number(above.container.querySelector('line[stroke="var(--serious)"]')?.getAttribute('y1'))
    expect(y1 >= 4 && y1 <= 206).toBe(true)
  })

  it('leaves out the stop and the indicator panel when the chart has none', () => {
    const { container } = render(<CandleChart bars={bars} indicator={null} stop={null} {...trade} ariaLabel="HD" />)
    expect(screen.queryByText(/^Stop/)).toBeNull()
    expect(container.querySelectorAll('[data-window]')).toHaveLength(1)
  })

  it('reads out a session from the keyboard', () => {
    render(<CandleChart bars={bars} indicator={rsi} stop={92} {...trade} ariaLabel="HD" />)
    fireEvent.keyDown(screen.getByRole('img', { name: 'HD' }), { key: 'End' })
    expect(screen.getByRole('status').textContent).toBe(
      'Thu 17 SepOpen104.00High105.00Low103.00Close104.40RSI(2)93.1')
  })

  it('has a table view that marks the buy and the sell', () => {
    render(<CandleTable bars={bars} indicator={rsi} entry={1} exit={3} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows).toHaveLength(5)
    expect(rows[0].textContent).toBe('DateOpenHighLowCloseRSI(2)Trade')
    expect(rows[2].textContent).toBe('Tue 15 Sep100.00101.5099.20101.00—Buy')
    expect(rows[4].textContent).toContain('Sell')
  })

  it('says so when there are no bars', () => {
    render(<CandleChart bars={[]} indicator={null} stop={null} {...trade} ariaLabel="HD" />)
    expect(screen.getByText('No chart for this trade.')).toBeTruthy()
  })
})
