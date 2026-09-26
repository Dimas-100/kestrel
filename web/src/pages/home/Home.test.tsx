import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { HomeView } from '../../lib/api'
import { homeFixture, renderApp } from '../../test/renderApp'
import { verdict } from './ComparisonPanel'
import { summaryParts } from './Home'

const panel = (name: string) => screen.getByRole('region', { name })

describe('Home', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with net worth, cents dimmed', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    const [whole, cents] = homeFixture.net_worth.total.toFixed(2).split('.')
    expect(within(nw).getByText(`$${Number(whole).toLocaleString('en-US')}`)).toBeTruthy()
    expect(within(nw).getByText(`.${cents}`)).toBeTruthy()
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
    const empty: HomeView = {
      ...homeFixture, allocation: [], accounts: [], attention: [], books: [], today: [], positions: [],
      comparison: { ...homeFixture.comparison, lines: [], dates: [], gap_pts: null, shallower: null },
      net_worth: { ...homeFixture.net_worth, total: 0, points: [] },
      summary: { day_change: 0, gap_pts: null, needs_you: 0 },
    }
    renderApp('/', { home: empty })
    expect(await screen.findByText('Nothing needs you right now.')).toBeTruthy()
    expect(screen.getByText('No open positions.')).toBeTruthy()
    expect(screen.getByText(/No history yet/)).toBeTruthy()
  })
})

describe('words from the data', () => {
  it('writes the summary sentence', () => {
    const base = homeFixture
    expect(summaryParts(base).needs).toBe('2 items need you.')
    const behind = { ...base, summary: { ...base.summary, gap_pts: -1.26, needs_you: 1 } }
    expect(summaryParts(behind)).toEqual({
      trading: 'Trading is behind your index money by 1.3 pts this year.', needs: 'One item needs you.',
    })
    expect(summaryParts({ ...base, summary: { ...base.summary, gap_pts: null, needs_you: 0 } }))
      .toEqual({ trading: null, needs: 'Nothing needs you.' })
  })

  it('writes the verdict with its sample-size caveat', () => {
    const v = verdict(homeFixture.comparison)
    expect(v?.headline).toMatch(/^Trading is ahead by 2\.9 pts this year, with a shallower worst drop/)
    expect(v?.caveat).toBe('34 real trades so far — early evidence. The strategy is reviewed at 50.')
    expect(verdict({ ...homeFixture.comparison, gap_pts: null })).toBeNull()
  })
})
