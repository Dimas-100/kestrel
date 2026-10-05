import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReservesView, Runway } from '../../lib/api'
import { money, num } from '../../lib/format'
import { renderApp, reservesFixture } from '../../test/renderApp'

const tableRows = (region: HTMLElement) => [...region.querySelectorAll('tbody tr')].map((r) => r.textContent ?? '')

describe('Reserves', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the summary the view wrote and the runway as the hero, with its ruler and band', async () => {
    renderApp('/reserves')
    const title = await screen.findByRole('heading', { level: 1, name: 'Reserves' })
    expect(title.closest('header')?.textContent).toContain(reservesFixture.summary)
    const r = reservesFixture.runway as Runway
    const runway = screen.getByRole('region', { name: 'Runway' })
    expect(runway.textContent).toContain(`${num(r.months, 1)} months`)
    expect(runway.textContent).toContain(`these ${r.days} days`)
    expect(runway.textContent).toContain(`${money(r.monthly_out)} a month`)
    expect(within(runway).getByRole('img', { name: `Runway: ${num(r.months, 1)} months; aim 6, band from 4` })).toBeTruthy()
    expect(runway.textContent).toContain(`${money(reservesFixture.totals.cash)} across 2 accounts`)
  })

  it('says so when there are no bank rows to measure the pace, and keeps the cash total', async () => {
    renderApp('/reserves', { reserves: { ...reservesFixture, runway: null, summary: '$30,255.98 in cash after debts.' } })
    const runway = await screen.findByRole('region', { name: 'Runway' })
    expect(runway.textContent).toContain('No bank transactions yet to measure the pace.')
    expect(runway.textContent).toContain(money(reservesFixture.totals.cash))
    expect(within(runway).queryByRole('img')).toBeNull()
  })

  it('draws money in and out as a pair of bars per month, with a table of every month', async () => {
    renderApp('/reserves')
    const flows = await screen.findByRole('region', { name: 'Money in and out' })
    expect(within(flows).getByRole('img', { name: 'Money in and out by month' })).toBeTruthy()
    fireEvent.click(within(flows).getByRole('button', { name: 'Table' }))
    const rows = tableRows(flows)
    expect(rows).toHaveLength(reservesFixture.flows.length)
    const last = reservesFixture.flows[reservesFixture.flows.length - 1]
    expect(rows[rows.length - 1]).toContain(money(last.money_in))
    expect(rows[rows.length - 1]).toContain(money(last.money_out))
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
    renderApp('/reserves', { reserves: { ...reservesFixture, cash: [{ ...savings, as_of: '2026-08-04' }] } })
    expect((await screen.findAllByText(/balance from 4 Aug/)).length).toBeGreaterThan(0)
  })

  it('Debt: the utilization as a bar, the word high from thirty percent, and a year of interest', async () => {
    const { unmount } = renderApp('/reserves')
    const debt = await screen.findByRole('region', { name: 'Debt' })
    expect(within(debt).getByText('Credit card')).toBeTruthy()
    expect(within(debt).getByText('12.8%')).toBeTruthy()
    expect(within(debt).getByRole('img', { name: 'Credit card: 12.8% of its limit' })).toBeTruthy()
    expect(debt.textContent).toContain('about $159.36 a year in interest')
    expect(debt.textContent).not.toContain('high')
    // 480, not 520 (screenshot pass, 2026-09-28): a floor taller than this panel's own ~510px content width at
    // 1440px forces a needless horizontal scroll on desktop
    expect((within(debt).getByRole('table') as HTMLTableElement).style.minWidth).toBe('480px')
    unmount()
    const card = reservesFixture.debts[0]
    renderApp('/reserves', { reserves: { ...reservesFixture, debts: [{ ...card, owed: 2250, utilization_pct: 45 }] } })
    const again = await screen.findByRole('region', { name: 'Debt' })
    expect(again.textContent).toContain('high')
  })

  it('shows a year of interest owed and earned apart, never netted, and what paying from cash would save', async () => {
    const { unmount } = renderApp('/reserves')
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(summary.textContent).toContain('The highest rate you pay is 24.9%, on Credit card')
    expect(summary.textContent).toContain('the best rate you earn is 4.1%')
    expect(summary.textContent).toContain('At today’s balances, a year of interest costs about $159.36 on what you owe '
      + 'and earns about $993.96 on your cash.')
    // 640.00 x (24.9 - 4.1)%, worked out by the view
    expect(summary.textContent).toContain('Paying $640.00 of the Credit card from cash would save about $133.12 a year.')
    expect(summary.textContent).not.toMatch(/in your favor|closing that gap/)
    unmount()
    const noPayDown: ReservesView = { ...reservesFixture,
      spread: { ...reservesFixture.spread!, pay_down: null, pay_down_saves: null } }
    renderApp('/reserves', { reserves: noPayDown })
    const again = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(again.textContent).toContain('a year of interest costs about $159.36')
    expect(again.textContent).not.toContain('Paying')
  })

  it('shows a credit balance as text, not a negative dollar amount', async () => {
    const v: ReservesView = { ...reservesFixture,
      debts: [{ ...reservesFixture.debts[0], owed: -50, yearly_cost: null }] }
    renderApp('/reserves', { reserves: v })
    const debt = await screen.findByRole('region', { name: 'Debt' })
    expect(within(debt).getByText('$50.00 credit balance')).toBeTruthy()
    expect(within(debt).queryByText('-$50.00')).toBeNull()
  })

  it('words a negative totals.owed the same way the Debt panel words a credit balance', async () => {
    const v: ReservesView = { ...reservesFixture,
      debts: [{ ...reservesFixture.debts[0], owed: -50, utilization_pct: 0, yearly_cost: null }],
      totals: { ...reservesFixture.totals, owed: -50, net: reservesFixture.totals.cash + 50 } }
    renderApp('/reserves', { reserves: v })
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(within(summary).getByText('$50.00 credit balance')).toBeTruthy()
    expect(within(summary).queryByText('−$50.00')).toBeNull()
  })

  it('leaves no spread sentence without a rated debt balance', async () => {
    const v: ReservesView = { ...reservesFixture, debts: [], spread: null }
    renderApp('/reserves', { reserves: v })
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    expect(summary.textContent).not.toContain('highest rate')
  })

  it('names a feed with cash or debt accounts in the empty state', async () => {
    const empty: ReservesView = { as_of: reservesFixture.as_of, summary: '', runway: null, flows: [], cash: [], debts: [],
      totals: { cash: 0, owed: 0, net: 0, utilization_pct: null }, spread: null }
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

  it('lets you try paying the dearest card from cash, and says what it saves and leaves', async () => {
    renderApp('/reserves')
    const summary = await screen.findByRole('region', { name: 'Earning against owing' })
    const slider = within(summary).getByRole('slider', { name: 'Pay this much of the Credit card from cash' }) as HTMLInputElement
    expect(Number(slider.value)).toBe(640)
    expect(slider.max).toBe('640')
    fireEvent.change(slider, { target: { value: '320' } })
    expect(summary.textContent).toContain('Paying $320.00 saves about $66.56 a year and leaves $30,575.98 in cash.')
  })
})
