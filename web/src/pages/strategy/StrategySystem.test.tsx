// The sections added 2026-10-07: what needs you, the next review, how the money is doing, how it trades (with its
// gates), the last decision cycle, adherence, and what the expectation rests on.
import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Attention, StrategyView } from '../../lib/api'
import { renderApp, strategyFixture } from '../../test/renderApp'
import { attentionCounts } from './AttentionPanel'
import { countsText } from './CyclePanel'
import { followedText } from './AdherencePanel'
import { rulesSubtitle } from './HowItTrades'
import { stopsText } from './PerformancePanel'
import { reviewLine } from './ReviewPanel'

const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const rows = (region: HTMLElement) => within(region).getAllByRole('row').slice(1)
const withView = (view: StrategyView) => ({ strategy: [{ id: view.id, book: 'real' as const, view }] })

describe('Strategy page: the system sections', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with what needs you on this strategy, most serious first, and counts it', async () => {
    const items: Attention[] = [
      { level: 'serious', title: 'MSFT has no resting stop', detail: 'Mean reversion · real', link: '/books/rsi2-real' },
      { level: 'warning', title: 'Evening run failed Mon 17:45', detail: 'The broker timed out', link: '/activity' },
      { level: 'note', title: '16 real trades so far — limited evidence', detail: 'Verdicts rest on a small sample',
        link: '/strategies/rsi2' },
    ]
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, attention: items }))
    const needs = await findPanel('Needs you')
    const listed = within(needs).getAllByRole('listitem')
    expect(listed.map((li) => li.textContent)).toEqual([
      'SeriousMSFT has no resting stopMean reversion · realOpen',
      'WarningEvening run failed Mon 17:45The broker timed outOpen',
      'Note16 real trades so far — limited evidenceVerdicts rest on a small sample', // its own page: no link
    ])
    expect(within(needs).getByText('1 serious · 1 warning · 1 note')).toBeTruthy()
    expect(attentionCounts([items[2], items[2]])).toBe('2 notes')
    expect(attentionCounts([])).toBe('')
  })

  it('says so when nothing needs you', async () => {
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, attention: [] }))
    const needs = await findPanel('Needs you')
    expect(within(needs).getByText('Nothing needs you on this strategy.')).toBeTruthy()
  })

  it('shows the next review as progress toward a trade count and a date, with its criteria', async () => {
    renderApp('/strategies/rsi2')
    const review = await findPanel('Next review')
    const r = strategyFixture.review!
    expect(within(review).getByText(`System review · ${r.doc}`)).toBeTruthy()
    expect(within(review).getByText(reviewLine(r))).toBeTruthy()
    expect(reviewLine(r)).toMatch(/^2 of 20 trades since \d+ \w+ · by \d+ \w+ \(\d+ days\)$/)
    expect(within(review).getByRole('progressbar', { name: 'System review: trades counted' }).getAttribute('aria-valuenow'))
      .toBe('2')
    expect(within(review).getByText(r.last_note)).toBeTruthy()
    expect(rows(review).map((tr) => tr.textContent)).toEqual([
      'Plan followedScored trades since the review≥ 90%100% of 8Pass',
      'Entries placed by the systemSystem entries ÷ entries100%100%Pass',
      'ExpectancyAverage return per tradeRead against +0.84% over 30–50 trades+0.79%Reported',
      'Worst dropFrom the book\'s peakHalt everything at −15%−2.1%Pass',
    ])
    expect(within(review).getByText('3 of 3 criteria passing')).toBeTruthy()
  })

  it('words a review that is due, a date-only review, and a strategy without one', async () => {
    const due = { ...strategyFixture.review!, trades: 20, due: true }
    expect(reviewLine(due)).toMatch(/· due now$/)
    const dated = { ...strategyFixture.review!, at_trades: null, counted_since: null, by: '2026-10-30', days_left: 35 }
    expect(reviewLine(dated)).toBe('by 30 Oct (35 days)')
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, review: null }))
    const review = await findPanel('Next review')
    expect(within(review).getByText('This strategy hasn’t set a review.')).toBeTruthy()
  })

  it('shows how the money is doing on a named capital basis', async () => {
    renderApp('/strategies/rsi2')
    const p = await findPanel('How the money is doing')
    expect(within(p).getByText('Real book · P&L is gross of fees; the return takes deposits out')).toBeTruthy()
    expect(p.textContent).toContain('Realized P&L▲ up +$741.20closed trades')
    expect(p.textContent).toContain('Unrealized P&L▲ up +$86.204 open positions at the last price')
    expect(p.textContent).toContain('Total P&L▲ up +$827.40')
    expect(p.textContent).toContain('Return since start▲ up +19.0%The trading account\'s value; deposits are taken out of the return · since 25 Sep')
    expect(p.textContent).toContain('Deployed$12,004 · 65%of $18,468 capital')
    expect(p.textContent).toContain('Stop coverage4 of 4 covered')
    expect(p.textContent).toContain('Drawdown now−3.8%')
    expect(p.textContent).toContain('Worst drawdown−5.6%over 365 days of history')
  })

  it('says what it cannot measure and why', async () => {
    const perf = {
      ...strategyFixture.performance, return_pct: null, drawdown_now_pct: null, drawdown_worst_pct: null, since: null,
      days: null, unavailable: ['The real book sends no value history, so its drawdown and its return since the start can\'t be measured; the P&L above is what the trades and positions add up to.'],
    }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, performance: perf }))
    const p = await findPanel('How the money is doing')
    expect(within(p).getByText(perf.unavailable[0])).toBeTruthy()
    expect(p.textContent).toContain('Drawdown now—')
    expect(stopsText({ ...perf, money: 'paper' })).toBe('paper: the runner holds them')
    expect(stopsText({ ...perf, stops_total: 0, stops_covered: 0 })).toBe('no open positions')
  })

  it('draws the rule as steps, then its gates and limits, then the sizing and the rules version', async () => {
    renderApp('/strategies/rsi2')
    const how = await findPanel('How it trades')
    expect(within(how).getByText('The whole rule, in four steps · 4 gates')).toBeTruthy()
    const steps = within(how).getAllByRole('list')[0]
    expect(within(steps).getAllByRole('listitem')).toHaveLength(4)
    expect(within(how).getByText('Gates and limits')).toBeTruthy()
    expect(within(how).getByText('No new entries risk-off')).toBeTruthy()
    expect(within(how).getByText('SPY < 200-day')).toBeTruthy()
    expect(how.textContent).toContain('SizingEach position is the account value ÷ 6, at most 5 open.')
    expect(how.textContent).toMatch(/Rules v2\.1 · since \d+ \w+ · 3 versions/)
    expect(rulesSubtitle([], [])).toBeUndefined()
    expect(rulesSubtitle([], strategyFixture.rules.gates)).toBe('No flow described · 4 gates')
    expect(screen.getAllByText(/^Rules v2\.1 · since/).length).toBe(2) // the header chip and the panel's line
  })

  it('shows the last decision cycle: signals, what the gate refused and why, placements, fills and expiries', async () => {
    renderApp('/strategies/rsi2')
    const cycle = await findPanel('Last decision cycle')
    expect(within(cycle).getByText(/^Ended 25 Sep · prices as of 25 Sep \(fresh\)$/)).toBeTruthy()
    expect(within(cycle).getByText(countsText(strategyFixture.cycle))).toBeTruthy()
    expect(countsText(strategyFixture.cycle)).toBe('2 signals · 2 queued · 6 blocked · 1 placed · 1 filled · 1 expired')
    const listed = rows(cycle)
    expect(listed).toHaveLength(13)
    expect(listed[0].textContent).toContain('Signal · buyMSFTRSI(2) 6.50Closed under 10')
    const blocked = listed.find((r) => r.textContent?.includes('Caps: 5 lots already open'))
    expect(blocked?.textContent).toContain('Blocked · buyORCL')
    expect(listed.some((r) => r.textContent?.includes('Expired · buyORCL'))).toBe(true)
    fireEvent.click(within(cycle).getByRole('button', { name: 'Runs' }))
    const runs = rows(cycle)
    expect(runs.map((r) => r.textContent?.slice(0, 11))).toEqual(['Morning run', 'Evening run', 'Evening run'])
    expect(runs[2].textContent).toContain('due')
  })

  it('says so when a book does not report its decisions', async () => {
    const cycle = { ...strategyFixture.cycle, rows: [], counts: [], reported: false, prices_as_of: null, freshness: 'not reported' }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, cycle }))
    const region = await findPanel('Last decision cycle')
    expect(within(region).getByText('This book doesn’t report its decisions.')).toBeTruthy()
    expect(within(region).getByText(/prices: date not reported$/)).toBeTruthy()
  })

  it('judges adherence per rules version and lists the deviations', async () => {
    renderApp('/strategies/rsi2')
    const a = await findPanel('Did it follow the rules?')
    const listed = rows(a)
    expect(listed).toHaveLength(3)
    expect(listed[0].textContent).toContain('v1.0')
    expect(listed[0].textContent).toContain('270 / 270 / 2724 of 27 followed') // hand-run: not deviations
    expect(listed[1].textContent).toContain('v2.0 · system-run')
    expect(listed[1].textContent).toContain('77 / 06 / 15 of 6 followed · 1 not scored')
    expect(followedText(strategyFixture.adherence.rows[2])).toBe('—')
    const deviations = within(a).getByText('Deviations').parentElement as HTMLElement
    const items = within(deviations).getAllByRole('listitem').map((li) => li.textContent)
    expect(items[0]).toMatch(/^KO · \d+ \w+ → \d+ \w+ · v2\.0 · Hand exit · Scored off-plan: Sold by hand ahead of a print$/)
    expect(items.filter((t) => t?.includes('v1.0'))).toHaveLength(3)
    expect(within(a).getByText(/^Each trade is judged against the rules in force when it was entered\. Before/)).toBeTruthy()
  })

  it('says adherence cannot be judged when the source does not say who placed the trades', async () => {
    const adherence = { ...strategyFixture.adherence, reported: false, rows: [], deviations: [],
      note: 'This source doesn\'t say who placed its trades, so adherence can\'t be judged.' }
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, adherence }))
    const a = await findPanel('Did it follow the rules?')
    expect(within(a).getByText(adherence.note)).toBeTruthy()
  })

  it('says what the expectation rests on, its caveats, and the research rows behind it', async () => {
    renderApp('/strategies/rsi2')
    const r = await findPanel('What the expectation rests on')
    expect(within(r).getByText('backtest · 2006–2020')).toBeTruthy()
    const labels = [...r.querySelectorAll('dt')].map((dt) => dt.textContent)
    expect(labels).toEqual(['Stage', 'Configuration', 'Sizing', 'Costs modelled', 'Sample'])
    expect(within(r).getByText('$6,000 fixed lots, 6 slots, in a $100,000 book')).toBeTruthy()
    expect(within(r).getByText('Today\'s names tested back to 2006: survivors by construction')).toBeTruthy()
    const listed = rows(r)
    expect(listed).toHaveLength(1)
    expect(listed[0].textContent).toContain('Dip buy')
    expect(listed[0].textContent).toContain('confirmPass240+0.84%+23.4%−11.7%')
  })

  it('says so when there is no research behind a strategy', async () => {
    renderApp('/strategies/rsi2', withView({ ...strategyFixture, research: { expected: null, backtests: [] } }))
    const r = await findPanel('What the expectation rests on')
    expect(within(r).getByText('No backtest to compare with.')).toBeTruthy()
  })

  it('qualifies the scorecard with its sample and shrinks the thin charts', async () => {
    renderApp('/strategies/rsi2')
    const card = await findPanel('Scorecard')
    expect(within(card).getByText('34 real trades so far — enough to read a pattern')).toBeTruthy()
    const thin = {
      ...strategyFixture, behaving: { ...strategyFixture.behaving, trades: 16, evidence: 'limited' as const,
        evidence_text: '16 real trades so far — limited evidence; the plan judges the system over 30–50' },
    }
    renderApp('/strategies/rsi2', withView(thin))
    await waitFor(() => expect(screen.getAllByText(/16 real trades so far — limited evidence/).length).toBeGreaterThan(0))
    // a row-level verdict on a thin sample says so, in muted ink
    expect(screen.getAllByText('within the band on 34 trades, limited evidence').length).toBeGreaterThan(0)
    expect(screen.getByText('16 real trades so far — limited evidence; the plan judges the system over 30–50 — a sketch, not a verdict'))
      .toBeTruthy()
    expect(screen.getByText(/^71 trades: the funnel is still wide/)).toBeTruthy()
  })
})
