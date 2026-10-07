import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { StrategyView } from '../../lib/api'
import { renderApp, strategyFixture } from '../../test/renderApp'

// a title lookup, not a role query over the whole app: role queries dominate these tests' time
const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const paper: StrategyView = { ...strategyFixture, book: 'paper', primary: 'rsi2-paper' }
const withView = (view: StrategyView, book: 'real' | 'paper' = 'real') => ({ strategy: [{ id: view.id, book, view }] })

describe('Strategy page', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the strategy, its books and its backtest', async () => {
    renderApp('/strategies/rsi2')
    expect(await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })).toBeTruthy()
    expect(screen.getByText('Strategy')).toBeTruthy()
    expect(screen.getByText(strategyFixture.summary)).toBeTruthy()
    expect(screen.getByText('Real · running · 4 open')).toBeTruthy()
    expect(screen.getByText('Paper · running · 5 open')).toBeTruthy()
    expect(screen.getByText('Backtest 2006–2020')).toBeTruthy()
    const toggle = screen.getByRole('group', { name: 'Book' })
    expect(within(toggle).getByRole('button', { name: 'Real' }).getAttribute('aria-pressed')).toBe('true')
    // keeps ONE role assertion so the named-region contract stays tested
    expect(screen.getByRole('region', { name: 'How it trades' })).toBeTruthy()
  })

  it('switches to the paper book and keeps the choice in the address', async () => {
    const { router } = renderApp('/strategies/rsi2', {
      strategy: [{ id: 'rsi2', book: 'real', view: strategyFixture }, { id: 'rsi2', book: 'paper', view: paper }],
    })
    await screen.findByText('Real book against the backtest · 34 closed trades')
    fireEvent.click(within(screen.getByRole('group', { name: 'Book' })).getByRole('button', { name: 'Paper' }))
    expect(await screen.findByText('Paper book against the backtest · 34 closed trades')).toBeTruthy()
    expect(router.state.location.search).toEqual({ book: 'paper' })
  })

  it('opens on the book the address names', async () => {
    renderApp('/strategies/rsi2?book=paper', withView(paper, 'paper'))
    expect(await screen.findByText('Paper book against the backtest · 34 closed trades')).toBeTruthy()
  })

  it('offers no toggle when the strategy has one kind of money', async () => {
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, toggle: false }))
    await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })
    expect(screen.queryByRole('group', { name: 'Book' })).toBeNull()
  })

  it('shows an unknown strategy as not found, inside the shell', async () => {
    const answer = () => Promise.resolve(new Response('{"detail":"no such strategy: nope"}', { status: 404 }))
    renderApp('/strategies/nope', {}, answer)
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
    const crumb = within(screen.getByRole('navigation', { name: 'Breadcrumb' })).getByRole('link', { name: 'Strategies' })
    expect(crumb.getAttribute('href')).toBe('/strategies')
  })

  it('says it is loading, and says so plainly when the strategy could not load', async () => {
    const { unmount } = renderApp('/strategies/rsi2', { strategy: [] }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the strategy…')).toBeTruthy()
    unmount()
    renderApp('/strategies/rsi2', { strategy: [] })
    expect((await screen.findByRole('alert')).textContent)
      .toBe('This strategy couldn’t load: network is off in tests')
  })

  it('draws the rule as numbered steps with its parameters and the sizing', async () => {
    renderApp('/strategies/rsi2')
    const how = await findPanel('How it trades')
    expect(within(how).getByText('The whole rule, in four steps · 4 gates')).toBeTruthy()
    const steps = within(within(how).getAllByRole('list')[0]).getAllByRole('listitem')
    expect(steps).toHaveLength(4)
    expect(steps[0].textContent).toContain('01')
    expect(steps[2].textContent).toContain('A stop rests at the broker')
    expect(within(how).getByText('−8% stop')).toBeTruthy()
    expect(how.textContent).toContain('SizingEach position is the account value ÷ 6, at most 5 open.')
  })

  it('says so when a strategy has not described its rules', async () => {
    const rules = { ...strategyFixture.rules, steps: [], gates: [], sizing: '', version: '', history: [] }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, steps: [], sizing: '', rules }))
    const how = await findPanel('How it trades')
    expect(within(how).getByText('This strategy hasn’t described its rules.')).toBeTruthy()
  })

  it('shows where trades landed, as a chart or a table', async () => {
    renderApp('/strategies/rsi2')
    const behaving = await findPanel('Is it behaving?')
    expect(within(behaving).getByText('Where each real trade landed, against the spread of outcomes in the backtest'))
      .toBeTruthy()
    expect(within(behaving).getByText('Real trades (34)')).toBeTruthy()
    expect(within(behaving).getByText(
      'Return per trade, in 1-point buckets. Bars show the share of trades in each bucket.')).toBeTruthy()
    expect(within(behaving).getByRole('img', { name: 'Real trade returns against the backtest' })).toBeTruthy()
    fireEvent.click(within(behaving).getByRole('button', { name: 'Table' }))
    expect(within(behaving).getAllByRole('row')).toHaveLength(21)
  })

  it('scores the book against the backtest, in words as well as marks', async () => {
    renderApp('/strategies/rsi2')
    const card = await findPanel('Scorecard')
    const rows = within(card).getAllByRole('row').slice(1)
    // every verdict carries its count and the band it was judged against
    expect(rows.map((r) => r.textContent)).toEqual([
      'Win rateband 50.1% to 81.9%64.7%66.0%34within the band on 34 trades',
      'Average per tradeband −0.17% to +1.85%+0.79%+0.84%34within the band on 34 trades',
      'Average winband +1.23% to +3.68%+2.59%+2.45%22within the band on 22 trades',
      'Average lossband −3.42% to −1.14%−2.51%−2.28%12within the band on 12 trades',
      'Trades per monthband 1.6 to 4.72.83.134within the band on 34 trades',
    ])
    expect(within(card).getByText('Real book against the backtest · 34 closed trades')).toBeTruthy()
    expect(within(card).getByText('34 real trades so far — enough to read a pattern')).toBeTruthy()
    expect(card.textContent).toContain('Paper, same rules: 71 trades · +0.83% · 69.0% wins')
  })

  it('flags a measure off its band and waits for enough trades', async () => {
    const scorecard = strategyFixture.behaving.scorecard.map((r, i) => ({
      ...r, status: (['above', 'below', 'early', 'ok', 'ok'] as const)[i],
    }))
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, behaving: { ...strategyFixture.behaving, scorecard } }))
    const card = await findPanel('Scorecard')
    expect(within(card).getByText('above the band on 34 trades')).toBeTruthy()
    expect(within(card).getByText('below the band on 34 trades')).toBeTruthy()
    expect(within(card).getByText('too early · 22')).toBeTruthy()
  })

  it('shows the figures alone when there is no backtest', async () => {
    const scorecard = strategyFixture.behaving.scorecard.map((r) => ({ ...r, expected: null, status: 'none' as const }))
    renderApp('/strategies/rsi2', withView({
      ...strategyFixture, expected: null, behaving: { ...strategyFixture.behaving, scorecard },
      funnel: { ...strategyFixture.funnel, expected: null },
    }))
    const card = await findPanel('Scorecard')
    expect(within(card).getByText('No backtest to compare with.')).toBeTruthy()
    expect(within(panel('Average per trade, as trades add up')).getByText('The running average of every closed trade'))
      .toBeTruthy()
    expect(within(card).getByText('Real book · 34 closed trades')).toBeTruthy()
    expect(screen.queryByText('Backtest 2006–2020')).toBeNull()
  })

  it('draws the running average of both books inside the expected range', async () => {
    renderApp('/strategies/rsi2')
    const funnel = await findPanel('Average per trade, as trades add up')
    expect(within(funnel).getByText('If the edge is real, the line settles inside the funnel')).toBeTruthy()
    expect(within(funnel).getByText('Expected range (95%)')).toBeTruthy()
    expect(within(funnel).getByText('Real +0.79%')).toBeTruthy()
    expect(within(funnel).getByText('Paper +0.83%')).toBeTruthy()
    expect(within(funnel).getByText('trade number')).toBeTruthy()
    fireEvent.click(within(funnel).getByRole('button', { name: 'Table' }))
    expect(within(funnel).getAllByRole('row')).toHaveLength(72) // a header and 71 trades
  })

  it('shows the slots in use, the money working and the names close to a signal', async () => {
    renderApp('/strategies/rsi2')
    const slots = await findPanel('Where the money works')
    expect(within(slots).getByText('Real book · slots in use, last 40 sessions · 5 slots')).toBeTruthy()
    expect(slots.textContent).toContain('Slots in use0.7 of 5 on average · 15%')
    expect(slots.textContent).toContain('Money deployed$12,004 · 65% of $18,468') // slots are not dollars
    expect(slots.textContent).toContain('Idle sessions17 of 40')
    expect(within(slots).getByText(/^Slots are not dollars/)).toBeTruthy()
    expect(slots.textContent).toContain('Close to a signalKORSI(2) 12.4ABTRSI(2) 16.8UNPRSI(2) 19.1')
  })

  it('says so when a book does not report slots, and hides an empty watch list', async () => {
    const slots = { ...strategyFixture.slots, total: null, days: [], used: [], watch: [] }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, slots }))
    const region = await findPanel('Where the money works')
    expect(within(region).getByText('This book doesn’t report slots.')).toBeTruthy()
    expect(within(region).queryByText('Close to a signal')).toBeNull()
  })

  it('handles a strategy with no books yet', async () => {
    const empty: StrategyView = {
      ...strategyFixture, books: [], book: null, primary: null, toggle: false,
      behaving: { ...strategyFixture.behaving, trades: 0, other: null,
        buckets: strategyFixture.behaving.buckets.map((b) => ({ ...b, count: 0, share: 0 })) },
      funnel: { ...strategyFixture.funnel, lines: [], lo: [], hi: [] },
      slots: { ...strategyFixture.slots, book_id: null, total: null, days: [], used: [] },
      performance: { ...strategyFixture.performance, book_id: null, unavailable: ['No book trades this strategy yet.'] },
      cycle: { ...strategyFixture.cycle, book_id: null, rows: [], counts: [], runs: [], reported: false },
    }
    renderApp('/strategies/rsi2', withView(empty))
    await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })
    expect(within(panel('How the money is doing')).getByText('No book trades this strategy yet.')).toBeTruthy()
    expect(within(panel('Last decision cycle')).getByText('No book trades this strategy yet.')).toBeTruthy()
    expect(within(panel('Average per trade, as trades add up')).getByText('No closed trades yet.')).toBeTruthy()
    expect(within(panel('Where the money works')).getByText('No book trades this strategy yet.')).toBeTruthy()
    expect(within(panel('Is it behaving?')).getByText('No book trades this strategy yet.')).toBeTruthy()
    expect(within(panel('Scorecard')).getByText('No book trades this strategy yet.')).toBeTruthy()
    expect(within(panel('Month by month')).getByText('No book trades this strategy yet.')).toBeTruthy()
  })

  it('lays out every step a strategy describes, not only the first four', async () => {
    const extra = { label: 'Extra', title: 'Extra step', text: 'One more.', params: [], kind: 'step' as const }
    const rules = { ...strategyFixture.rules, steps: [...strategyFixture.rules.steps, extra] }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, rules }))
    const how = await findPanel('How it trades')
    expect(within(how).getByText('The whole rule, in five steps · 4 gates')).toBeTruthy()
    expect(within(within(how).getAllByRole('list')[0]).getAllByRole('listitem')).toHaveLength(5)
  })
})
