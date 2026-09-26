import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { pct } from '../lib/format'
import { CategoryChip, Delta, type Sort, SortHeader, Stat, toggleSort } from './bits'

describe('Delta', () => {
  it('treats a value that rounds to zero at its shown precision as no change', () => {
    const { container } = render(<Delta value={0.03} digits={1}>{pct(0.03)}</Delta>)
    expect(container.textContent).toBe('0.0%')
    expect(container.textContent).not.toContain('▲')
  })

  it('still marks a change that shows', () => {
    const { container } = render(<Delta value={0.06} digits={1}>{pct(0.06)}</Delta>)
    expect(container.textContent).toContain('▲')
    expect(container.textContent).toContain('+0.1%')
  })
})

describe('shared pieces', () => {
  it('writes a stat block as a label, the value and a second line', () => {
    const { container } = render(<Stat label="Started at" sub="1 Jan">$1,000.00</Stat>)
    expect(container.textContent).toBe('Started at$1,000.001 Jan')
    expect(container.querySelector('.label')?.textContent).toBe('Started at')
  })

  it('sorts by a column heading, and flips the order when it is clicked again', () => {
    const sorted: Sort<'value' | 'gain'>[] = []
    const sort: Sort<'value' | 'gain'> = { key: 'value', dir: 'desc' }
    render(
      <table><thead><tr>
        <SortHeader label="Value" k="value" sort={sort} onSort={(k) => sorted.push(toggleSort(sort, k))} right />
        <SortHeader label="Gain" k="gain" sort={sort} onSort={(k) => sorted.push(toggleSort(sort, k))} right />
      </tr></thead></table>,
    )
    const [value, gain] = screen.getAllByRole('columnheader')
    expect([value.getAttribute('aria-sort'), gain.getAttribute('aria-sort')]).toEqual(['descending', 'none'])
    fireEvent.click(screen.getByRole('button', { name: 'Value' }))
    fireEvent.click(screen.getByRole('button', { name: 'Gain' }))
    expect(sorted).toEqual([{ key: 'value', dir: 'asc' }, { key: 'gain', dir: 'desc' }])
  })

  it('names a category in words beside its dot', () => {
    const { container } = render(<><CategoryChip category="long_term" /><CategoryChip category="cash" /></>)
    expect([...container.querySelectorAll('.chip')].map((c) => c.textContent)).toEqual(['Long-term', 'Cash'])
    expect(container.querySelector('.chip span')?.getAttribute('style')).toContain('var(--s1)')
  })
})
