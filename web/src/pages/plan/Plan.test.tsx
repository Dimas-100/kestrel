import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { GoalRow, PlanView } from '../../lib/api'
import { longDate, money } from '../../lib/format'
import { planFixture, renderApp } from '../../test/renderApp'
import { unitText } from './PlanBar'
import { nextDated } from './timeline'
import { monthsToReach, reachDate } from './whatif'

const rows = (region: HTMLElement) => [...region.querySelectorAll('li')]
const tableRows = (region: HTMLElement) => [...region.querySelectorAll('tbody tr')].map((r) => r.textContent ?? '')
const goalOf = (over: Partial<GoalRow>): GoalRow => ({ ...planFixture.goals[0], ...over })

describe('Plan', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the summary the view wrote', async () => {
    renderApp('/plan')
    const title = await screen.findByRole('heading', { level: 1, name: 'Plan' })
    expect(title.closest('header')?.textContent).toContain(planFixture.summary)
    renderApp('/plan', { plan: { ...planFixture, summary: 'Every goal is reached.' } })
    expect((await screen.findAllByText('Every goal is reached.')).length).toBeGreaterThan(0)
  })

  it('Milestones: the next three dated goals as cards with a ring each, and a table of every goal', async () => {
    renderApp('/plan')
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    const next = nextDated(planFixture.goals, 3)
    const cards = within(panel).getAllByRole('article')
    expect(cards.map((c) => within(c).getByRole('heading', { level: 3 }).textContent)).toEqual(next.map((g) => g.label))
    const first = next[0]
    expect(within(cards[0]).getByRole('img', { name: `${first.label}: ${Math.round(first.progress_pct ?? 0)}% there` })).toBeTruthy()
    expect(cards[0].textContent).toContain(`${money(first.current ?? 0, false)} / ${money(first.target, false)}`)
    expect(cards[0].textContent).toContain(`by ${longDate(first.by as string)}`)
    expect(within(panel).getByRole('img', { name: 'Your goals in time' })).toBeTruthy()
    fireEvent.click(within(panel).getByRole('button', { name: 'Table' }))
    const table = tableRows(panel)
    expect(table).toHaveLength(planFixture.goals.length)
    expect(table[0]).toContain(planFixture.goals[0].label)
    expect(table.find((r) => r.startsWith('Save into savings this year'))).toMatch(/(ahead|behind) \$/)
  })

  it('Milestones: goals due on one day are one labelled cluster on the line and one group of cards', async () => {
    renderApp('/plan')
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    const line = within(panel).getByRole('img', { name: 'Your goals in time' })
    expect(line.querySelector('[data-cluster="2"]')?.textContent).toBe('2 goals · 31 Dec 20262')
    expect(panel.textContent).toContain('Due 31 Dec 2026 · 2 goals')
  })

  it('Milestones: a card says which goals it counts toward and draws its pace when the history allows', async () => {
    renderApp('/plan')
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    const save = panel.querySelector('#goal-save-this-year') as HTMLElement
    expect(save.textContent).toContain('Counts toward A year of spending in cash, Net worth milestone too.')
    expect(within(save).getByRole('img', { name: /^Save into savings this year: (Ahead of|Behind) the straight line by \$/ })).toBeTruthy()
    const later = panel.querySelector('#goal-long-term-together') as HTMLElement // after the next three: a compact row
    expect(later.tagName).toBe('LI')
    expect(later.textContent).toContain('by 31 Dec 2031')
  })

  it('Milestones: the newest three passed show, the rest sit closed under "n earlier"', async () => {
    const passed = ['2026-09-01', '2026-08-01', '2026-07-01', '2026-06-01', '2026-05-01']
      .map((date, i) => ({ date, label: `$${15 - i}0,000`, kind: 'round' as const }))
    renderApp('/plan', { plan: { ...planFixture, passed } })
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    expect(rows(within(panel).getByRole('list', { name: 'Passed' }))).toHaveLength(3)
    const earlier = within(panel).getByText('2 earlier').closest('details') as HTMLDetailsElement
    expect(earlier.open).toBe(false)
  })

  it('Milestones: an overdue goal says was due, never a monthly pace; a far placeholder date is never overdue', async () => {
    const late = goalOf({ id: 'late', label: 'Late', by: '2026-01-01', overdue: true, months_left: null, monthly_needed: null })
    const far = goalOf({ id: 'far', label: 'Someday', by: '9999-12-31', months_left: null, monthly_needed: null, overdue: false })
    renderApp('/plan', { plan: { ...planFixture, goals: [far, late] } })
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    const cards = within(panel).getAllByRole('article')
    expect(cards[0].textContent).toContain('Late')
    expect(cards[0].textContent).toContain('was due 1 Jan 2026')
    expect(cards[0].textContent).not.toContain('a month')
    expect(cards[1].textContent).toContain('by 31 Dec 9999')
    expect(cards[1].textContent).not.toContain('was due')
  })

  it('Milestones: says the monthly amount for what it is, and a goal it cannot see shows — with why in the table', async () => {
    const value = goalOf({ id: 'v', label: 'Value goal', measure: 'value', monthly_needed: 120 })
    const deposits = goalOf({ id: 'd', label: 'Deposits goal', measure: 'deposits', monthly_needed: 80 })
    const blind = goalOf({ id: 'b', label: 'Blind', measure: 'deposits', current: null, progress_pct: null,
      monthly_needed: null, unknown_reason: 'no deposit history for Checking' })
    const missing = goalOf({ id: 'm', label: 'Missing', current: null, progress_pct: null, monthly_needed: null,
      missing_accounts: ['gone'] })
    renderApp('/plan', { plan: { ...planFixture, goals: [value, deposits, blind, missing] } })
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    expect(within(panel).getByText('about $120.00 a month, before any market growth')).toBeTruthy()
    expect(within(panel).getByText('about $80.00 a month in deposits')).toBeTruthy()
    expect(within(panel).getAllByRole('article')).toHaveLength(2) // the two it can measure
    fireEvent.click(within(panel).getByRole('button', { name: 'Table' }))
    const table = tableRows(panel)
    expect(table.find((r) => r.includes('Blind'))).toContain('no deposit history for Checking')
    expect(table.find((r) => r.includes('Missing'))).toContain('account not in any source: gone')
    expect(within(panel).queryByRole('progressbar', { name: 'Blind' })).toBeNull()
  })

  it('Milestones: an undated goal is an ongoing row with a progress bar', async () => {
    const floor = goalOf({ id: 'floor', label: 'Keep a floor', by: null, months_left: null, monthly_needed: null })
    renderApp('/plan', { plan: { ...planFixture, goals: [floor, planFixture.goals[0]] } })
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    expect(within(panel).getByRole('progressbar', { name: 'Keep a floor' })).toBeTruthy()
    expect(within(panel).getAllByRole('article')).toHaveLength(1)
  })

  it('This month: the three priorities as numbered cards with why and a link, the rest closed', async () => {
    renderApp('/plan')
    const panel = await screen.findByRole('region', { name: 'This month' })
    const top = within(panel).getByRole('list', { name: 'This month’s priorities' })
    const cards = [...top.children] as HTMLElement[]
    expect(cards).toHaveLength(3)
    planFixture.actions.slice(0, 3).forEach((a, i) => {
      expect(cards[i].textContent).toContain(String(i + 1))
      expect(within(cards[i]).getByRole('heading', { level: 3 }).textContent).toBe(a.title)
      expect(cards[i].textContent).toContain(a.why)
    })
    expect(cards[0].textContent).toContain('Warning')
    expect(within(cards[1]).getByRole('link', { name: 'See it in Allocation' }).getAttribute('href'))
      .toBe(`#${planFixture.actions[1].anchor}`)
    const rest = panel.querySelector('details') as HTMLDetailsElement
    expect(rest.open).toBe(false)
    expect(rest.querySelector('summary')?.textContent).toBe(`Also this month (${planFixture.actions.length - 3})`)
  })

  it('This month: a priority’s link opens and focuses the place that backs it', async () => {
    renderApp('/plan')
    const panel = await screen.findByRole('region', { name: 'This month' })
    const watch = planFixture.actions.find((a) => a.kind === 'thesis' && a.level === 'note')
    expect(watch).toBeTruthy()
    fireEvent.click(within(panel).getAllByRole('link', { name: 'See it in Theses' }).at(-1) as HTMLElement)
    expect(document.activeElement?.id).toBe(watch?.anchor)
  })

  it('This month: nothing to do says so, and never calls an unmeasured target on plan', async () => {
    renderApp('/plan', { plan: { ...planFixture, actions: [] } })
    expect((await screen.findAllByText(/^Nothing to do this month: every measured target/)).length).toBeGreaterThan(0)
    renderApp('/plan', { plan: { ...planFixture, actions: [], counts: { ...planFixture.counts, unknown: 2 } } })
    const line = (await screen.findAllByText(/can’t be measured yet/)).at(-1) as HTMLElement
    expect(line.textContent).toContain('2 targets can’t be measured yet, so they aren’t counted as on plan')
    expect(line.textContent).not.toContain('every target is on plan')
  })

  it('Allocation: one row per target on the account’s scale, never stacked, off-plan accounts first', async () => {
    renderApp('/plan')
    const panel = await screen.findByRole('region', { name: 'Allocation against plan' })
    const blocks = within(panel).getAllByRole('group').filter((g) => g.tagName === 'SECTION' && g.getAttribute('aria-label') !== 'Other targets')
    expect(blocks.map((b) => b.getAttribute('aria-label'))).toEqual(['Roth IRA', 'Brokerage'])
    expect(blocks[0].textContent).toContain('1 of 3 on plan')
    // each share is drawn and named at its own figure, with its band and aim
    expect(within(blocks[0]).getByRole('img', { name: 'XLP: 16.0% held, band 18–22%, aim 20.0%' })).toBeTruthy()
    const xlp = blocks[0].querySelector('#target-roth-xlp') as HTMLElement
    expect(xlp.textContent).toContain('Under')
    expect(xlp.textContent).toContain('$1,357.86 under the low end')
    expect(blocks[1].textContent).toContain('9.0% of Brokerage sits in no target, cash included.')
    const ratio = planFixture.unscoped[0] // a ratio keeps its own scale
    expect(within(panel).getByRole('img', { name: `${ratio.label}: ${unitText(ratio.actual as number, ratio.unit)} actual, band from 4x, aim 6.0x` })).toBeTruthy()
    fireEvent.click(within(panel).getByRole('button', { name: 'Table' }))
    const table = tableRows(panel)
    expect(table).toHaveLength(planFixture.accounts.reduce((n, a) => n + a.rows.length, 0) + planFixture.unscoped.length)
    expect(table.find((r) => r.startsWith('XLI'))).toContain('New money only')
  })

  it('Allocation: a sleeve’s members sit under it, and a plan that never sells never reads as trim', async () => {
    renderApp('/plan')
    const panel = await screen.findByRole('region', { name: 'Allocation against plan' })
    const brokerage = within(panel).getByRole('group', { name: 'Brokerage' })
    const ids = [...brokerage.querySelectorAll('li.range-row')].map((li) => [li.id, li.getAttribute('data-depth')])
    const sleeve = ids.findIndex(([id]) => id === 'target-brokerage-stocks')
    expect(ids[sleeve + 1]).toEqual(['target-brokerage-cost', '1'])
    const cost = brokerage.querySelector('#target-brokerage-cost') as HTMLElement
    expect(cost.textContent).toContain('Over')
    expect(cost.textContent).toContain('dilutes with new money, no sale')
    expect(cost.textContent).toContain(', in Single stocks')
    expect((brokerage.querySelector('#target-brokerage-xli') as HTMLElement).textContent).toContain('steer new money here')
    expect(brokerage.textContent).not.toMatch(/Trim|\$[\d,.]+ over the high end/)
  })

  it('Allocation: a zero-value known account’s gap is in points, never a bogus dollar figure, to two decimals when tiny', async () => {
    const base = { symbols: [], unit: '%' as const, note: '', rebalance: 'trades' as const, parent: null }
    const v: PlanView = { ...planFixture,
      accounts: [{ account_id: 'z', name: 'Zero', known: true, untargeted_pct: null, rows: [
        { ...base, id: 't3', label: 'VTI', symbols: ['VTI'], target: 60, low: 55, high: 65, actual: 0,
          status: 'under', gap: 55, gap_unit: 'pts', gap_text: 'under the low end' },
        { ...base, id: 't4', label: 'BND', symbols: ['BND'], target: 10, low: 9, high: 11, actual: 11.05,
          status: 'over', gap: -0.05, gap_unit: 'pts', gap_text: 'over the high end' },
      ] }] }
    renderApp('/plan', { plan: v })
    const panel = await screen.findByRole('region', { name: 'Allocation against plan' })
    expect(within(panel).getByText('55.0 pts under the low end')).toBeTruthy()
    expect(within(panel).getByText('0.05 pts over the high end')).toBeTruthy()
    expect(within(panel).queryByText(/\$55/)).toBeNull()
  })

  it('Allocation: a target naming an unsent account sits under its own id, unlinked, not "Across every account"', async () => {
    const v: PlanView = { ...planFixture,
      accounts: [{ account_id: 'ghost', name: 'ghost', known: false, untargeted_pct: null, rows: [{
        id: 'g1', label: 'VTI', symbols: ['VTI'], unit: '%', target: 60, low: 55, high: 65, actual: null,
        status: 'unknown', gap: null, gap_unit: null, gap_text: '', note: '', rebalance: 'trades', parent: null }] }],
      unscoped: [] }
    renderApp('/plan', { plan: v })
    const panel = await screen.findByRole('region', { name: 'Allocation against plan' })
    const block = within(panel).getByRole('group', { name: 'ghost' })
    expect(within(block).queryByRole('link')).toBeNull()
    expect(block.textContent).toContain('can’t be measured yet')
    expect(within(panel).queryByText('Across every account')).toBeNull()
  })

  it('Theses: chips count each health, the exceptions lead and open, the healthy and unrated ones closed', async () => {
    renderApp('/plan')
    const theses = await screen.findByRole('region', { name: 'Theses' })
    expect(theses.textContent).toContain('1 alert · 1 watch · 2 ok · 9 not rated')
    const exceptions = within(theses).getByRole('list', { name: 'Theses that need a look' })
    expect([...exceptions.children].map((li) => li.id)).toEqual(['thesis-HD', 'thesis-XLE'])
    const closed = [...theses.querySelectorAll('details.also')] as HTMLDetailsElement[]
    expect(closed.map((d) => [d.querySelector('summary')?.textContent, d.open])).toEqual(
      [['2 holding', false], ['9 not rated', false]])
    expect(closed[0].querySelector('#thesis-COST')).toBeTruthy()
    const items = rows(theses)
    expect(items[0].textContent).toContain('HD')
    expect(items[0].textContent).toContain('Alert')
    expect(items[0].textContent).toContain('Comparable sales fell for a third quarter')
    const details = items[0].querySelector('details') as HTMLDetailsElement
    expect(details.open).toBe(false)
    expect(within(items[0]).getByText('Comparable sales fall for a fourth quarter')).toBeTruthy()
  })

  it('names an investing feed in the empty state', async () => {
    const empty: PlanView = { ...planFixture, summary: '', actions: [], accounts: [], unscoped: [], theses: [], goals: [],
      counts: { off_plan: 0, theses_alert: 0, theses_watch: 0, unknown: 0, need_trade: 0 } }
    renderApp('/plan', { plan: empty })
    const text = await screen.findByText(/^No plan yet\./)
    expect(text.textContent).toContain('investing feed')
    expect(screen.queryByRole('region', { name: 'Milestones' })).toBeNull()
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
    fireEvent.click(await screen.findByRole('link', { name: 'Plan' }))
    await screen.findByRole('heading', { level: 1, name: 'Plan' })
  })

  it('Milestones: lists what was passed, says the day a goal was reached, and tries a monthly amount', async () => {
    const reached = goalOf({ id: 'done', label: 'Done', reached: true, progress_pct: 100, reached_on: '2026-08-15',
      months_left: null, monthly_needed: null })
    const passed = [{ date: '2026-09-01', label: '$150,000', kind: 'round' as const }, { date: '2026-08-15', label: 'Done', kind: 'goal' as const }]
    renderApp('/plan', { plan: { ...planFixture, goals: [...planFixture.goals, reached], passed } })
    const panel = await screen.findByRole('region', { name: 'Milestones' })
    const list = within(panel).getByRole('list', { name: 'Passed' })
    expect(rows(list).map((li) => li.textContent)).toEqual(['$150,000passed 1 Sep 2026', 'Donereached 15 Aug 2026'])
    const first = nextDated(planFixture.goals, 1)[0]
    const card = within(panel).getAllByRole('article')[0]
    expect(within(card).queryByRole('slider')).toBeNull() // the what-if opens on demand
    fireEvent.click(within(card).getByRole('button', { name: 'Try a monthly amount' }))
    const slider = within(panel).getByRole('slider', { name: `${first.label}: a month` }) as HTMLInputElement
    expect(Number(slider.value)).toBe(Math.round(first.monthly_needed as number))
    fireEvent.change(slider, { target: { value: String(Math.round((first.monthly_needed as number) * 2)) } })
    const months = monthsToReach(first.current as number, first.target, Math.round((first.monthly_needed as number) * 2)) as number
    expect(panel.textContent).toContain(`reaches ${money(first.target, false)} by ${longDate(reachDate(planFixture.as_of, months))}`)
    fireEvent.change(slider, { target: { value: '0' } })
    expect(panel.textContent).toContain('never at this pace')
    fireEvent.click(within(panel).getByRole('button', { name: 'Table' }))
    expect(tableRows(panel).find((r) => r.includes('Done'))).toContain('Reached 15 Aug 2026')
  })
})
