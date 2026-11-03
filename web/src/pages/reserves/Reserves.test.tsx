import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MonthFlow, Rates, ReservesView, Runway } from '../../lib/api'
import { money, num } from '../../lib/format'
import { renderApp, reservesFixture } from '../../test/renderApp'
import { partText } from './FlowsPanel'
import { cardColumns } from './DebtPanel'
import { coverFor, dayScaleEnd } from './RunwayPanel'
import { coverageChange } from './SpreadPanel'
import { balanceDays } from './StandingPanel'

const tableRows = (region: HTMLElement) => [...region.querySelectorAll('tbody tr')].map((r) => r.textContent ?? '')
const runway = reservesFixture.runway as Runway

describe('Reserves', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the summary the view wrote, then cash − recorded debt = the difference and how fresh it is', async () => {
    renderApp('/reserves')
    const title = await screen.findByRole('heading', { level: 1, name: 'Reserves' })
    expect(title.closest('header')?.textContent).toContain(reservesFixture.summary)
    const standing = screen.getByRole('region', { name: 'Where you stand' })
    const t = reservesFixture.totals
    expect(standing.textContent).toContain(`Cash${money(t.cash)}2 accounts`)
    expect(standing.textContent).toContain(`Recorded debt${money(t.owed)}1 debt on record`)
    expect(standing.textContent).toContain(`Difference${money(t.net)}cash after recorded debt`)
    expect(standing.textContent).toMatch(/minus.*equals/) // the operators are read out, not only drawn
    expect(standing.textContent).toContain('Balances from 25 Sep')
    expect(standing.className).toContain('panel-lead') // the page's main summary carries the accent wash and edge
    expect(standing.textContent).not.toContain('Over a week old')
  })

  it('names balances over a week old beside the totals, and says when debt outweighs cash', async () => {
    const savings = reservesFixture.cash[0]
    renderApp('/reserves', { reserves: { ...reservesFixture,
      cash: [{ ...savings, as_of: '2026-08-04' }, ...reservesFixture.cash.slice(1)],
      totals: { ...reservesFixture.totals, net: -312.4, oldest_as_of: '2026-08-04', stale: [savings.name] } } })
    const standing = await screen.findByRole('region', { name: 'Where you stand' })
    expect(standing.textContent).toContain(`Warning: Over a week old, so these figures may be off: ${savings.name} (balance from 4 Aug).`)
    expect(standing.textContent).toContain('more owed than held in cash')
    expect(standing.textContent).toContain('Balances from 4 Aug – 25 Sep')
    expect(balanceDays('2026-10-06', '2026-10-07')).toBe('6–7 Oct')
  })

  it('shows coverage with how it is worked out beside it: the pace, the window, the moves left out', async () => {
    renderApp('/reserves')
    const coverage = await screen.findByRole('region', { name: 'Coverage' })
    expect(coverage.textContent).toContain(`${num(runway.months, 1)}months`)
    expect(within(coverage).getByRole('img', { name: `Coverage: ${num(runway.months, 1)} months; aim 6, band from 4` })).toBeTruthy()
    // the workings sit in a disclosure, closed until asked for
    const workings = within(coverage).getByLabelText('How coverage is worked out')
    const details = workings.closest('details') as HTMLDetailsElement
    expect(details.open).toBe(false)
    expect(details.querySelector('summary')?.textContent).toBe('How it’s worked out')
    expect(workings.textContent).toContain(`${money(runway.daily_out)} a day · ${money(runway.monthly_out)} a month`)
    expect(workings.textContent).toContain(`${runway.days} days of bank rows, 1 Jul – 18 Sep`)
    expect(workings.textContent).toContain(`${money(runway.moved)} moved between your own accounts (${runway.moved_count} transfers)`)
    expect(workings.textContent).toContain('No money comes in')
    expect(coverage.textContent).not.toContain('No bank rows since')
  })

  it('reads coverage in days when it is short, and warns when the bank rows have gone quiet', async () => {
    const short: Runway = { ...runway, unit: 'days', days_cover: 4, months: 0.1, daily_out: 150, stale: true, through: '2026-09-10' }
    renderApp('/reserves', { reserves: { ...reservesFixture, runway: short } })
    const coverage = await screen.findByRole('region', { name: 'Coverage' })
    expect(coverage.textContent).toContain('4days')
    expect(coverage.textContent).toContain('At $150.00 a day, the pace of the last')
    expect(coverage.textContent).toContain('Warning: No bank rows since 10 Sep: the pace may be out of date.')
    expect(coverFor(845, short)).toEqual({ unit: 'days', days_cover: 5, months: 0.2 })
    // a two-week scale in days, not a dot at the start of a year; the plan's 6-month aim is said in words
    const scale = within(coverage).getByRole('img', { name: 'Coverage: 4 days on a scale of 14 days; aim 6 months, past the end of the scale' })
    expect(scale.textContent).toContain('today1 wk2 wk')
    expect(coverage.textContent).toContain('your cash would run out around Tue 29 Sep.')
    expect(coverage.textContent).toContain('Your plan aims for 6 months, past the end of this scale')
    expect(dayScaleEnd(4)).toBe(14)
    expect(dayScaleEnd(13)).toBe(14)
    expect(dayScaleEnd(20)).toBe(21)
    expect(dayScaleEnd(59)).toBe(63)
    expect(coverFor(-20, short).days_cover).toBe(0)
  })

  it('says so when there are no bank rows to measure the pace, and keeps the cash total', async () => {
    renderApp('/reserves', { reserves: { ...reservesFixture, runway: null, summary: '$30,255.98 in cash after recorded debts.' } })
    const coverage = await screen.findByRole('region', { name: 'Coverage' })
    expect(coverage.textContent).toContain('No bank transactions yet to measure the pace.')
    expect(coverage.textContent).toContain(money(reservesFixture.totals.cash))
    expect(within(coverage).queryByRole('img')).toBeNull()
  })

  it('draws money in and out per month with a partial month named and the net under each, and a table', async () => {
    renderApp('/reserves')
    const flows = await screen.findByRole('region', { name: 'Money in and out' })
    const last = reservesFixture.flows[reservesFixture.flows.length - 1]
    expect(last.partial).toBe(true)
    const chart = within(flows).getByRole('img', { name: /^Money in and out by month/ })
    expect(chart.getAttribute('aria-label')).toContain(`Sep 2026 (to date), in ${money(last.money_in)}`)
    expect(chart.textContent).toContain('to date')
    expect(chart.textContent).toContain('net −$87')
    const shownMoved = reservesFixture.flows.slice(-3).reduce((sum, f) => sum + f.moved, 0)
    expect(flows.textContent).toContain(`left out: ${money(shownMoved)} moved between your accounts`)
    fireEvent.click(within(flows).getByRole('button', { name: 'Table' }))
    const rows = tableRows(flows)
    expect(rows).toHaveLength(reservesFixture.flows.length)
    expect(rows[rows.length - 1]).toBe(`Sep 2026to date${last.days}${money(last.money_in)}${money(last.money_out)}−${money(-last.net)}${money(last.moved)}`)
    const first: MonthFlow = { ...last, start: '2026-07-10', end: '2026-07-31' }
    expect(partText(first)).toBe('from 10 Jul')
    expect(partText({ ...last, partial: false })).toBeNull()
    renderApp('/reserves', { reserves: { ...reservesFixture, flows: [] } })
    expect((await screen.findAllByText('No bank transactions yet.')).length).toBeGreaterThan(0)
  })

  it('Cash: each account with its share of all the cash, and a note when a balance is from a while ago', async () => {
    renderApp('/reserves')
    const cash = await screen.findByRole('region', { name: 'Cash' })
    expect(within(cash).getByText('High-yield savings')).toBeTruthy()
    expect(within(cash).getByText('$24,242.85')).toBeTruthy()
    const savings = reservesFixture.cash[0]
    expect(within(cash).getByRole('img', { name: `${savings.name}: ${num(savings.share_pct as number, 1)}% of your cash` })).toBeTruthy()
    expect(cash.textContent).not.toContain('balance from')
    // each row leads with its institution's tile, as the debt cards do (initials without a logo file)
    expect(within(cash).getAllByRole('row')[1].querySelector('td span[aria-hidden="true"]')?.textContent).toBe('BC')
    renderApp('/reserves', { reserves: { ...reservesFixture, cash: [{ ...savings, as_of: '2026-08-04' }] } })
    expect((await screen.findAllByText(/balance from 4 Aug/)).length).toBeGreaterThan(0)
  })

  it('Debt: a card per line with its balance, utilization, APR and date together', async () => {
    const { unmount } = renderApp('/reserves')
    const debt = await screen.findByRole('region', { name: 'Debt' })
    const cards = within(debt).getAllByRole('listitem')
    expect(cards).toHaveLength(1)
    const card = cards[0]
    expect(within(card).getByText('Credit card')).toBeTruthy()
    expect(card.textContent).toContain('Owed$640.00')
    expect(within(card).getByRole('img', { name: 'Credit card: 12.8% of its limit' })).toBeTruthy()
    expect(card.textContent).toContain('12.8% of a $5,000 limit')
    expect(card.textContent).toContain('24.9% APR · about $159.36 a year in interest')
    expect(card.textContent).toContain('balance from 25 Sep')
    expect(card.textContent).not.toContain('high')
    expect(debt.textContent).toContain('12.8% of limits used · largest balance first')
    // one row of cards across the page: three tracks at least so a lone card isn't stretched, four at most
    expect(cardColumns(1)).toContain('/ 3)')
    expect(cardColumns(3)).toContain('/ 3)')
    expect(cardColumns(6)).toContain('/ 4)')
    unmount()
    const line = reservesFixture.debts[0]
    renderApp('/reserves', { reserves: { ...reservesFixture,
      debts: [{ ...line, owed: 2250, utilization_pct: 45 },
        { ...line, id: 'charge', name: 'Charge card', limit: null, utilization_pct: null, rate_pct: null, yearly_cost: null,
          as_of: '2026-08-04' }],
      totals: { ...reservesFixture.totals, debt_count: 2, limited_count: 1 } } })
    const again = await screen.findByRole('region', { name: 'Debt' })
    const [high, charge] = within(again).getAllByRole('listitem')
    expect(high.textContent).toContain('high')
    expect(charge.textContent).toContain('No limit on record')
    expect(charge.textContent).toContain('APR not on record')
    expect(charge.textContent).toContain('Warning: balance from 4 Aug, over a week old')
    expect(again.textContent).toContain('over the 1 with a limit on record')
  })

  it('shows a year of interest owed and earned apart, on the part with a rate, and what paying from cash would save', async () => {
    const { unmount } = renderApp('/reserves')
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(summary.textContent).toContain('The highest rate on record is 24.9%, on Credit card')
    expect(summary.textContent).toContain('the best your cash earns on record is 4.1%')
    expect(summary.textContent).toContain('At today’s balances, a year of interest costs about $159.36 on what you owe '
      + 'and earns about $993.96 on the $24,242.85 of your cash with a rate.')
    // 640.00 x (24.9 - 4.1)%, worked out by the view
    expect(summary.textContent).not.toContain('would save about') // one place says the saving: its block
    expect(summary.textContent).not.toMatch(/in your favor|closing that gap|Warning/)
    unmount()
    const noPayDown: ReservesView = { ...reservesFixture,
      spread: { ...reservesFixture.spread!, pay_down: null, pay_down_saves: null } }
    renderApp('/reserves', { reserves: noPayDown })
    const again = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(again.textContent).toContain('a year of interest costs about $159.36')
    expect(again.textContent).not.toContain('Try paying')
  })

  it('warns first when a rate is on record for only part of what is owed, naming the lines without one', async () => {
    const partial: Rates = { ...reservesFixture.rates!, owed: 1890, rated_owed: 640, rated_owed_pct: 33.86,
      unrated: ['Store card', 'Charge card'] }
    const { unmount } = renderApp('/reserves', { reserves: { ...reservesFixture, rates: partial } })
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(summary.textContent).toContain('Warning: Rates are on record for $640.00 of the $1,890.00 you owe (33.9%). '
      + 'Store card and Charge card have none, so the interest below covers the rated part only')
    expect(summary.textContent).toContain('costs about $159.36 on the $640.00 with a rate')
    unmount()
    renderApp('/reserves', { reserves: { ...reservesFixture, spread: null,
      rates: { ...partial, rated_owed: 0, rated_owed_pct: 0, unrated: ['Store card', 'Credit card'] } } })
    const none = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(none.textContent).toContain('No APR is on record for any of the $1,890.00 you owe')
  })

  it('shows a credit balance as text, not a negative dollar amount', async () => {
    const v: ReservesView = { ...reservesFixture,
      debts: [{ ...reservesFixture.debts[0], owed: -50, yearly_cost: null }] }
    renderApp('/reserves', { reserves: v })
    const debt = await screen.findByRole('region', { name: 'Debt' })
    expect(within(debt).getByText('$50.00 credit balance')).toBeTruthy()
    expect(within(debt).queryByText('-$50.00')).toBeNull()
  })

  it('words a negative recorded debt the same way the Debt panel words a credit balance', async () => {
    const v: ReservesView = { ...reservesFixture,
      debts: [{ ...reservesFixture.debts[0], owed: -50, utilization_pct: 0, yearly_cost: null }],
      totals: { ...reservesFixture.totals, owed: -50, net: reservesFixture.totals.cash + 50 } }
    renderApp('/reserves', { reserves: v })
    const standing = await screen.findByRole('region', { name: 'Where you stand' })
    expect(within(standing).getByText('$50.00 credit balance')).toBeTruthy()
    expect(within(standing).queryByText('−$50.00')).toBeNull()
  })

  it('leaves no spread sentence without a rated debt balance', async () => {
    const v: ReservesView = { ...reservesFixture, debts: [], spread: null,
      rates: { ...reservesFixture.rates!, owed: 0, rated_owed: 0, rated_owed_pct: null, unrated: [] } }
    renderApp('/reserves', { reserves: v })
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(summary.textContent).not.toContain('highest rate')
    expect(summary.textContent).toContain('Nothing owed.')
  })

  it('names a feed with cash or debt accounts in the empty state', async () => {
    const empty: ReservesView = { as_of: reservesFixture.as_of, today: reservesFixture.today, summary: '', runway: null,
      flows: [], cash: [], debts: [], spread: null, rates: null,
      totals: { cash: 0, owed: 0, net: 0, utilization_pct: null, cash_count: 0, debt_count: 0, limited_count: 0,
        oldest_as_of: null, newest_as_of: null, stale: [] } }
    renderApp('/reserves', { reserves: empty })
    expect(await screen.findByText(/a feed with cash or debt accounts/)).toBeTruthy()
  })

  it('says it is loading, and says so plainly when reserves could not load', async () => {
    const { unmount } = renderApp('/reserves', { reserves: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading your reserves…')).toBeTruthy()
    unmount()
    renderApp('/reserves', { reserves: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Reserves couldn’t load: network is off in tests')
  })

  it('opens Reserves from the sidebar', async () => {
    renderApp('/')
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    fireEvent.click(within(nav).getByRole('link', { name: /Reserves/ }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Reserves' })).toBeTruthy()
  })

  it('lets you try paying the dearest rated card from cash, and shows before and after side by side', async () => {
    renderApp('/reserves')
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    const slider = within(summary).getByRole('slider', { name: 'Pay this much of the Credit card from cash' }) as HTMLInputElement
    expect(Number(slider.value)).toBe(640)
    expect(slider.max).toBe('640')
    fireEvent.change(slider, { target: { value: '320' } })
    const blocks = (label: string) => [...summary.querySelectorAll('.label')].find((l) => l.textContent === label)?.parentElement?.textContent
    expect(blocks('Cash')).toBe('Cashnow $30,895.98after $30,575.98$320.00 to the card')
    expect(blocks('Coverage')).toBe('Coveragenow 6.0 monthsafter 6.0 monthsno change')
    expect(blocks('Interest saved a year')).toBe('Interest saved a yearnow $0.00after $66.56net of what that cash would have earned')
    expect(coverageChange({ unit: 'days', days_cover: 4, months: 0.1 }, { unit: 'days', days_cover: 3, months: 0.1 }))
      .toBe('1 day less')
    const table = within(summary).getByRole('table', { name: 'Before and after paying $320.00 from cash' })
    expect(tableRows(table)).toEqual([
      'Cash$30,895.98$30,575.98',
      'Coverage6.0 months6.0 months',
      'Owed on the Credit card$640.00$320.00',
      // 320 x 24.9% a year less on the rated debt
      'Interest a year, rates on record$159.36$79.68',
    ])
  })

  it('stops the slider at the exact amount owed, never past it, when that is not a whole dollar', async () => {
    const card = reservesFixture.debts[0]
    renderApp('/reserves', { reserves: { ...reservesFixture, debts: [{ ...card, owed: 400.50 }],
      spread: { ...reservesFixture.spread!, yearly_cost: 99.72, pay_down: 400.50, pay_down_saves: 80.00 } } })
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    const slider = within(summary).getByRole('slider') as HTMLInputElement
    expect(slider.max).toBe('401')
    const rows = tableRows(within(summary).getByRole('table', { name: 'Before and after paying $400.50 from cash' }))
    expect(rows[2]).toBe('Owed on the Credit card$400.50$0.00')
    expect(rows[3]).toBe('Interest a year, rates on record$99.72$0.00')
  })
})
