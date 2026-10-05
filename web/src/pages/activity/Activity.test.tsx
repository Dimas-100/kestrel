import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ActivityView } from '../../lib/api'
import { activityFixture, renderApp } from '../../test/renderApp'

const region = (name: string) => screen.getByRole('region', { name })

describe('Activity', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with the summary, today on the clock with the now rule, the next run, and today’s list', async () => {
    renderApp('/activity')
    const title = await screen.findByRole('heading', { level: 1, name: 'Activity' })
    expect(title.closest('header')?.textContent).toContain(activityFixture.summary)
    const today = region('Today')
    expect(within(today).getByRole('img', { name: 'Today’s runs on the clock' })).toBeTruthy()
    expect(today.textContent).toContain('now 17:08') // 21:08 UTC in New York, the shell's zone
    expect(today.textContent).toContain(`Next: ${activityFixture.next_run?.label} at 17:30`)
    expect(within(today).getAllByRole('listitem')).toHaveLength(activityFixture.days[0].runs.length)
  })

  it('shows the week as a grid, one row per job and a cell per day, with the status in words', async () => {
    renderApp('/activity')
    await screen.findByRole('heading', { level: 1, name: 'Activity' })
    const week = region('The week')
    const table = within(week).getByRole('table')
    expect(within(table).getAllByRole('columnheader')).toHaveLength(1 + 8)
    expect(within(table).getAllByRole('columnheader').pop()?.textContent).toBe('Today')
    expect(table.querySelectorAll('tbody tr')).toHaveLength(activityFixture.week.length)
    expect(within(table).getAllByText('failed').length).toBeGreaterThan(0)
    expect(within(table).getAllByText('late').length).toBeGreaterThan(0)
    expect(within(table).getAllByText('no run').length).toBeGreaterThan(0) // the weekend
  })

  it('shows a failed run with its word and detail, not colour alone', async () => {
    const failed: ActivityView = {
      ...activityFixture, next_run: null, week: [],
      days: [{ date: activityFixture.days[0].date, label: 'Today',
        runs: [{ time: activityFixture.days[0].runs[0].time, label: 'Morning run', book_id: null, book_name: null,
                status: 'failed' as const, detail: 'timed out' }] }],
    }
    renderApp('/activity', { activity: failed })
    const today = await screen.findByRole('region', { name: 'Today' })
    expect(within(today).getByText('failed')).toBeTruthy()
    expect(within(today).getByText('timed out')).toBeTruthy()
  })

  it('shows every source as a card with its status, its age and its detail', async () => {
    const withDetail: ActivityView = {
      ...activityFixture,
      sources: [{ id: 'desk', label: 'Trading desk', kind: 'feed', status: 'error' as const, last_success: null,
                 age_text: null, stale_after: '36h', detail: 'connection refused' }],
    }
    renderApp('/activity', { activity: withDetail })
    const sources = await screen.findByRole('region', { name: 'Sources' })
    const cards = within(sources).getAllByRole('article')
    expect(cards).toHaveLength(1)
    expect(cards[0].textContent).toContain('Trading desk')
    expect(cards[0].textContent).toContain('error')
    expect(cards[0].textContent).toContain('connection refused')
    expect(cards[0].textContent).toContain('stale after 36h')
  })

  it('dates a source’s last success in the profile’s time zone, not UTC', async () => {
    // 02:30 UTC on Saturday the 26th is 22:30 on Friday the 25th in New York, the shell's zone
    const late = { ...activityFixture, sources: [{ ...activityFixture.sources[0], last_success: '2026-09-26T02:30:00Z' }] }
    renderApp('/activity', { activity: late })
    const sources = await screen.findByRole('region', { name: 'Sources' })
    expect(sources.textContent).toContain('Fri 25 Sep')
    expect(sources.textContent).not.toContain('Sat 26 Sep')
  })

  it('says so when there is no activity yet', async () => {
    renderApp('/activity', { activity: { as_of: activityFixture.as_of, summary: 'No runs today.', next_run: null,
      week: [], days: [], counts: {}, alerts: [], sources: [] } })
    expect(await screen.findByText('Nothing has run yet today.')).toBeTruthy()
    expect(screen.getByText('No runs recorded yet. They appear once a scheduled task reports in.')).toBeTruthy()
    expect(screen.getByText('No alerts right now.')).toBeTruthy()
    expect(screen.getByText('No sources configured yet.')).toBeTruthy()
  })

  it('says it is loading while activity is on its way', async () => {
    renderApp('/activity', { activity: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading activity…')).toBeTruthy()
  })

  it('says so when activity could not load', async () => {
    renderApp('/activity', { activity: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Activity couldn’t load: network is off in tests')
  })
})
