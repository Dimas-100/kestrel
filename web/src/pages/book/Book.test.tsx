import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { bookFixture, renderApp } from '../../test/renderApp'

describe('Book', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders the header, equity, scorecard, positions and trades', async () => {
    renderApp('/books/rsi2-real')
    expect(await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Mean reversion' }).getAttribute('href')).toBe('/strategies/rsi2')
    expect(screen.getByRole('heading', { name: 'Equity' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Scorecard' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Open positions' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'All trades' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Runs' })).toBeTruthy()
    // MSFT's stop rests but its level isn't reported: worded plainly, no alarm flag
    const restingLabel = screen.getByText('resting (level not reported)')
    expect(restingLabel).toBeTruthy()
    expect(screen.queryByText('No stop')).toBeNull()
    // it wraps rather than forcing the Stop column wide (screenshot pass, 2026-09-28), and the P/L figure beside
    // it stays on one line
    expect(restingLabel.className).not.toMatch(/whitespace-nowrap/)
    const pnlCell = restingLabel.closest('tr')?.querySelector('td:last-child') as HTMLElement
    expect(pnlCell.style.whiteSpace).toBe('nowrap')
    // 480, not 640 (screenshot pass, 2026-09-28): 640 was sized for the old one-line resting label and hid the
    // Days and P/L columns behind an unscrolled edge on a 1440px desktop panel
    const positionsTable = screen.getByRole('heading', { name: 'Open positions' }).closest('.panel')
      ?.querySelector('table') as HTMLTableElement
    expect(positionsTable.style.minWidth).toBe('480px')
    expect(screen.getAllByText(`${bookFixture.trades.length} closed trades`)).toHaveLength(2) // scorecard + trades table
  })

  it('flags a position with a genuinely missing stop: the shield icon and "No stop"', async () => {
    // stop_resting=true (MSFT in the fixture) must not be the only shape this page ever sees a position in: both
    // "not reported at all" (null) and an explicit "false" are a real missing stop and must still be flagged
    const base = bookFixture.positions[0] // MSFT: stop_price null, stop_resting true, flag null
    const noStopUnreported = { ...base, symbol: 'XOM', stop_price: null, stop_resting: null, flag: 'no_stop' as const,
      room_pct: null }
    const noStopFalse = { ...base, symbol: 'CVX', stop_price: null, stop_resting: false, flag: 'no_stop' as const,
      room_pct: null }
    const resting = { ...base, symbol: 'MSFT', stop_price: null, stop_resting: true, flag: null, room_pct: null }
    renderApp('/books/rsi2-real', {
      book: [{ id: 'rsi2-real', view: { ...bookFixture, positions: [noStopUnreported, noStopFalse, resting] } }],
    })
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    const rowFor = (symbol: string) =>
      within(positions).getAllByRole('row').find((r) => r.textContent?.includes(symbol)) as HTMLElement
    for (const symbol of ['XOM', 'CVX']) {
      const row = rowFor(symbol)
      expect(within(row).getByText('No stop')).toBeTruthy()
      expect(row.querySelector('svg')).toBeTruthy() // the shield icon: never colour alone
      expect(within(row).queryByText('resting (level not reported)')).toBeNull()
    }
    const restingRow = rowFor('MSFT')
    expect(within(restingRow).getByText('resting (level not reported)')).toBeTruthy()
    expect(within(restingRow).queryByText('No stop')).toBeNull()
  })

  it('says it is loading while the book is on its way', async () => {
    renderApp('/books/rsi2-real', { book: [] }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the book…')).toBeTruthy()
  })

  it('shows Not found for an unknown book', async () => {
    const answer = () => Promise.resolve(new Response('{"detail":"no such book: nope"}', { status: 404 }))
    renderApp('/books/nope', {}, answer)
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
  })

  it('says so when the book could not load', async () => {
    renderApp('/books/rsi2-real', { book: [] }, () =>
      Promise.resolve(new Response('oops', { status: 500, statusText: 'Server error' })))
    expect((await screen.findByRole('alert')).textContent).toContain('couldn’t load')
  })
})
