// The Strategy page's trade-level sections: anatomy, recent trades, is it worth it, month by month, all trades.
import { fireEvent, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Attention, StrategyView } from '../../lib/api'
import { homeFixture, renderApp, strategyFixture } from '../../test/renderApp'
import { reasonWord, selectedChartKey, sessionsText } from './Anatomy'

// a title lookup, not a role query over the whole app: role queries dominate these tests' time
const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const withView = (view: StrategyView) => ({ strategy: [{ id: view.id, book: 'real' as const, view }] })
const rows = (region: HTMLElement) => [...region.querySelectorAll('tbody tr')] as HTMLElement[]

describe('Strategy page, trade by trade', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('opens the newest charted trade in the anatomy chart', async () => {
    renderApp('/strategies/rsi2')
    const anatomy = await findPanel('Trade anatomy')
    expect(within(anatomy).getByText('HON · real · bought Thu 10 Sep, sold Fri 18 Sep · stop')).toBeTruthy()
    expect(anatomy.textContent).toContain('−8.01%')
    expect(within(anatomy).getByText('−1.00 R')).toBeTruthy()
    expect(within(anatomy).getByText('6 sessions')).toBeTruthy()
    expect([sessionsText(0), sessionsText(1), reasonWord('signal'), reasonWord('')]).toEqual(
      ['Same day', '1 session', 'Signal', '—'])
    expect(within(anatomy).getByRole('img', { name: 'HON daily bars with the buy, the sell and the stop' })).toBeTruthy()
    expect(within(anatomy).getByText(/^Stop .* · −8%$/)).toBeTruthy()
    fireEvent.click(within(anatomy).getByRole('button', { name: 'Table' }))
    expect(within(anatomy).getAllByRole('row')).toHaveLength(31) // a header and 30 sessions
  })

  it('picks another recent trade for the chart', async () => {
    renderApp('/strategies/rsi2')
    const recent = await findPanel('Recent trades')
    const buttons = within(recent).getAllByRole('button')
    expect(buttons).toHaveLength(8)
    expect(buttons[0].getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(within(recent).getByRole('button', { name: 'TXN, closed Thu 3 Sep, Signal, +3.5%' }))
    expect(within(recent).getByRole('button', { name: 'TXN, closed Thu 3 Sep, Signal, +3.5%' }).getAttribute('aria-pressed'))
      .toBe('true')
    const anatomy = panel('Trade anatomy')
    expect(within(anatomy).getByText('TXN · real · bought Fri 28 Aug, sold Thu 3 Sep · signal')).toBeTruthy()
    expect(within(recent).getByRole('link', { name: 'All 34' }).getAttribute('href')).toBe('#trades-title')
  })

  it('lists a trade without a chart plainly, and says so when none has one', async () => {
    const anatomy = strategyFixture.anatomy
    const one = {
      ...anatomy, recent: anatomy.recent.map((r, i) => (i === 1 ? { ...r, chart: false } : r)),
      charts: anatomy.charts.filter((c) => c.key !== anatomy.recent[1].key),
    }
    const { unmount } = renderApp('/strategies/rsi2', withView({ ...strategyFixture, anatomy: one }))
    const recent = await findPanel('Recent trades')
    expect(within(recent).getAllByRole('button')).toHaveLength(7)
    expect(within(recent).getByText('no chart')).toBeTruthy()
    unmount()
    const none = { ...anatomy, recent: anatomy.recent.map((r) => ({ ...r, chart: false })), charts: [], selected: null }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, anatomy: none }))
    const region = await findPanel('Trade anatomy')
    expect(within(region).getByText('No chart for these trades.')).toBeTruthy()
  })

  it('plots yearly return against worst drop, labelled, with a table', async () => {
    renderApp('/strategies/rsi2')
    const worth = await findPanel('Is it worth it?')
    // every live point is measured over the book's own window, and the subtitle says so
    expect(within(worth).getByText('Yearly return against the worst drop along the way · every live point measured over '
      + '25 Sep to 25 Sep; the backtest over its own window')).toBeTruthy()
    for (const text of ['Backtest', 'Real book', 'Long-term accounts', 'S&P 500', '+23.4%/yr · 2006–2020',
      '+19.0%/yr · 12 months']) {
      expect(within(worth).getByText(text)).toBeTruthy()
    }
    fireEvent.click(within(worth).getByRole('button', { name: 'Table' }))
    expect(rows(worth).map((r) => r.textContent)).toEqual([
      'Backtest+23.4%−11.7%2006–2020', 'Real book+19.0%−5.6%12 months', 'Long-term accounts+21.4%−9.0%12 months',
      'S&P 500+20.5%−11.5%12 months',
    ])
  })

  it('marks a book with under a year of history as early, and says why live points are missing', async () => {
    const points = strategyFixture.worth.points.map((p) => (p.key === 'book' ? { ...p, early: true, period: '7 months' } : p))
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, worth: { ...strategyFixture.worth, points } }))
    const worth = await findPanel('Is it worth it?')
    expect(within(worth).getByText('+19.0%/yr · 7 months · early')).toBeTruthy()
    const note = 'The real book sends no value history, so there is nothing to measure yet.'
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, worth: { points: points.slice(0, 1), window: '', note } }))
    await waitFor(() => expect(document.body.textContent).toContain(note))
  })

  it('sums up month by month against the long-term accounts over the same dates, partial months starred', async () => {
    renderApp('/strategies/rsi2')
    const monthly = await findPanel('Month by month')
    expect(within(monthly).getByText('Real book against your long-term accounts over the same dates · 1 partial month (*)'))
      .toBeTruthy()
    expect(monthly.textContent).toContain('Sep* partial') // the star, and its hidden word
    expect(monthly.textContent).toContain('Months ahead of long-term7 of 12')
    expect(monthly.textContent).toContain('Best month · Jan▲ up +6.9%')
    expect(monthly.textContent).toContain('Worst month · Apr▼ down −2.1%')
    fireEvent.click(within(monthly).getByRole('button', { name: 'Table' }))
    expect(rows(monthly)).toHaveLength(12)
  })

  it('lists every closed trade, newest first, and sorts by return or P/L', async () => {
    renderApp('/strategies/rsi2')
    const all = await findPanel('All trades')
    expect(within(all).getByText('Real book · 34 closed trades · hand-placed and system-placed together')).toBeTruthy()
    expect(rows(all)).toHaveLength(34)
    // the newest trade: placed by the system both ways under v2.0, not scored yet
    expect(rows(all)[0].textContent).toBe('HONreal10 Sep18 Sep8▼ down −8.01%−1.00▼ down −$225.72Stopsystemsystemv2.0—not scored')
    const scored = rows(all).map((r) => r.textContent ?? '')
    expect(scored.filter((t) => t.endsWith('followed the plan'))).toHaveLength(29)
    expect(scored.filter((t) => t.includes('off-plan'))).toHaveLength(4)
    expect(scored.filter((t) => t.includes('handhandv1.0'))).toHaveLength(27) // the hand-run weeks, kept on the book
    const closed = within(all).getByRole('columnheader', { name: 'Closed' })
    expect(closed.getAttribute('aria-sort')).toBe('descending')
    fireEvent.click(within(all).getByRole('button', { name: 'Return' }))
    expect(rows(all)[0].textContent).toContain('HD')
    expect(within(all).getByRole('columnheader', { name: 'Return' }).getAttribute('aria-sort')).toBe('descending')
    fireEvent.click(within(all).getByRole('button', { name: 'Return' }))
    expect(rows(all)[0].textContent).toContain('−8.09%')
    fireEvent.click(within(all).getByRole('button', { name: 'P/L' }))
    expect(rows(all)[0].textContent).toContain('+$111.45')
  })

  it('says so when the book has no closed trades', async () => {
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, trades: [] }))
    const all = await findPanel('All trades')
    expect(within(all).getByText('No closed trades yet.')).toBeTruthy()
  })

  it('falls back to the view’s own pick once a refetch drops the current selection’s chart', () => {
    const charts = [{ key: 'a' }, { key: 'b' }]
    expect(selectedChartKey(charts, 'b', 'a')).toBe('b') // still charted: keep it
    expect(selectedChartKey(charts, 'c', 'a')).toBe('a') // gone: fall back to the view's pick
    expect(selectedChartKey([], 'a', null)).toBe(null) // nothing charted at all
  })

  it('links a book below its band on Home to its strategy', async () => {
    // a realistic mix (a serious item ahead of it), not isolated to a single item: the panel only renders its
    // first few, so the item under test must sit inside that visible window
    const serious: Attention = { level: 'serious', title: 'XLF has no resting stop', detail: '', link: '/books' }
    const below = homeFixture.attention.find((a) => a.title.includes('below its expected band'))!
    renderApp('/', { home: { ...homeFixture, attention: [serious, below] } })
    const needs = await findPanel('Needs you')
    const item = within(needs).getAllByRole('listitem').find((li) => li.textContent?.includes('below its expected band'))
    expect(item && within(item).getByRole('link', { name: 'Open' }).getAttribute('href')).toBe('/strategies/leader')
  })
})
