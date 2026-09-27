import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { activityFixture, renderApp } from '../../test/renderApp'

describe('Activity', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists today first, and shows a table of every source', async () => {
    renderApp('/activity')
    expect(await screen.findByRole('heading', { level: 1, name: 'Activity' })).toBeTruthy()
    const runsPanel = screen.getByRole('heading', { name: 'Runs' }).closest('section') as HTMLElement
    const dayLabels = within(runsPanel).getAllByText(activityFixture.days[0].label)
    expect(dayLabels.length).toBeGreaterThan(0)
    expect(within(runsPanel).getAllByRole('listitem')).toHaveLength(activityFixture.days[0].runs.length)
    const sourcesPanel = screen.getByRole('heading', { name: 'Sources' }).closest('section') as HTMLElement
    expect(within(sourcesPanel).getAllByRole('row')).toHaveLength(activityFixture.sources.length + 1) // + header row
    expect(within(sourcesPanel).getByText('Trading desk')).toBeTruthy()
  })

  it('shows a failed run with its word and icon, not colour alone', async () => {
    const failed = {
      ...activityFixture,
      days: [{ date: activityFixture.days[0].date, label: 'Today',
        runs: [{ time: activityFixture.days[0].runs[0].time, label: 'Morning run', book_id: null, book_name: null,
                status: 'failed' as const, detail: 'timed out' }] }],
    }
    renderApp('/activity', { activity: failed })
    expect(await screen.findByText('failed')).toBeTruthy()
    expect(screen.getByText('timed out')).toBeTruthy()
  })

  it('says so when there is no activity yet', async () => {
    renderApp('/activity', { activity: { as_of: activityFixture.as_of, days: [], counts: {}, alerts: [], sources: [] } })
    expect(await screen.findByText('No runs recorded yet. They appear once a scheduled task reports in.')).toBeTruthy()
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
