import { fireEvent, screen, within } from '@testing-library/react'
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

  it('tells a missing stop from one not on record and from a signal exit, with the source notes under the table', async () => {
    const base = bookFixture.positions[0] // MSFT: stop_price null, stop_resting true, flag null
    const unknown = { ...base, symbol: 'XOM', stop_price: null, stop_resting: null, flag: 'unknown_stop' as const,
      room_pct: null, note: 'no recent price in the store: marked at the entry price' }
    const none = { ...base, symbol: 'CVX', stop_price: null, stop_resting: false, flag: 'no_stop' as const, room_pct: null }
    const resting = { ...base, symbol: 'MSFT', stop_price: null, stop_resting: true, flag: null, room_pct: null }
    const signal = { ...base, symbol: 'XLF', stop_price: null, stop_resting: null, flag: 'signal_exit' as const, room_pct: null }
    const view = { ...bookFixture, positions: [unknown, none, resting, signal],
      notes: ['no recent price in the store: marked at the entry price'], freshness: 'oldest mark 2 sessions old' }
    renderApp('/books/rsi2-real', { book: [{ id: 'rsi2-real', view }] })
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    const rowFor = (symbol: string) =>
      within(positions).getAllByRole('row').find((r) => r.textContent?.includes(symbol)) as HTMLElement
    const cvx = rowFor('CVX')
    expect(within(cvx).getByText('No stop')).toBeTruthy()
    expect(cvx.querySelector('svg')).toBeTruthy() // the shield icon: never colour alone
    expect(within(rowFor('XOM')).getByText('not on record')).toBeTruthy()
    expect(within(rowFor('XLF')).getByText('signal exit')).toBeTruthy()
    const restingRow = rowFor('MSFT')
    expect(within(restingRow).getByText('resting (level not reported)')).toBeTruthy()
    expect(within(restingRow).queryByText('No stop')).toBeNull()
    // the marks' date and freshness, the protection rule, and the source's own note reach the page
    expect(within(positions).getByText(/^4 open · a resting stop on every lot · marks from 25 Sep \(oldest mark 2 sessions old\)$/))
      .toBeTruthy()
    expect(within(positions).getByText('no recent price in the store: marked at the entry price')).toBeTruthy()
  })

  it('shows realized, unrealized and combined P/L, and what the return is measured on', async () => {
    renderApp('/books/rsi2-real')
    const scorecard = (await screen.findByRole('heading', { name: 'Scorecard' })).closest('section') as HTMLElement
    expect(scorecard.textContent).toContain('Realized P/L▲ up +$741.20closed trades')
    expect(scorecard.textContent).toContain('Unrealized P/L▲ up +$86.20open positions')
    expect(scorecard.textContent).toContain('Combined P/L▲ up +$827.40realized + open')
    const equity = screen.getByRole('heading', { name: 'Equity' }).closest('section') as HTMLElement
    expect(within(equity).getByText(/measured on The trading account's value; deposits are taken out of the return$/))
      .toBeTruthy()
  })

  it('names the benchmark, says when its history starts later, and offers a table view', async () => {
    const e = bookFixture.equity
    const later = { ...e, benchmark: e.benchmark.map((b, i) => (i < 3 ? null : b)), benchmark_from: e.dates[3] }
    renderApp('/books/rsi2-real', { book: [{ id: 'rsi2-real', view: { ...bookFixture, equity: later } }] })
    const equity = (await screen.findByRole('heading', { name: 'Equity' })).closest('section') as HTMLElement
    expect(within(equity).getByText('S&P 500')).toBeTruthy() // the legend names it
    expect(within(equity).getByText(/^S&P 500 is drawn from 30 Sep, where its history starts/)).toBeTruthy()
    expect(within(equity).getByRole('img', { name: "The book's return since it started, against S&P 500" })).toBeTruthy()
    fireEvent.click(within(equity).getByRole('button', { name: 'Table' }))
    const rows = within(equity).getAllByRole('row')
    expect(rows[0].textContent).toBe('DayBookS&P 500Drawdown')
    expect(rows).toHaveLength(e.dates.length + 1)
    expect(rows[rows.length - 1].textContent).toContain('—') // the first day: the benchmark hasn't started
  })

  it('says so when there is no benchmark over the book\'s dates', async () => {
    const e = { ...bookFixture.equity, benchmark: bookFixture.equity.benchmark.map(() => null), benchmark_from: null }
    renderApp('/books/rsi2-real', { book: [{ id: 'rsi2-real', view: { ...bookFixture, equity: e } }] })
    const equity = (await screen.findByRole('heading', { name: 'Equity' })).closest('section') as HTMLElement
    expect(within(equity).getByText('No benchmark history over these dates.')).toBeTruthy()
    expect(within(equity).queryByText('S&P 500')).toBeNull()
  })

  it('lists what needs you on this book under the header', async () => {
    renderApp('/books/rsi2-real')
    await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })
    const list = screen.getByRole('list', { name: 'Needs you on this book' })
    expect(within(list).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'WarningEvening run failed Mon 17:45 · The broker timed out; the retry at 18:15 ran',
    ])
  })

  it('shows the win rate as a rate, never with a sign', async () => {
    renderApp('/books/rsi2-real', { book: [{ id: 'rsi2-real', view: { ...bookFixture,
      scorecard: { ...bookFixture.scorecard, win_rate: 62.5 } } }] })
    const scorecard = (await screen.findByRole('heading', { name: 'Scorecard' })).closest('section') as HTMLElement
    expect(within(scorecard).getByText('Win rate').parentElement?.textContent).toBe('Win rate62.5%')
  })

  it('keeps two lots of one symbol apart', async () => {
    // two AAPL lots in one book: rows keyed by book, symbol and opened day, so React never folds them together
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    const lot = { ...bookFixture.positions[1], symbol: 'AAPL' }
    const view = { ...bookFixture, positions: [{ ...lot, opened: '2026-09-21', quantity: 3 },
      { ...lot, opened: '2026-09-24', quantity: 5 }] }
    renderApp('/books/rsi2-real', { book: [{ id: 'rsi2-real', view }] })
    const panel = (await screen.findByRole('heading', { name: 'Open positions' })).closest('section') as HTMLElement
    expect(within(panel).getAllByText('AAPL')).toHaveLength(2)
    expect(errors.mock.calls.flat().join(' ')).not.toMatch(/same key/)
    errors.mockRestore()
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
