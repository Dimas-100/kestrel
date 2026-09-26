import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { pct } from '../lib/format'
import { Delta } from './bits'

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
