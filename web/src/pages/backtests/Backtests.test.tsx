import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Backtest, BacktestsView, FamilyRow } from '../../lib/api'
import { backtestsFixture, renderApp } from '../../test/renderApp'
import { matchesRowFilter, matchesSearch, VERDICT_WORD } from './Backtests'

const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))

function bt(over: Partial<Backtest>): Backtest {
  return {
    id: 'x', name: 'X', family: 'Fam', window: 'develop', verdict: 'pass', at: '2026-09-20T00:00:00Z',
    strategy_id: null, trades: 10, avg_trade_pct: 0.5, t_stat: 2.5, calmar: 1, max_drawdown_pct: -5, note: '',
    ...over,
  }
}

describe('Backtests', { timeout: 15_000 }, () => {
  it('filters rows by all/passed/failed, and never by refused or pending', () => {
    expect(matchesRowFilter('pass', 'all')).toBe(true)
    expect(matchesRowFilter('pass', 'passed')).toBe(true)
    expect(matchesRowFilter('fail', 'passed')).toBe(false)
    expect(matchesRowFilter('fail', 'failed')).toBe(true)
    expect(matchesRowFilter('refused', 'passed')).toBe(false)
    expect(matchesRowFilter('refused', 'failed')).toBe(false)
    expect(matchesRowFilter('pending', 'all')).toBe(true)
  })

  it('searches by family or by name, case-insensitively', () => {
    const row = bt({ family: 'Dip buy', name: 'Dip buy C' })
    expect(matchesSearch(row, '')).toBe(true)
    expect(matchesSearch(row, 'dip')).toBe(true)
    expect(matchesSearch(row, 'BUY C')).toBe(true)
    expect(matchesSearch(row, 'gap fade')).toBe(false)
  })

  it('shows the totals and every verdict word carried on its chip, not colour alone', async () => {
    renderApp('/backtests')
    await screen.findByRole('heading', { level: 1, name: 'Backtests' })
    const totals = document.getElementById('backtests-totals') as HTMLElement
    expect(within(totals).getByText('Total results').parentElement?.textContent).toBe('Total results120')
    expect(within(totals).getByText('Candidates').parentElement?.textContent).toBe('Candidates108')
    const families = await findPanel('Families')
    for (const word of Object.values(VERDICT_WORD)) {
      expect(within(families).getAllByText(word).length).toBeGreaterThan(0)
    }
  })

  it('dates a result and a family’s last run in the profile’s time zone, not UTC', async () => {
    // 02:30 UTC on Saturday the 26th is 22:30 on Friday the 25th in New York, the shell's zone
    const at = '2026-09-26T02:30:00Z'
    const row = bt({ id: 'late', name: 'Late night', family: 'Night owl', at })
    const family: FamilyRow = { family: 'Night owl', candidates: 1, best: row, verdicts: { develop: 'pass' },
      last_at: at }
    renderApp('/backtests', { backtests: { ...backtestsFixture, families: [family], rows: [row] } })
    for (const name of ['Families', 'Results']) {
      const region = await findPanel(name)
      expect(within(region).getByText('Fri 25 Sep')).toBeTruthy()
      expect(within(region).queryByText('Sat 26 Sep')).toBeNull()
    }
  })

  it('lists every family with its best result and a chip per window', async () => {
    renderApp('/backtests')
    const families = await findPanel('Families')
    expect(families.textContent).toContain('Momentum rank')
    expect([...families.querySelectorAll('thead th')].map((th) => th.textContent))
      .toEqual(['Family', 'Candidates', 'Best result', 'develop', 'confirm', 'Last ran'])
  })

  it('narrows the results table by verdict (with proper words, via the shared Seg) and by a search term', async () => {
    renderApp('/backtests')
    const results = await findPanel('Results')
    const rowCount = () => within(results).getAllByRole('row').length - 1 // minus the header row
    const all = rowCount()
    fireEvent.click(within(results).getByRole('button', { name: 'Passed' }))
    const passed = rowCount()
    expect(passed).toBeGreaterThan(0)
    expect(passed).toBeLessThan(all)
    fireEvent.click(within(results).getByRole('button', { name: 'All' }))
    expect(rowCount()).toBe(all)
    fireEvent.change(within(results).getByRole('searchbox', { name: /Search/ }), { target: { value: 'dip buy' } })
    expect(rowCount()).toBeGreaterThan(0)
    expect(rowCount()).toBeLessThan(all)
    expect(results.textContent).toContain('Dip buy')
    expect(results.textContent).not.toContain('Gap fade')
  })

  it('shows why a refused or pending result is that way, beside its verdict', async () => {
    renderApp('/backtests')
    const results = await findPanel('Results')
    fireEvent.change(within(results).getByRole('searchbox', { name: /Search/ }), { target: { value: 'overnight hold' } })
    // the demo's "Overnight hold" confirm result is refused, with a note explaining why
    expect(results.textContent).toContain('refused: too few trades in the develop window to judge')
    const families = await findPanel('Families')
    const weeklyReversal = [...families.querySelectorAll('tbody tr')]
      .find((row) => row.textContent?.startsWith('Weekly reversal'))
    // its best result is still pending (no candidate has passed yet), and the row says why
    expect(weeklyReversal?.textContent).toContain('running')
  })

  it('shows the first families then all of them, when there are more than the page shows', async () => {
    const many: FamilyRow[] = Array.from({ length: 30 }, (_, i) => ({
      family: `Family ${i}`, candidates: 1, verdicts: {}, last_at: '2026-09-20T00:00:00Z',
      best: bt({ id: `b${i}`, name: `Family ${i} A`, family: `Family ${i}`, verdict: 'fail' }),
    }))
    const view: BacktestsView = { ...backtestsFixture, families: many }
    renderApp('/backtests', { backtests: view })
    const families = await findPanel('Families')
    expect(within(families).getAllByRole('row')).toHaveLength(1 + 25) // header + first 25
    fireEvent.click(within(families).getByRole('button', { name: 'Show all 30' }))
    expect(within(families).getAllByRole('row')).toHaveLength(1 + 30)
    expect(within(families).getByRole('button', { name: 'Show the first 25' })).toBeTruthy()
  })

  it('says so when there are no backtests yet', async () => {
    const none: BacktestsView = { ...backtestsFixture, totals: { results: 0, candidates: 0, families: 0,
      passes_by_window: {} }, windows: [], families: [], rows: [] }
    renderApp('/backtests', { backtests: none })
    const empty = await screen.findByText(/^No backtests yet\./)
    expect(empty.textContent).toContain('the research record')
    expect(document.querySelector('.panel-title')).toBeNull()
  })

  it('says it is loading, and says so plainly when the record could not load', async () => {
    const { unmount } = renderApp('/backtests', { backtests: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the research record…')).toBeTruthy()
    unmount()
    renderApp('/backtests', { backtests: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Backtests couldn’t load: network is off in tests')
  })
})
