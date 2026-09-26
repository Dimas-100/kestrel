import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderApp, shellFixture } from '../test/renderApp'

describe('shell', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('greets by name in the profile time zone', async () => {
    renderApp('/')
    expect(await screen.findByText('Good evening,')).toBeTruthy() // 17:08 in New York
    expect(screen.getByText('Alex')).toBeTruthy()
  })

  it('lists every source and flags the stale one without relying on colour', async () => {
    renderApp('/')
    const sidebar = await screen.findByRole('complementary', { name: 'Sidebar' })
    expect(within(sidebar).getByText('Savings')).toBeTruthy()
    expect(within(sidebar).getByText('26h')).toBeTruthy()
    expect(within(sidebar).getAllByText('stale')).toHaveLength(1)
  })

  it('marks the current page and navigates', async () => {
    renderApp('/')
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    expect(within(nav).getByRole('link', { name: /Home/ }).getAttribute('aria-current')).toBe('page')
    fireEvent.click(within(nav).getByRole('link', { name: /Strategies/ }))
    expect(await screen.findByText(/Phase 3/)).toBeTruthy()
    expect(within(nav).getByRole('link', { name: /Strategies/ }).getAttribute('aria-current')).toBe('page')
  })

  it('themes the whole document from the profile, and the toggle flips it', async () => {
    renderApp('/', { shell: { ...shellFixture, app: { ...shellFixture.app, theme: 'light', accent: 'slate' } } })
    await screen.findByText('Alex')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(document.documentElement.dataset.accent).toBe('slate')
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    window.localStorage.clear()
  })

  it('opens and closes the phone drawer, keeping keyboard focus in step', async () => {
    const { container } = renderApp('/')
    const menu = await screen.findByRole('button', { name: 'Open menu' })
    const frame = container.querySelector('.shell') as HTMLElement
    const sidebar = screen.getByRole('complementary', { name: 'Sidebar' })
    expect(menu.getAttribute('aria-controls')).toBe(sidebar.id)
    expect(menu.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(menu)
    expect(menu.getAttribute('aria-expanded')).toBe('true')
    expect(frame.dataset.drawer).toBe('open')
    expect(sidebar.contains(document.activeElement)).toBe(true) // focus moved into the drawer
    fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' })
    expect(menu.getAttribute('aria-expanded')).toBe('false')
    expect(frame.dataset.drawer).toBe('closed')
    expect(document.activeElement).toBe(menu)
  })

  it('shows an unknown path as not found inside the shell', async () => {
    renderApp('/nowhere')
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
  })
})
