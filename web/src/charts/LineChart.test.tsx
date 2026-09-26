import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LineChart } from './LineChart'

const props = (dates: string[], values: number[]) => ({
  dates, height: 120, ariaLabel: 'Test chart', yFormat: String, valueFormat: String, xLabel: (d: string) => d,
  tipTitle: (d: string) => `Day ${d}`,
  series: [{ key: 'a', label: 'A', values, color: 'var(--s1)', style: 'solid' as const }],
})

describe('LineChart', () => {
  afterEach(() => vi.restoreAllMocks())

  it('ignores the pointer and keys when it has no dates', () => {
    render(<LineChart {...props([], [])} />)
    const chart = screen.getByRole('img', { name: 'Test chart' })
    fireEvent.pointerMove(chart, { clientX: 30 })
    for (const key of ['ArrowRight', 'ArrowLeft', 'Home', 'End']) fireEvent.keyDown(chart, { key })
    expect(screen.queryByRole('status')).toBeNull() // no tooltip for a day that doesn't exist
  })

  it('keeps the tooltip inside a narrow chart', () => {
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(200) // a phone-width panel
    render(<LineChart {...props(['2026-09-24', '2026-09-25'], [1, 2])} />)
    const chart = screen.getByRole('img', { name: 'Test chart' })
    for (const key of ['Home', 'End']) {
      fireEvent.keyDown(chart, { key })
      const left = parseFloat(screen.getByRole('status').style.left)
      expect(left).toBeGreaterThanOrEqual(0)
      expect(left).toBeLessThanOrEqual(200 - 190)
    }
  })

  it('draws an expected band and reads it out in the tooltip', () => {
    render(<LineChart {...props(['1', '2', '3'], [1, 2, 3])}
      band={{ lo: [null, 0, 0.5], hi: [null, 2, 1.5], label: 'Expected range' }} />)
    const chart = screen.getByRole('img', { name: 'Test chart' })
    expect(chart.querySelector('[data-band="wash"]')).not.toBeNull()
    fireEvent.keyDown(chart, { key: 'End' })
    expect(screen.getByRole('status').textContent).toContain('Expected range0.5 to 1.5')
    fireEvent.keyDown(chart, { key: 'Home' })
    expect(screen.getByRole('status').textContent).toContain('Expected range—') // no band before trade 3
  })

  it('labels the end of a series that asks for it, where that series ends', () => {
    const series = [{ key: 'a', label: 'A', values: [1, 2, null], color: 'var(--s2)', style: 'solid' as const,
      endLabel: 'Real +2%' }]
    render(<LineChart {...props(['1', '2', '3'], [1, 2, 3])} series={series} />)
    expect(screen.getByText('Real +2%')).toBeTruthy()
  })
})
