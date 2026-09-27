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

describe('Home', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with net worth, cents dimmed', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    const [whole, cents] = homeFixture.net_worth.total.toFixed(2).split('.')
    expect(within(nw).getByText(`$${Number(whole).toLocaleString('en-US')}`)).toBeTruthy()
    expect(within(nw).getByText(`.${cents}`)).toBeTruthy()
  })

  it('says what is owed under net worth, and nothing when nothing is', async () => {
    const { unmount } = renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    expect(homeFixture.net_worth.owed).toBe(640) // the demo's card, already taken off the total
    expect(within(nw).getByText(/owed$/).textContent).toBe('net of $640.00 owed')
    unmount()
    for (const owed of [0, -25]) { // nothing owed, or a card paid past zero: no line
      const { unmount: done } = renderApp('/', { home: { ...homeFixture, net_worth: { ...homeFixture.net_worth, owed } } })
      expect((await screen.findByRole('region', { name: 'Net worth' })).textContent).not.toContain('owed')
      done()
    }
  })

  it('opens an account from Where it sits', async () => {
    renderApp('/')
    const where = await screen.findByRole('region', { name: 'Where it sits' })
    const roth = within(where).getByRole('link', { name: /^Roth IRA/ })
    expect(roth.getAttribute('href')).toBe('/accounts/roth')
    expect(within(where).getAllByRole('link')).toHaveLength(homeFixture.accounts.length + 1) // and "4 accounts"
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
    expect(items[0].textContent).toContain('MSFT has no resting stop')
    expect(items[0].textContent).toContain('Serious')
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

describe('words from the data', () => {
  it('writes the summary sentence', async () => {
    const base = homeFixture
    expect(summaryParts(base).needs).toBe('2 items need you.')
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
    expect(v?.caveat).toBe('34 real trades so far — early evidence. The strategy is reviewed at 50.')
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
})
