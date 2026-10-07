import { act, fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { HomeView } from '../../lib/api'
import { setCurrency } from '../../lib/format'
import { homeFixture, renderApp, shellFixture } from '../../test/renderApp'
import { period, verdict } from './ComparisonPanel'
import { summaryParts } from './Home'

const panel = (name: string) => screen.getByRole('region', { name })

const empty: HomeView = {
  ...homeFixture, allocation: [], accounts: [], attention: [], books: [], today: [], positions: [],
  comparison: { ...homeFixture.comparison, lines: [], dates: [], gap_pts: null, shallower: null },
  net_worth: { ...homeFixture.net_worth, total: 0, owed: 0, points: [] },
  summary: { day_change: 0, gap_pts: null, needs_you: 0 },
}

describe('Home', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with net worth, cents dimmed', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    const [whole, cents] = homeFixture.net_worth.total.toFixed(2).split('.')
    expect(within(nw).getByText(`$${Number(whole).toLocaleString('en-US')}`)).toBeTruthy()
    expect(within(nw).getByText(`.${cents}`)).toBeTruthy()
  })

  it('says what is owned and owed under net worth, and nothing when nothing is owed', async () => {
    const { unmount } = renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    expect(homeFixture.net_worth.owed).toBe(640) // the demo's card, already taken off the total
    expect(within(nw).getByText(/^you own/).textContent).toBe('you own $168,918.24 · owe $640.00')
    unmount()
    for (const owed of [0, -25]) { // nothing owed, or a card paid past zero: no line
      const { unmount: done } = renderApp('/', { home: { ...homeFixture, net_worth: { ...homeFixture.net_worth, owed } } })
      expect((await screen.findByRole('region', { name: 'Net worth' })).textContent).not.toContain('owed')
      done()
    }
  })

  it('says under the chart when some accounts have no history, and nothing when all do', async () => {
    expect(homeFixture.net_worth.no_history).toBe(0) // every demo account has a history
    const { unmount } = renderApp('/')
    expect((await screen.findByRole('region', { name: 'Net worth' })).textContent).not.toContain('no history')
    unmount()
    for (const [n, text] of [[1, "1 account has no history: counted at today's balance"],
      [2, "2 accounts have no history: counted at today's balance"]] as const) {
      const { unmount: done } = renderApp('/', { home: { ...homeFixture, net_worth: { ...homeFixture.net_worth,
        no_history: n } } })
      expect(within(await screen.findByRole('region', { name: 'Net worth' })).getByText(text)).toBeTruthy()
      done()
    }
  })

  it('opens an account from Where it sits', async () => {
    renderApp('/')
    const where = await screen.findByRole('region', { name: 'Where it sits' })
    const roth = within(where).getByRole('link', { name: /^Roth IRA/ })
    expect(roth.getAttribute('href')).toBe('/accounts/roth')
    // "N accounts", one link per account row, and the "Owed" line (the demo's card is 640, so it shows)
    expect(within(where).getAllByRole('link')).toHaveLength(homeFixture.accounts.length + 2)
    const owed = within(where).getByRole('link', { name: /^Owed/ })
    expect(owed.getAttribute('href')).toBe('/reserves')
    expect(owed.textContent).toBe('Owed: $640.00 across 1 account')
  })

  it('shows a debt row in Where it sits as owed, in words that stay on a phone', async () => {
    renderApp('/')
    const where = await screen.findByRole('region', { name: 'Where it sits' })
    const card = within(where).getByRole('link', { name: /^Credit card/ })
    const owed = within(card).getByText('$640.00 owed')
    expect(owed.className).not.toMatch(/hidden/) // not the category word, which a phone hides
    expect(owed.className).toMatch(/whitespace-nowrap/) // one line: the name truncates first, never the figure
    expect(card.textContent).not.toMatch(/\$640\.00(?! owed)/)
  })

  it('opens each book from the books table', async () => {
    renderApp('/')
    await screen.findByRole('region', { name: 'Books' })
    const hrefs = within(panel('Books')).getAllByRole('link').map((a) => a.getAttribute('href') ?? '')
    expect(hrefs.filter((h) => h.startsWith('/books/'))).toEqual(homeFixture.books.map((b) => `/books/${b.id}`))
  })

  it('gives the account name priority over its category word when the row is tight', async () => {
    // screenshot pass, 2026-09-28: at 1200px this span-4 panel has room for barely more than the name, so the
    // name (flex-1, min-w-0) must claim space before the fixed category word does, or it truncates far worse
    renderApp('/')
    const where = await screen.findByRole('region', { name: 'Where it sits' })
    const roth = within(where).getByRole('link', { name: /^Roth IRA/ })
    const nameSpan = within(roth).getByText('Roth IRA').parentElement as HTMLElement
    expect(nameSpan.className).toMatch(/\bflex-1\b/)
    expect(nameSpan.className).toMatch(/\bmin-w-0\b/)
  })

  it('says nothing is owed when nothing is', async () => {
    const none = { ...homeFixture, net_worth: { ...homeFixture.net_worth, owed: 0, debt_accounts: 0 } }
    renderApp('/', { home: none })
    const where = await screen.findByRole('region', { name: 'Where it sits' })
    expect(within(where).queryByText(/^Owed/)).toBeNull()
  })

  it('switches a chart to its table', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    fireEvent.click(within(nw).getByRole('button', { name: 'Table' }))
    expect(within(nw).getByRole('table')).toBeTruthy()
    expect(within(nw).getAllByRole('row').length).toBeGreaterThan(200) // a year of weekdays
  })

  it('shows what needs you, most serious first', async () => {
    renderApp('/')
    const items = within(await screen.findByRole('region', { name: 'Needs you' })).getAllByRole('listitem')
    // MSFT's stop rests but isn't reported: no false alarm, so the top item is the stale-source warning
    expect(items[0].textContent).toContain("Savings hasn't synced")
    expect(items[0].textContent).toContain('Warning')
  })

  it('shows a resting-but-unreported stop in words, with no alarm and no room to stop', async () => {
    renderApp('/')
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    const msft = within(positions).getAllByRole('row').find((r) => r.textContent?.includes('MSFT')) as HTMLElement
    const restingLabel = within(msft).getByText('resting (level not reported)')
    expect(restingLabel).toBeTruthy()
    expect(within(msft).queryByText('No stop')).toBeNull()
    // the label wraps rather than forcing the Stop column wide (screenshot pass, 2026-09-28): it must NOT carry
    // whitespace-nowrap, or the table needs to scroll to show P/L on a 1440px desktop panel
    expect(restingLabel.className).not.toMatch(/whitespace-nowrap/)
    const needsYou = within(await screen.findByRole('region', { name: 'Needs you' })).getAllByRole('listitem')
    expect(needsYou.some((li) => li.textContent?.includes('MSFT'))).toBe(false)
  })

  it('keeps a P/L figure on one line even though the resting-stop label above it wraps', async () => {
    renderApp('/')
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    const msft = within(positions).getAllByRole('row').find((r) => r.textContent?.includes('MSFT')) as HTMLElement
    const pnlCell = msft.querySelector('td:last-child') as HTMLElement
    expect(pnlCell.style.whiteSpace).toBe('nowrap')
  })

  it('tells a real position whose source says there is no stop from one with nothing on record', async () => {
    // the view's flag drives the words: "No stop" (serious) only when the source says there is none; "not on
    // record" (a warning) when nothing is reported; "signal exit" for a strategy that never rests one
    const base = homeFixture.positions.find((p) => p.money === 'real')!
    const unknown = { ...base, symbol: 'XOM', stop_price: null, stop_resting: null, room_pct: null, flag: 'unknown_stop' as const }
    const none = { ...base, symbol: 'CVX', stop_price: null, stop_resting: false, room_pct: null, flag: 'no_stop' as const }
    const resting = { ...base, symbol: 'MSFT', stop_price: null, stop_resting: true, room_pct: null, flag: null }
    const signal = { ...base, symbol: 'XLF', money: 'paper' as const, stop_price: null, stop_resting: null, room_pct: null,
      flag: 'signal_exit' as const }
    renderApp('/', { home: { ...homeFixture, positions: [unknown, none, resting, signal] } })
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    const rowFor = (symbol: string) =>
      within(positions).getAllByRole('row').find((r) => r.textContent?.includes(symbol)) as HTMLElement
    const cvx = rowFor('CVX')
    expect(within(cvx).getByText('No stop')).toBeTruthy()
    expect(cvx.querySelector('svg')).toBeTruthy() // the shield icon: never colour alone
    const xom = rowFor('XOM')
    expect(within(xom).getByText('not on record')).toBeTruthy()
    expect(within(xom).queryByText('No stop')).toBeNull()
    expect(within(rowFor('XLF')).getByText('signal exit')).toBeTruthy()
    const restingRow = rowFor('MSFT')
    expect(within(restingRow).getByText('resting (level not reported)')).toBeTruthy()
    expect(within(restingRow).queryByText('No stop')).toBeNull()
  })

  it('reveals every needs-you item in place, then collapses back, never linking out to Activity', async () => {
    renderApp('/')
    const panel = await screen.findByRole('region', { name: 'Needs you' })
    expect(within(panel).getAllByRole('listitem')).toHaveLength(3)
    fireEvent.click(within(panel).getByRole('button', { name: `Show all ${homeFixture.attention.length}` }))
    expect(within(panel).getAllByRole('listitem')).toHaveLength(homeFixture.attention.length)
    expect(within(panel).queryByRole('link', { name: /Activity/ })).toBeNull()
    fireEvent.click(within(panel).getByRole('button', { name: 'Show fewer' }))
    expect(within(panel).getAllByRole('listitem')).toHaveLength(3)
  })

  it('lists every book with its real/paper badge', async () => {
    renderApp('/')
    await screen.findByRole('region', { name: 'Books' })
    const rows = within(panel('Books')).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(homeFixture.books.length)
    expect(rows[0].textContent).toContain('REAL')
    expect(within(panel('Books')).getByText('Below band')).toBeTruthy()
  })

  it('puts the now line between done and due runs', async () => {
    renderApp('/')
    const today = await screen.findByRole('region', { name: 'Today' })
    const labels = within(today).getAllByRole('listitem').map((li) => li.getAttribute('aria-label') ?? li.textContent)
    const nowAt = labels.findIndex((l) => l?.startsWith('Now'))
    expect(labels[nowAt - 1]).toContain('ETF close entries')
    expect(labels[nowAt + 1]).toContain('Nightly suite')
  })

  it('caps the positions table and links to the rest', async () => {
    renderApp('/')
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    expect(within(positions).getAllByRole('row')).toHaveLength(6) // header + 5
    expect(within(positions).getByText(`${homeFixture.positions.length - 5} more in Books`)).toBeTruthy()
  })

  it('handles a person with no data yet', async () => {
    renderApp('/', { home: empty })
    expect(await screen.findByText('Nothing needs you right now.')).toBeTruthy()
    expect(screen.getByText('No open positions.')).toBeTruthy()
    expect(within(panel('Trading vs your index money')).getByText(/No history yet/)).toBeTruthy()
    expect(within(panel('Net worth')).getByText(/No history yet/)).toBeTruthy()
  })

  it('survives a pointer or key on an empty chart', async () => {
    renderApp('/', { home: empty })
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    const chart = within(nw).queryByRole('img') ?? nw
    fireEvent.pointerMove(chart, { clientX: 40 })
    fireEvent.keyDown(chart, { key: 'ArrowRight' })
    expect(screen.getByRole('region', { name: 'Net worth' })).toBeTruthy()
    expect(screen.queryByText(/Something went wrong/)).toBeNull()
  })

  it('keeps what it showed when a refresh fails', async () => {
    const { client } = renderApp('/')
    await screen.findByRole('region', { name: 'Net worth' })
    act(() => client.getQueryCache().find({ queryKey: ['home'] })?.setState({
      status: 'error', error: new Error('/api/home answered 502'), fetchStatus: 'idle',
    }))
    expect((await screen.findByRole('alert')).textContent).toMatch(/refresh.*502/)
    expect(screen.getByRole('region', { name: 'Net worth' })).toBeTruthy()
  })

  it('prints a stop above the last price with a true minus sign', async () => {
    const positions = homeFixture.positions.map((p, i) => (i === 1 ? { ...p, room_pct: -2.5 } : p))
    renderApp('/', { home: { ...homeFixture, positions } })
    const table = await screen.findByRole('region', { name: 'Open positions' })
    expect(within(table).getByText('−2.5%')).toBeTruthy()
  })

  describe('in another currency', () => {
    afterEach(() => setCurrency('USD'))

    it('shows every amount in the profile currency from the first render', async () => {
      renderApp('/', { shell: { ...shellFixture, app: { ...shellFixture.app, currency: 'EUR' } } })
      const nw = await screen.findByRole('region', { name: 'Net worth' })
      const [whole] = homeFixture.net_worth.total.toFixed(2).split('.')
      expect(within(nw).getByText(`€${Number(whole).toLocaleString('en-US')}`)).toBeTruthy()
      expect(nw.textContent).not.toContain('$')
    })
  })

  it('marks returns as gains or losses, never by colour alone', async () => {
    renderApp('/')
    const cmp = await screen.findByRole('region', { name: 'Trading vs your index money' })
    expect(within(cmp).getAllByText('up')).toHaveLength(3)
  })
})

describe('words from the data', { timeout: 15_000 }, () => {
  it('writes the summary sentence', async () => {
    const base = homeFixture
    expect(summaryParts(base).needs).toBe('4 items need you.')
    expect(summaryParts(base).trading).toBe('Trading is ahead of your index money by 2.9 pts this year.')
    const behind = { ...base, summary: { ...base.summary, gap_pts: -1.26, needs_you: 1 } }
    expect(summaryParts(behind)).toEqual({
      trading: 'Trading is behind your index money by 1.3 pts this year.', needs: 'One item needs you.',
    })
    expect(summaryParts({ ...base, summary: { ...base.summary, gap_pts: null, needs_you: 0 } }))
      .toEqual({ trading: null, needs: 'Nothing needs you.' })
    // a weekend or a flat day: no "$0.00", no arrow
    renderApp('/', { home: { ...base, summary: { ...base.summary, day_change: 0.004 } } })
    expect(await screen.findByText(/^All your money is unchanged today\. Trading is ahead/)).toBeTruthy()
  })

  it('writes the verdict with its sample-size caveat', () => {
    const v = verdict(homeFixture.comparison)
    expect(v?.headline).toMatch(/^Trading is ahead by 2\.9 pts this year, with a shallower worst drop/)
    expect(v?.caveat).toBe('34 real trades so far.') // past the 20-trade review bar: no early-evidence caveat
    expect(verdict({ ...homeFixture.comparison, gap_pts: null })).toBeNull()
    const lt = homeFixture.comparison.lines.find((l) => l.key === 'long_term')!
    const level = homeFixture.comparison.lines.map((l) => (l.key === 'trading'
      ? { ...l, max_drop_pct: lt.max_drop_pct + 0.04 } : l))
    expect(verdict({ ...homeFixture.comparison, lines: level })?.headline).toMatch(/, with an equal worst drop \(/)
  })

  it('names no date when there is nothing to compare yet', () => {
    const none = { ...homeFixture.comparison, window: '12m' as const, start: '2025-09-25', dates: [], lines: [] }
    expect(period(none)).toEqual({ phrase: 'over the past 12 months', title: 'Past 12 months' })
  })

  it('names the shared start when a line begins later in the year', async () => {
    const late: HomeView = { ...homeFixture, comparison: { ...homeFixture.comparison, start: '2026-07-01' } }
    expect(summaryParts(late).trading).toBe('Trading is ahead of your index money by 2.9 pts since 1 Jul.')
    expect(verdict(late.comparison)?.headline).toMatch(/^Trading is ahead by 2\.9 pts since 1 Jul, with a/)
    // the year's first close can fall a few days into January: that is still "this year"
    const firstClose: HomeView = { ...homeFixture, comparison: { ...homeFixture.comparison, start: '2026-01-05' } }
    expect(summaryParts(firstClose).trading).toMatch(/this year\.$/)
    renderApp('/', { home: late })
    const cmp = await screen.findByRole('region', { name: 'Trading vs your index money' })
    expect(within(cmp).getByText(/^Since 1 Jul · real money only/)).toBeTruthy()
  })

  it('names the next round number and how far to it, and says so the day one is passed', async () => {
    const { unmount } = renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    expect(nw.textContent).toContain('$31,721.76 to $200,000')
    expect(within(nw).getByText('Next: $200,000')).toBeTruthy() // the reference line's legend entry
    expect(within(nw).queryByText(/^Passed/)).toBeNull()
    unmount()
    renderApp('/', { home: { ...homeFixture, net_worth: { ...homeFixture.net_worth, passed_today: 150000 } } })
    const again = await screen.findByRole('region', { name: 'Net worth' })
    expect(within(again).getByText('Passed $150,000 today')).toBeTruthy()
  })
})
