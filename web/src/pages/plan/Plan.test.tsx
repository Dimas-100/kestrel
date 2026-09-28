import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PlanView } from '../../lib/api'
import { planFixture, renderApp } from '../../test/renderApp'

const rows = (region: HTMLElement) => [...region.querySelectorAll('li')]

describe('Plan', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists off-plan targets first inside each account', async () => {
    renderApp('/plan')
    const targets = await screen.findByRole('region', { name: 'Targets' })
    const roth = within(targets).getByText('Roth IRA').closest('div') as HTMLElement
    const labels = rows(roth).map((li) => li.querySelector('.text-sm')?.textContent)
    expect(labels).toEqual(['XLP', 'XLV', 'SPY']) // the two off-plan rows lead; SPY (on plan) comes last
    expect(rows(roth)[0].textContent).toContain('Under')
    expect(rows(roth)[1].textContent).toContain('Over')
  })

  it('shows a health word and reasons for each thesis, alert leading', async () => {
    renderApp('/plan')
    const theses = await screen.findByRole('region', { name: 'Theses' })
    const items = rows(theses)
    expect(items[0].textContent).toContain('HD')
    expect(items[0].textContent).toContain('Alert')
    expect(items[0].textContent).toContain('Comparable sales fell for a third quarter')
  })

  it('keeps the wrong-if list behind a disclosure', async () => {
    renderApp('/plan')
    const theses = await screen.findByRole('region', { name: 'Theses' })
    const first = rows(theses)[0]
    const details = first.querySelector('details') as HTMLDetailsElement
    expect(details.open).toBe(false)
    expect(within(first).getByText('Comparable sales fall for a fourth quarter')).toBeTruthy()
  })

  it('shows each goal with its progress and target', async () => {
    renderApp('/plan')
    const goals = await screen.findByRole('region', { name: 'Goals' })
    expect(within(goals).getByText('Grow the Roth IRA')).toBeTruthy()
    const bars = within(goals).getAllByRole('progressbar')
    expect(bars.length).toBe(planFixture.goals.length)
    expect(within(goals).getAllByText(/a month would reach it/).length).toBeGreaterThan(0)
  })

  it('shows a zero-value known account’s gap in points, never a bogus dollar figure', async () => {
    // the bug this guards: gap_unit, not the account-known grouping, decides money vs points
    const v: PlanView = { ...planFixture,
      accounts: [{ account_id: 'z', name: 'Zero', known: true, rows: [{
        id: 't3', label: 'VTI', symbols: ['VTI'], unit: '%', target: 60, low: 55, high: 65, actual: 0,
        status: 'under', gap: 55, gap_unit: 'pts', gap_text: 'under the low end', note: '',
      }] }] }
    renderApp('/plan', { plan: v })
    const targets = await screen.findByRole('region', { name: 'Targets' })
    expect(within(targets).getByText('55.0 pts under the low end')).toBeTruthy()
    expect(within(targets).queryByText(/\$55/)).toBeNull()
  })

  it('shows a points/ratio gap under 0.1 to two decimals, never a rounded "0.0"', async () => {
    const v: PlanView = { ...planFixture,
      accounts: [{ account_id: 'z', name: 'Zero', known: true, rows: [{
        id: 't3', label: 'VTI', symbols: ['VTI'], unit: '%', target: 60, low: 55, high: 65, actual: 54.97,
        status: 'under', gap: 0.03, gap_unit: 'pts', gap_text: 'under the low end', note: '',
      }] }] }
    renderApp('/plan', { plan: v })
    const targets = await screen.findByRole('region', { name: 'Targets' })
    expect(within(targets).getByText('0.03 pts under the low end')).toBeTruthy()
    expect(within(targets).queryByText('0.0 pts under the low end')).toBeNull()
  })

  it('groups a target naming an unsent account under its own id, not "Across every account"', async () => {
    const v: PlanView = { ...planFixture,
      accounts: [{ account_id: 'gone', name: 'gone', known: false, rows: [{
        id: 't2', label: 'VTI', symbols: ['VTI'], unit: '%', target: 60, low: 55, high: 65, actual: 40,
        status: 'under', gap: 15, gap_unit: 'pts', gap_text: 'under the low end', note: '',
      }] }], unscoped: [] }
    renderApp('/plan', { plan: v })
    const targets = await screen.findByRole('region', { name: 'Targets' })
    expect(within(targets).getByText(/no source sent this account/)).toBeTruthy()
    expect(within(targets).queryByText('Across every account')).toBeNull()
    expect(within(targets).queryByRole('link', { name: 'gone' })).toBeNull() // never a link to a nonexistent account
  })

  it('shows a goal with a missing account as "—" and names the missing id, with no progress bar', async () => {
    const v: PlanView = { ...planFixture,
      goals: [{ id: 'g', label: 'Grow', scope_text: 'gone', current: null, target: 100000, progress_pct: null,
        by: '2030-12-31', months_left: null, monthly_needed: null, reached: false, missing_accounts: ['gone'] }] }
    renderApp('/plan', { plan: v })
    const goals = await screen.findByRole('region', { name: 'Goals' })
    expect(within(goals).getByText(/account not in any source: gone/)).toBeTruthy()
    expect(within(goals).queryByRole('progressbar')).toBeNull()
  })

  it('shows an overdue, unreached goal as "was due", never a monthly pace', async () => {
    const v: PlanView = { ...planFixture,
      goals: [{ id: 'g4', label: 'Overdue', scope_text: 'A', current: 5000, target: 10000, progress_pct: 50,
        by: '2025-06-30', months_left: null, monthly_needed: null, reached: false, missing_accounts: [] }] }
    renderApp('/plan', { plan: v })
    const goals = await screen.findByRole('region', { name: 'Goals' })
    expect(within(goals).getByText('was due 30 Jun 2025')).toBeTruthy()
    expect(within(goals).queryByText(/a month would reach it/)).toBeNull()
  })

  it('names an investing feed in the empty state', async () => {
    const empty: PlanView = { accounts: [], unscoped: [], theses: [], goals: [],
      counts: { off_plan: 0, theses_alert: 0, theses_watch: 0 }, as_of: planFixture.as_of }
    renderApp('/plan', { plan: empty })
    expect(await screen.findByText(/an investing feed/)).toBeTruthy()
    expect(screen.queryByRole('region')).toBeNull()
  })

  it('says it is loading, and says so plainly when the plan could not load', async () => {
    const { unmount } = renderApp('/plan', { plan: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading your plan…')).toBeTruthy()
    unmount()
    renderApp('/plan', { plan: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Plan couldn’t load: network is off in tests')
  })

  it('opens Plan from the sidebar', async () => {
    renderApp('/')
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    fireEvent.click(within(nav).getByRole('link', { name: /Plan/ }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Plan' })).toBeTruthy()
  })
})
