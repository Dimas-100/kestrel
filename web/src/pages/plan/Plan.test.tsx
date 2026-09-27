import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { PlanView } from '../../lib/api'
import { planFixture, renderApp } from '../../test/renderApp'

const rows = (region: HTMLElement) => [...region.querySelectorAll('li')]

describe('Plan', () => {
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
