import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Scatter, type ScatterPoint, ScatterTable } from './Scatter'

const points: ScatterPoint[] = [
  { key: 'backtest', label: 'Backtest', sub: '+23.4%/yr · 2006–2020', period: '2006–2020', x: 11.7, y: 23.4,
    color: 'var(--s2)', style: 'dotted' },
  { key: 'book', label: 'Paper book', sub: '+19.0%/yr · 12 months', period: '12 months', x: 5.6, y: 19,
    color: 'var(--s2)', style: 'hatched' },
  { key: 'long_term', label: 'Long-term accounts', sub: '+21.4%/yr · 12 months', period: '12 months', x: 9, y: 21.4,
    color: 'var(--s1)', style: 'solid' },
]

describe('Scatter', () => {
  afterEach(() => vi.restoreAllMocks())

  it('draws and labels every point in its money style, with the guide line', () => {
    const { container } = render(<Scatter points={points} ariaLabel="Worth" />)
    const marks = [...container.querySelectorAll('[data-point]')].map((m) => m.getAttribute('data-point'))
    expect(marks).toEqual(['dotted', 'hatched', 'solid'])
    for (const p of points) {
      expect(screen.getByText(p.label)).toBeTruthy()
      expect(screen.getByText(p.sub)).toBeTruthy()
    }
    expect(screen.getByText('return = worst drop')).toBeTruthy()
    expect(screen.getByText('↖ better')).toBeTruthy()
  })

  it('moves the labels into a key under the chart when they would collide on it', () => {
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(220) // a narrow phone panel
    render(<Scatter points={points} ariaLabel="Worth" />)
    const key = screen.getByRole('list', { name: 'Key' })
    expect(within(key).getAllByRole('listitem').map((li) => li.textContent)).toEqual(points.map((p) => p.label + p.sub))
  })

  it('reads out a point from the keyboard', () => {
    render(<Scatter points={points} ariaLabel="Worth" />)
    fireEvent.keyDown(screen.getByRole('img', { name: 'Worth' }), { key: 'Home' })
    expect(screen.getByRole('status').textContent).toBe('Backtest · 2006–2020Yearly return+23.4%Worst drop−11.7%')
  })

  it('has a table view', () => {
    render(<ScatterTable points={points} />)
    const rows = within(screen.getByRole('table')).getAllByRole('row')
    expect(rows.map((r) => r.textContent)).toEqual([
      'LineYearly returnWorst dropOver',
      'Backtest+23.4%−11.7%2006–2020',
      'Paper book+19.0%−5.6%12 months',
      'Long-term accounts+21.4%−9.0%12 months',
    ])
  })

  it('says so when there is nothing to plot', () => {
    render(<Scatter points={[]} ariaLabel="Worth" />)
    expect(screen.getByText('Not enough history yet. A yearly figure needs at least 90 days.')).toBeTruthy()
  })
})
