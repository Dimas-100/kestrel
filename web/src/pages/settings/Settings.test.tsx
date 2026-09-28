import { screen, waitFor } from '@testing-library/react'
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
const rows = (region: HTMLElement) => [...region.querySelectorAll('tbody tr')].map((r) => r.textContent)

describe('Settings', { timeout: 15_000 }, () => {
  it('shows who you are and how the app looks', async () => {
    renderApp('/settings')
    await screen.findByRole('heading', { level: 1, name: 'Settings' })
    const you = await findPanel('You and the look')
    expect(you.textContent).toContain(`Name${settingsFixture.you.name}`)
    expect(you.textContent).toContain(`Theme${readable(settingsFixture.app.theme)}`)
    expect(you.textContent).toContain(`Currency${settingsFixture.app.currency}`)
    expect(you.textContent).toContain(`Time zone${settingsFixture.app.timezone}`)
  })

  it('shows the benchmark, the profile in use, and the versions', async () => {
    renderApp('/settings')
    const about = await findPanel('Benchmark and version')
    expect(about.textContent).toContain(`${settingsFixture.benchmark.symbol} · ${settingsFixture.benchmark.label}`)
    expect(about.textContent).toContain(`Profile${settingsFixture.profile}`)
    expect(about.textContent).toContain(`Contract version${settingsFixture.contract_version}`)
    expect(about.textContent).toContain(`kestrel version${settingsFixture.version}`)
  })

  it('shows a source’s last success in the profile’s time zone, not UTC', async () => {
    // 02:30 UTC on the 26th is 22:30 on the 25th in New York, the fixture profile's zone
    expect(settingsFixture.app.timezone).toBe('America/New_York')
    const view: SettingsView = { ...settingsFixture,
      sources: [{ ...settingsFixture.sources[0], last_success: '2026-09-26T02:30:00Z' }] }
    renderApp('/settings', { settings: view })
    const sources = await findPanel('Sources')
    expect(rows(sources)[0]).toContain('· 22:30')
    expect(rows(sources)[0]).not.toContain('02:30')
  })

  it('lists every source, what it reads, and its live status — never a token value', async () => {
    renderApp('/settings')
    const sources = await findPanel('Sources')
    expect(rows(sources)).toHaveLength(settingsFixture.sources.length)
    expect(sources.textContent).not.toMatch(/super-secret/i)
  })

  it('shows a command sources program file name, never a machine path, and its token name only', async () => {
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
    expect(rows(sources)[0]).toContain('python.exe -m desk.feed')
    expect(sources.textContent).not.toContain('C:\\') // never a machine path
    expect(rows(sources)[1]).toContain('token: KESTREL_DESK_TOKEN')
    expect(rows(sources)[1]).not.toMatch(/[a-z0-9_]{10,}TOKEN[a-z0-9_]*=/i) // no token value, only its name
    expect(sources.textContent).toContain('never') // the never-synced row's last success
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
