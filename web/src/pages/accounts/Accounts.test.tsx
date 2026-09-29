import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { AccountsView } from '../../lib/api'
import { accountsFixture, renderApp } from '../../test/renderApp'
import { headline, kindText } from './Accounts'

// a title lookup, not a role query over the whole app: role queries dominate these tests' time
const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const rows = (region: HTMLElement) => [...region.querySelectorAll('tbody tr')].map((r) => r.textContent)
const ytd = accountsFixture.growth.ytd!

describe('Accounts', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with how many accounts, how much, and this year in two figures', async () => {
    renderApp('/accounts')
    const title = await screen.findByRole('heading', { level: 1, name: 'Accounts' })
    // every account together, net of the $640.00 owed on the card
    expect(title.closest('header')?.textContent).toBe('MoneyAccounts6 accounts, $168,278.24 in all. This year the '
      + 'market added ▲ up +$11,511.65 and you deposited $13,715.25.')
  })

  it('words the sentence for one account, a withdrawal, and a year without history', () => {
    expect(headline(accountsFixture)).toEqual({ lead: '6 accounts, $168,278.24 in all.', moved: 'you deposited $13,715.25' })
    const one: AccountsView = { ...accountsFixture, count: 1, total: 500, growth: {
      ...accountsFixture.growth, ytd: { ...ytd, deposits: -250 } } }
    expect(headline(one)).toEqual({ lead: '1 account, $500.00 in all.', moved: 'you withdrew $250.00' })
    expect(headline({ ...accountsFixture, growth: { ...accountsFixture.growth, ytd: null } }).moved).toBeNull()
    expect([kindText({ institution: 'Bank C', account_type: '' }), kindText({ institution: '', account_type: '' })])
      .toEqual(['Bank C', ''])
  })

  it('splits the growth into what you put in and what the market added, for each window', async () => {
    renderApp('/accounts')
    const growth = await findPanel('Growth')
    expect(growth.textContent).toContain('Started at$143,051.341 Jan')
    expect(growth.textContent).toContain('You put in$13,715.25The market added▲ up +$11,511.65Now$168,278.24')
    fireEvent.click(within(growth).getByRole('button', { name: '1 year' }))
    expect(growth.textContent).toContain('Started at$128,846.51Sep 2025')
    expect(within(growth).getByRole('img', { name: '1 year: started at, you put in, the market added' })).toBeTruthy()
    fireEvent.click(within(growth).getByRole('button', { name: 'Table' }))
    expect(rows(growth)).toEqual(['Started at$128,846.51', 'You put in$16,366.62',
      'The market added▲ up +$23,065.11', 'Now$168,278.24'])
  })

  it('says under the growth when some accounts have no history, and nothing when all do', async () => {
    expect(accountsFixture.no_history).toBe(0) // every demo account has a history
    const { unmount } = renderApp('/accounts')
    expect((await findPanel('Growth')).textContent).not.toContain('no history')
    unmount()
    for (const [n, text] of [[1, "1 account has no history: counted at today's balance"],
      [3, "3 accounts have no history: counted at today's balance"]] as const) {
      const { unmount: done } = renderApp('/accounts', { accounts: { ...accountsFixture, no_history: n } })
      expect(within(await findPanel('Growth')).getByText(text)).toBeTruthy()
      done()
    }
  })

  it('shows dashes for a window without enough history', async () => {
    renderApp('/accounts', { accounts: { ...accountsFixture, growth: { ...accountsFixture.growth, ytd: null } } })
    const growth = await findPanel('Growth')
    expect(within(growth).getAllByText('—')).toHaveLength(4)
    expect(within(growth).getByText('Not enough history for this window yet.')).toBeTruthy()
  })

  it('lists every account, largest first, each opening its own page', async () => {
    renderApp('/accounts')
    const accounts = await findPanel('Accounts')
    // "Last day": the change on the history's last day (Friday's all weekend), not the calendar day's
    expect([...accounts.querySelectorAll('thead th')].map((th) => th.textContent)).toEqual([
      'Account', 'Category', 'Value', 'Share', 'Last day', 'Market this year'])
    // each row leads with its institution's initials tile (aria-hidden: the institution is named in words beside it)
    expect(rows(accounts)).toEqual([
      'BARoth IRABrokerage A · Roth IRALong-term$67,890.8140.2%▼ down −$49.79−0.07%▲ up +$5,603.44',
      'BABrokerageBrokerage A · BrokerageLong-term$51,663.7430.6%▲ up +$146.99+0.29%▲ up +$3,362.77',
      'BCHigh-yield savingsBank C · SavingsCash$24,242.8514.4%▲ up +$3.82+0.02%▲ up +$701.08',
      'BBTrading accountBrokerage B · IndividualTrading$18,467.7110.9%▼ down −$94.32−0.51%▲ up +$1,844.36',
      'BCCheckingBank C · CheckingCash$6,653.133.9%$0.000.00%$0.00', // moves by what goes in and out alone
      'BDCredit cardBank D · Credit cardDebt$640.00———', // what it owes: no share of what is held, no market growth
    ])
    expect(within(accounts).getByRole('link', { name: 'Roth IRA' }).getAttribute('href')).toBe('/accounts/roth')
  })

  it('adds up everything held across accounts: the first twelve, then all of it', async () => {
    renderApp('/accounts')
    const held = await findPanel('Everything you hold')
    expect(rows(held)).toHaveLength(12)
    expect(rows(held).slice(0, 2)).toEqual([
      'SPYS&P 500 index fund$61,723.6836.5%Brokerage, Roth IRA',
      'Cash—$38,557.2022.8%Brokerage, Checking, High-yield savings, Roth IRA, Trading account',
    ])
    fireEvent.click(within(held).getByRole('button', { name: 'Show all 14' }))
    expect(rows(held)).toHaveLength(14)
    expect(within(held).getByRole('button', { name: 'Show the first 12' })).toBeTruthy()
  })

  it('says so when there are no accounts yet', async () => {
    const none: AccountsView = { ...accountsFixture, count: 0, total: 0, accounts: [], holdings: [],
      growth: { ytd: null, '1y': null, all: null } }
    renderApp('/accounts', { accounts: none })
    const empty = await screen.findByText(/^No accounts yet\./)
    expect(empty.textContent).toBe('No accounts yet. Add a source in profile.toml, or run kestrel check if one isn’t '
      + 'reading (see docs/connectors.md).')
    expect(empty.querySelector('code')?.textContent).toBe('kestrel check')
    expect(document.querySelector('.panel-title')).toBeNull()
  })

  it('says it is loading, and says so plainly when the accounts could not load', async () => {
    const { unmount } = renderApp('/accounts', { accounts: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading your accounts…')).toBeTruthy()
    unmount()
    renderApp('/accounts', { accounts: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Accounts couldn’t load: network is off in tests')
  })
})
