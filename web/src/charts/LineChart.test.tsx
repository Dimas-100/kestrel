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
})
