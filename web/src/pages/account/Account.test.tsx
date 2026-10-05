import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AccountView } from '../../lib/api'
import { accountCheckingFixture, accountFixture, renderApp } from '../../test/renderApp'
import { money } from '../../lib/format'
import { flowDay } from './AccountGrowth'
import { quantityText } from './HoldingsPanel'

// a title lookup, not a role query over the whole app: role queries dominate these tests' time
const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const rows = (region: HTMLElement, part = 'tbody') => [...region.querySelectorAll(`${part} tr`)].map((r) => r.textContent)
const withView = (view: AccountView) => ({ account: [{ id: view.id, view }] })

describe('Account page', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the account, where it is, what kind it is and when', async () => {
    renderApp('/accounts/roth')
    const title = await screen.findByRole('heading', { level: 1, name: 'Roth IRA' })
    expect(title.closest('header')?.textContent).toBe('AccountRoth IRABrokerage A · Roth IRALong-termas of Fri 25 Sep')
  })

  it('gives the year of a value from before this year', async () => {
    renderApp('/accounts/roth', withView({ ...accountFixture, as_of: '2025-12-31' }))
    const title = await screen.findByRole('heading', { level: 1, name: 'Roth IRA' })
    expect(title.closest('header')?.textContent).toBe('AccountRoth IRABrokerage A · Roth IRALong-termas of 31 Dec 2025')
  })

  it('draws a year of value against the start plus deposits, as a chart or a table', async () => {
    renderApp('/accounts/roth')
    const value = await findPanel('Value')
    expect(value.textContent).toContain('$67,890.81')
    expect(within(value).getByText('1 year · the gap between the lines is the market')).toBeTruthy()
    const chart = within(value).getByRole('img', { name: 'The account’s value against its starting value plus deposits' })
    expect(chart.querySelectorAll('path[stroke-dasharray="1.5 3.5"]')).toHaveLength(1) // the dotted start + deposits
    fireEvent.click(within(value).getByRole('button', { name: 'Table' }))
    const table = rows(value)
    expect(table).toHaveLength(262)
    expect(table[0]).toBe('Fri 25 Sep$67,890.81$56,200.00—') // newest first; the deposits line ends at start + deposits
  })

  it('moves the value and the growth to another window together', async () => {
    renderApp('/accounts/roth')
    const value = await findPanel('Value')
    const growth = panel('Growth')
    expect(growth.textContent).toContain('Started at$50,200.00Sep 2025')
    fireEvent.click(within(value).getByRole('button', { name: 'This year' }))
    expect(within(growth).getByText('This year')).toBeTruthy()
    expect(growth.textContent).toContain('Started at$58,287.371 JanYou put in$4,000.00The market added▲ up +$5,603.44')
    fireEvent.click(within(value).getByRole('button', { name: 'Table' }))
    expect(rows(value)).toHaveLength(192)
  })

  it('lists the last eight times money moved in or out', async () => {
    const flows = [{ date: '2026-09-18', amount: -200 }, ...accountFixture.flows.slice(0, 7)]
    renderApp('/accounts/roth', withView({ ...accountFixture, flows }))
    const growth = await findPanel('Growth')
    const items = within(growth).getAllByRole('listitem').map((li) => li.textContent)
    expect(items).toHaveLength(8)
    expect(items.slice(0, 2)).toEqual(['Fri 18 Sep▼ out$200.00', 'Tue 1 Sep▲ in$500.00'])
    expect(flowDay('2025-11-03', '2026')).toBe('3 Nov 2025')
  })

  it('says when money moved that the records do not show yet', async () => {
    const flows = [{ date: '2026-09-24', amount: 100, unexplained: 100 }, ...accountFixture.flows.slice(0, 7)]
    renderApp('/accounts/roth', withView({ ...accountFixture, flows }))
    const growth = await findPanel('Growth')
    const [first, second] = within(growth).getAllByRole('listitem')
    expect(first.textContent).toBe('Thu 24 Sep▲ in · not posted yet$100.00')
    expect(within(first).getByText('not posted yet').getAttribute('title')).toMatch(/hasn.t posted/)
    expect(second.textContent).not.toContain('not posted yet')
  })

  it('weighs each holding with its gain, then the cash and the totals', async () => {
    renderApp('/accounts/roth')
    const holdings = await findPanel('Holdings')
    expect(rows(holdings)).toEqual([
      'SPYS&P 500 index fund63.66661.20$42,091.9962.0%$32,831.75▲ up +$9,260.24▲ up +28.21%',
      'XLVHealth care sector fund100.155142.35$14,257.0621.0%$13,259.07▲ up +$997.99▲ up +7.53%',
      'XLPConsumer staples sector fund137.32679.10$10,862.4916.0%$11,296.99▼ down −$434.50▼ down −3.85%',
      'Cash———$679.271.0%——',
    ])
    expect(rows(holdings, 'tfoot')).toEqual(['Total$67,890.81100.0%$57,387.81▲ up +$9,823.73▲ up +17.12%'])
    expect(within(holdings).getByRole('columnheader', { name: 'Value' }).getAttribute('aria-sort')).toBe('descending')
  })

  it('sorts by gain, with a holding of unknown cost last and the totals saying they leave it out', async () => {
    const holdings = accountFixture.holdings.map((h) => (h.symbol === 'XLV'
      ? { ...h, cost_basis: null, gain: null, gain_pct: null } : h))
    const totals = { ...accountFixture.totals, unknown_cost: 1 }
    renderApp('/accounts/roth', withView({ ...accountFixture, holdings, totals }))
    const panelEl = await findPanel('Holdings')
    fireEvent.click(within(panelEl).getByRole('button', { name: 'Gain' }))
    expect(rows(panelEl).map((r) => r?.slice(0, 3))).toEqual(['SPY', 'XLP', 'XLV', 'Cas'])
    fireEvent.click(within(panelEl).getByRole('button', { name: 'Gain' }))
    expect(rows(panelEl).map((r) => r?.slice(0, 3))).toEqual(['XLP', 'SPY', 'XLV', 'Cas'])
    expect(within(panelEl).getByText('The cost and gain totals leave out 1 holding with no cost basis.')).toBeTruthy()
    expect([quantityText(1200), quantityText(0.000123), quantityText(-2.5)]).toEqual(['1,200', '0.000123', '−2.5'])
  })

  it('says when the holdings were reported before the value’s day, and only then', async () => {
    const older = async (day: string | null) => {
      const { unmount } = renderApp('/accounts/roth', withView({ ...accountFixture, holdings_as_of: day }))
      const lines = [...(await findPanel('Holdings')).querySelectorAll('p')].map((p) => p.textContent)
      unmount()
      return lines.find((line) => line?.startsWith('Holdings as reported'))
    }
    expect(await older('2026-09-24')).toBe('Holdings as reported on Thu 24 Sep; the value above is from a newer day.')
    expect(await older('2025-11-03')).toBe('Holdings as reported on 3 Nov 2025; the value above is from a newer day.')
    expect(await older(null)).toBeUndefined()
    expect(await older('2026-09-25')).toBeUndefined() // the value's own day
  })

  it('prints a margin debit with a true minus, and a closed account plainly', async () => {
    const margin = { ...accountFixture, cash: -200, cash_weight: -25 }
    const { unmount } = renderApp('/accounts/roth', withView(margin))
    const holdings = await findPanel('Holdings')
    expect(rows(holdings).at(-1)).toBe('Cash———−$200.00−25.0%——')
    unmount()
    const closed: AccountView = { ...accountFixture, value: 0, points: [], flows: [], holdings: [], cash: 0,
      cash_weight: null, growth: { ytd: null, '1y': null, all: null },
      totals: { value: 0, cost_basis: null, gain: null, gain_pct: null, unknown_cost: 0 } }
    renderApp('/accounts/roth', withView(closed))
    expect(within(await findPanel('Holdings')).getByText('This account holds nothing right now.')).toBeTruthy()
    expect(within(panel('Value')).getByText(/^No history yet/)).toBeTruthy()
    expect(within(panel('Growth')).getAllByText('—')).toHaveLength(4)
    expect(within(panel('Growth')).getByText('No money has moved in or out yet.')).toBeTruthy()
  })

  it('draws a debt account as what it owes, with no start-plus-deposits line and no market gap', async () => {
    const card: AccountView = { ...accountFixture, id: 'card', name: 'Credit card', category: 'debt', value: 640,
      holdings: [], cash: 0, cash_weight: null, growth: { ytd: null, '1y': null, all: null },
      points: [{ date: '2026-09-23', value: 587.12, net_flow: 0 }, { date: '2026-09-24', value: 702.4, net_flow: -115.28 },
        { date: '2026-09-25', value: 640, net_flow: 62.4 }] }
    renderApp('/accounts/card', { account: [{ id: 'card', view: card }] })
    const value = await findPanel('Value')
    expect(value.textContent).not.toMatch(/Start \+ deposits|the gap between the lines is the market/)
    expect(value.textContent).toContain('What it owes')
    expect(within(value).getByRole('img', { name: 'What the account owes over time' })).toBeTruthy()
    fireEvent.click(within(value).getByRole('button', { name: 'Table' }))
    expect([...value.querySelectorAll('thead th')].map((th) => th.textContent)).toEqual(['Date', 'Owed', 'In or out'])
  })

  it('shows an unknown account as not found, inside the shell', async () => {
    const answer = () => Promise.resolve(new Response('{"detail":"no such account: nope"}', { status: 404 }))
    renderApp('/accounts/nope', {}, answer)
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    const crumbs = screen.getByRole('navigation', { name: 'Breadcrumb' })
    expect(crumbs.textContent).toBe('MoneyAccounts')
    expect(within(crumbs).getByRole('link', { name: 'Accounts' }).getAttribute('href')).toBe('/accounts')
  })

  it('says it is loading, and says so plainly when the account could not load', async () => {
    const { unmount } = renderApp('/accounts/roth', { account: [] }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the account…')).toBeTruthy()
    unmount()
    renderApp('/accounts/roth', { account: [] })
    expect((await screen.findByRole('alert')).textContent).toBe('This account couldn’t load: network is off in tests')
  })

  it('lists a bank account’s transactions newest first, with the totals, a Show filter and a search', async () => {
    renderApp('/accounts/checking', { account: [{ id: 'checking', view: accountCheckingFixture }] })
    const panel = await findPanel('Transactions')
    const t = accountCheckingFixture.transactions as NonNullable<AccountView['transactions']>
    expect(panel.querySelector('.panel-sub')?.textContent).toBe(
      `${t.count} since ${flowDay(t.since, '2026')} · in ${money(t.money_in)} · out ${money(t.money_out)}`)
    const body = rows(panel)
    expect(body).toHaveLength(t.count)
    expect(body[0]).toContain(t.rows[0].description)
    expect(body[0]).toContain(flowDay(t.rows[0].date, '2026'))
    fireEvent.click(within(panel).getByRole('button', { name: 'Out' }))
    expect(rows(panel).length).toBeGreaterThan(0)
    expect(rows(panel).every((r) => r?.includes('−$'))).toBe(true)
    fireEvent.click(within(panel).getByRole('button', { name: 'In' }))
    expect(rows(panel).length).toBeGreaterThan(0)
    expect(rows(panel).every((r) => r?.includes('+$'))).toBe(true)
    fireEvent.click(within(panel).getByRole('button', { name: 'All' }))
    const search = within(panel).getByRole('searchbox', { name: 'Search transactions' })
    fireEvent.change(search, { target: { value: 'rent' } })
    expect(rows(panel).length).toBeGreaterThan(0)
    expect(rows(panel).every((r) => /rent/i.test(r ?? ''))).toBe(true)
    fireEvent.change(search, { target: { value: 'landlord' } }) // the counterparty matches too
    expect(rows(panel).length).toBeGreaterThan(0)
    fireEvent.change(search, { target: { value: 'zzz' } })
    expect(panel.textContent).toContain('No transactions match.')
  })

  it('shows no Transactions panel for an account whose source sends none', async () => {
    renderApp('/accounts/roth')
    await findPanel('Holdings')
    expect(() => panel('Transactions')).toThrow()
  })
})
