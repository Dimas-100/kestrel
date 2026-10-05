import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SettingsView } from '../../lib/api'
import { renderApp, settingsFixture } from '../../test/renderApp'
import { readable } from './Settings'

const panel = (name: string) => {
  const title = [...document.querySelectorAll('.panel-title')].find((t) => t.textContent === name)
  if (!title) throw new Error(`no panel titled "${name}"`)
  return title.closest('section') as HTMLElement
}
const findPanel = (name: string) => waitFor(() => panel(name))
const cards = (region: HTMLElement) => within(region).getAllByRole('article')

describe('Settings', { timeout: 15_000 }, () => {
  it('leads with your name, then the look with its swatches, and the time where you are', async () => {
    renderApp('/settings')
    const title = await screen.findByRole('heading', { level: 1, name: 'Settings' })
    expect(title.closest('header')?.textContent).toContain(`everything here comes from ${settingsFixture.profile}`)
    const you = await findPanel('You')
    expect(within(you).getByRole('heading', { level: 3, name: settingsFixture.you.name })).toBeTruthy()
    expect(you.textContent).toContain(`Theme${readable(settingsFixture.app.theme)}`)
    expect(you.textContent).toContain(`Accent${readable(settingsFixture.app.accent)}`)
    expect(you.textContent).toContain(`Gain / loss${readable(settingsFixture.app.gain_loss)}`)
    expect(you.textContent).toContain(`Currency${settingsFixture.app.currency}`)
    expect(you.textContent).toContain(`Time zone${settingsFixture.app.timezone}`)
    expect(you.textContent).toContain('17:08 there now') // 21:08 UTC in New York
    expect(within(you).getByRole('img', { name: `the ${settingsFixture.app.accent} accent` })).toBeTruthy()
    expect(within(you).getByRole('img', { name: 'the gain colour' })).toBeTruthy()
    expect(within(you).getByRole('img', { name: 'the loss colour' })).toBeTruthy()
  })

  it('shows the benchmark, the profile in use, and the versions', async () => {
    renderApp('/settings')
    const about = await findPanel('About')
    expect(about.textContent).toContain(`Benchmark${settingsFixture.benchmark.symbol} · ${settingsFixture.benchmark.label}`)
    expect(about.textContent).toContain(`Profile${settingsFixture.profile}`)
    expect(about.textContent).toContain(`Contract${settingsFixture.contract_version}`)
    expect(about.textContent).toContain(`kestrel${settingsFixture.version}`)
  })

  it('shows a source’s last success in the profile’s time zone, not UTC', async () => {
    // 02:30 UTC on the 26th is 22:30 on the 25th in New York, the fixture profile's zone
    expect(settingsFixture.app.timezone).toBe('America/New_York')
    const view: SettingsView = { ...settingsFixture,
      sources: [{ ...settingsFixture.sources[0], last_success: '2026-09-26T02:30:00Z' }] }
    renderApp('/settings', { settings: view })
    const sources = await findPanel('Sources')
    expect(cards(sources)[0].textContent).toContain('· 22:30')
    expect(cards(sources)[0].textContent).not.toContain('02:30')
  })

  it('lists every source as a card with what it reads and its live status — never a token value', async () => {
    renderApp('/settings')
    const sources = await findPanel('Sources')
    expect(cards(sources)).toHaveLength(settingsFixture.sources.length)
    expect(sources.textContent).not.toMatch(/super-secret/i)
  })

  it('shows a command source’s program file name, never a machine path, its timing and its token name only', async () => {
    const view: SettingsView = {
      ...settingsFixture,
      sources: [
        { id: 'desk', label: 'Desk', kind: 'feed', reads: 'python.exe -m desk.feed', stale_after: '36h',
          refresh: '1m', timeout: 30, token_env: null, status: 'ok', last_success: settingsFixture.as_of, detail: '' },
        { id: 'api', label: 'API', kind: 'feed', reads: 'https://example.com/feed', stale_after: '15m',
          refresh: null, timeout: 5, token_env: 'KESTREL_DESK_TOKEN', status: 'error', last_success: null,
          detail: 'the feed answered 401' },
      ],
    }
    renderApp('/settings', { settings: view })
    const sources = await findPanel('Sources')
    const [desk, api] = cards(sources)
    expect(desk.textContent).toContain('python.exe -m desk.feed')
    expect(desk.textContent).toContain('stale after 36h · reuses for 1m · times out at 30s')
    expect(sources.textContent).not.toContain('C:\\') // never a machine path
    expect(api.textContent).toContain('token: KESTREL_DESK_TOKEN')
    expect(api.textContent).not.toMatch(/[a-z0-9_]{10,}TOKEN[a-z0-9_]*=/i) // no token value, only its name
    expect(api.textContent).toContain('never updated') // the never-synced source
    expect(api.textContent).toContain('the feed answered 401')
  })

  it('says so when there are no sources yet', async () => {
    renderApp('/settings', { settings: { ...settingsFixture, sources: [] } })
    const sources = await findPanel('Sources')
    expect(sources.textContent).toContain('No sources configured yet.')
  })

  it('reads dashes and slashes as words', () => {
    expect(readable('green-red')).toBe('Green / Red')
    expect(readable('system')).toBe('System')
  })

  it('says it is loading, and says so plainly when settings could not load', async () => {
    const { unmount } = renderApp('/settings', { settings: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading settings…')).toBeTruthy()
    unmount()
    renderApp('/settings', { settings: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Settings couldn’t load: network is off in tests')
  })
})
