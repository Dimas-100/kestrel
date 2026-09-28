import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReservesView } from '../../lib/api'
import { renderApp, reservesFixture } from '../../test/renderApp'

describe('Reserves', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders the cash and debt tables', async () => {
    renderApp('/reserves')
    const cash = await screen.findByRole('region', { name: 'Cash' })
    expect(within(cash).getByText('High-yield savings')).toBeTruthy()
    expect(within(cash).getByText('$24,242.85')).toBeTruthy()
    const debt = screen.getByRole('region', { name: 'Debt' })
    expect(within(debt).getByText('Credit card')).toBeTruthy()
    expect(within(debt).getByText('12.8%')).toBeTruthy()
  })

  it('shows the spread sentence with both rates and a yearly figure', async () => {
    renderApp('/reserves')
    const summary = await screen.findByRole('region', { name: 'Cash and debt' })
    expect(summary.textContent).toContain('The highest rate you pay is 24.9%')
    expect(summary.textContent).toContain('the best rate you earn is 4.1%')
    expect(summary.textContent).toContain('$834.60 a year in your favor')
  })

  it('shows a credit balance as text, not a negative dollar amount', async () => {
    const v: ReservesView = { ...reservesFixture,
      debts: [{ ...reservesFixture.debts[0], owed: -50 }] }
    renderApp('/reserves', { reserves: v })
    const debt = await screen.findByRole('region', { name: 'Debt' })
    expect(within(debt).getByText('$50.00 credit balance')).toBeTruthy()
    expect(within(debt).queryByText('-$50.00')).toBeNull()
  })

  it('words a negative totals.owed the same way DebtPanel words a credit balance', async () => {
    // a lone credit-balance card: the signed total is negative too, and must read the same way as the per-line
    // wording ("$50.00 credit balance"), never a bare negative dollar figure
    const v: ReservesView = { ...reservesFixture,
      debts: [{ ...reservesFixture.debts[0], owed: -50, utilization_pct: 0 }],
      totals: { ...reservesFixture.totals, owed: -50, net: reservesFixture.totals.cash + 50 } }
    renderApp('/reserves', { reserves: v })
    const summary = await screen.findByRole('region', { name: 'Cash and debt' })
    expect(within(summary).getByText('$50.00 credit balance')).toBeTruthy()
    expect(within(summary).queryByText('−$50.00')).toBeNull()
  })

  it('leaves no spread sentence without a rated debt balance', async () => {
    const v: ReservesView = { ...reservesFixture, debts: [], spread: null }
    renderApp('/reserves', { reserves: v })
    const summary = await screen.findByRole('region', { name: 'Cash and debt' })
    expect(summary.textContent).not.toContain('highest rate')
  })

  it('names a feed with cash or debt accounts in the empty state', async () => {
    const empty: ReservesView = { as_of: reservesFixture.as_of, cash: [], debts: [],
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
})
