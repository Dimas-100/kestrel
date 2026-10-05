import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { CalendarView } from '../../lib/api'
import { calendarFixture, renderApp } from '../../test/renderApp'
import { eventKey, isHttpsUrl, matches } from './Calendar'

const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const toList = async () => fireEvent.click(await screen.findByRole('button', { name: 'List' }))

describe('Calendar', { timeout: 15_000 }, () => {
  it('words matching and the https guard', () => {
    expect(matches('earnings', 'all')).toBe(true)
    expect(matches('earnings', 'filing')).toBe(false)
    expect(matches('earnings', 'earnings')).toBe(true)
    expect(isHttpsUrl('https://www.sec.gov/x')).toBe(true)
    expect(isHttpsUrl('http://www.sec.gov/x')).toBe(false)
    expect(isHttpsUrl('javascript:alert(1)')).toBe(false)
    expect(isHttpsUrl('')).toBe(false)
  })

  it('keys an event row by its own fields, stably across list re-orders', () => {
    const a = { date: '2026-10-05', symbol: 'COST', kind: 'earnings' as const, title: 'Quarterly results',
      detail: '', url: '', held: true }
    const b = { ...a, symbol: 'KO' } // a different symbol makes a different key
    expect(eventKey(a)).toBe('2026-10-05|earnings|COST|Quarterly results')
    expect(eventKey(a)).not.toBe(eventKey(b))
  })

  it('opens on the month: this month, with today selected and nothing on it', async () => {
    renderApp('/calendar')
    await screen.findByRole('heading', { level: 1, name: 'Calendar' })
    expect(screen.getByRole('grid', { name: 'September 2026' })).toBeTruthy()
    const day = await findPanel('Fri 25 Sep')
    expect(day.textContent).toContain('Nothing on this day.')
    expect(document.querySelector('#calendar-upcoming-title')).toBeNull()
  })

  it('selecting a day lists its events beside the grid', async () => {
    renderApp('/calendar')
    await screen.findByRole('grid', { name: 'September 2026' })
    fireEvent.click(screen.getByRole('button', { name: 'Next month' }))
    fireEvent.click(screen.getByRole('button', { name: 'Mon 5 Oct, 1 event' }))
    const day = await findPanel('Mon 5 Oct')
    expect(day.querySelector('.panel-sub')?.textContent).toBe('1 event')
    expect(within(day).getByText('COST')).toBeTruthy()
    expect(within(day).getByText('Held')).toBeTruthy()
  })

  it('the kind filter narrows the grid too', async () => {
    renderApp('/calendar')
    await screen.findByRole('grid', { name: 'September 2026' })
    fireEvent.click(screen.getByRole('button', { name: 'Next month' }))
    fireEvent.click(screen.getByRole('button', { name: 'Dividend' }))
    expect(screen.getByRole('button', { name: 'Tue 6 Oct, 1 event' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Mon 5 Oct, 1 event' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Mon 5 Oct' })).toBeTruthy()
  })

  it('shows the counts by kind and, as the list, both panels', async () => {
    renderApp('/calendar')
    await screen.findByRole('heading', { level: 1, name: 'Calendar' })
    expect(screen.getByText('Earnings 8')).toBeTruthy()
    expect(screen.getByText('Filing 9')).toBeTruthy()
    expect(screen.getByText('Insider 2')).toBeTruthy()
    expect(screen.getByText('Dividend 1')).toBeTruthy()
    expect(screen.getByText('Other 0')).toBeTruthy()
    await toList()
    const upcoming = await findPanel('Upcoming')
    expect(upcoming.textContent).toContain('COST')
    const recent = await findPanel('Recent')
    expect(recent.textContent).toContain('MSFT')
    expect(screen.queryByRole('grid')).toBeNull()
  })

  it('narrows both lists to the selected kind, and back to all', async () => {
    renderApp('/calendar')
    await toList()
    const upcoming = await findPanel('Upcoming')
    const recent = await findPanel('Recent')
    expect(within(upcoming).getAllByText('Earnings').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Insider' }))
    expect(within(upcoming).queryByText('Earnings')).toBeNull()
    expect(within(recent).getAllByText('Insider').length).toBeGreaterThan(0)
    expect(within(recent).queryByText('Filing')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'All' }))
    expect(within(upcoming).getAllByText('Earnings').length).toBeGreaterThan(0)
  })

  it('opens a source link in a new tab, safely', async () => {
    renderApp('/calendar')
    await toList()
    const recent = await findPanel('Recent')
    const link = within(recent).getAllByRole('link', { name: /Source/ })[0]
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noopener noreferrer')
    expect(link.getAttribute('href')).toMatch(/^https:\/\//)
  })

  it('marks a held event, and never renders a title as markup', async () => {
    const withHtml: CalendarView = {
      ...calendarFixture,
      upcoming: [{
        week_start: calendarFixture.today,
        items: [{ date: calendarFixture.today, symbol: 'ZZZ', kind: 'earnings', title: '<b>Bold</b> title',
                 detail: '', url: '', held: true }],
      }],
      recent: [],
    }
    renderApp('/calendar', { calendar: withHtml })
    await toList()
    const upcoming = await findPanel('Upcoming')
    expect(within(upcoming).getByText('Held')).toBeTruthy()
    expect(upcoming.querySelector('b')).toBeNull()
    expect(upcoming.textContent).toContain('<b>Bold</b> title')
  })

  it('says so when there are no events at all', async () => {
    const none: CalendarView = { ...calendarFixture, upcoming: [], recent: [],
      counts: { earnings: 0, filing: 0, insider: 0, dividend: 0, other: 0 } }
    renderApp('/calendar', { calendar: none })
    const empty = await screen.findByText(/^No calendar events yet\./)
    expect(empty.textContent).toContain('an investing feed')
    expect(document.querySelector('.panel-title')).toBeNull()
    expect(screen.queryByRole('grid')).toBeNull()
  })

  it('says it is loading, and says so plainly when the calendar could not load', async () => {
    const { unmount } = renderApp('/calendar', { calendar: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the calendar…')).toBeTruthy()
    unmount()
    renderApp('/calendar', { calendar: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Calendar couldn’t load: network is off in tests')
  })
})
