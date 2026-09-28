import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderApp, shellFixture } from '../test/renderApp'
import { crumbs, NAV } from './Shell'

const MORE_LABELS = ['Plan', 'Reserves', 'Backtests', 'Calendar', 'Activity', 'Settings']

describe('shell', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders real content for every NAV entry (no Soon placeholder left)', async () => {
    for (const { items } of NAV) {
      for (const item of items) {
        const { unmount } = renderApp(item.to)
        expect(await screen.findByRole('heading', { level: 1, name: item.label })).toBeTruthy()
        expect(screen.queryByText('There is no page here. Pick one from the menu.')).toBeNull()
        unmount()
      }
    }
  })

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
    expect(await screen.findByRole('heading', { level: 1, name: 'Strategies' })).toBeTruthy()
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

  it('keeps the section in the breadcrumb on a page inside it', () => {
    expect(crumbs('/strategies')).toEqual({ group: 'Trading', page: 'Strategies', parent: null })
    expect(crumbs('/strategies/rsi2')).toEqual({ group: 'Trading', page: 'Strategies', parent: '/strategies' })
    expect(crumbs('/books')).toEqual({ group: 'Trading', page: 'Books', parent: null })
    expect(crumbs('/books/rsi2-real')).toEqual({ group: 'Trading', page: 'Books', parent: '/books' })
    expect(crumbs('/nowhere')).toEqual({ group: 'kestrel', page: 'Not found', parent: null })
  })

  it('shows an unknown path as not found inside the shell', async () => {
    renderApp('/nowhere')
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
  })

  it('shows a breadcrumb back to Books on a book page', async () => {
    renderApp('/books/rsi2-real')
    const crumb = await screen.findByRole('navigation', { name: 'Breadcrumb' })
    expect(within(crumb).getByRole('link', { name: 'Books' })).toBeTruthy()
  })

  it('opens the phone "More" sheet listing the rest of the nav, keyboard- and screen-reader-friendly', async () => {
    renderApp('/')
    const trigger = await screen.findByRole('button', { name: 'More' })
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(trigger)
    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    const sheet = screen.getByRole('dialog', { name: 'More' })
    for (const label of MORE_LABELS) {
      expect(within(sheet).getByRole('link', { name: label })).toBeTruthy()
    }
    expect(sheet.contains(document.activeElement)).toBe(true) // focus moved into the sheet

    // Tab from the last focusable element wraps back to the first
    const focusable = within(sheet).getAllByRole('button').concat(within(sheet).getAllByRole('link'))
    focusable[focusable.length - 1].focus()
    fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Tab' })
    expect(document.activeElement).toBe(focusable[0])

    fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' })
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(trigger)
  })

  it('closes the "More" sheet by clicking its scrim', async () => {
    const { container } = renderApp('/')
    fireEvent.click(await screen.findByRole('button', { name: 'More' }))
    expect(screen.getByRole('dialog', { name: 'More' })).toBeTruthy()
    fireEvent.click(container.querySelector('.sheet-scrim') as HTMLElement)
    expect(screen.queryByRole('dialog', { name: 'More' })).toBeNull()
  })

  it('closes the "More" sheet on navigating to one of its pages', async () => {
    renderApp('/')
    fireEvent.click(await screen.findByRole('button', { name: 'More' }))
    const sheet = screen.getByRole('dialog', { name: 'More' })
    fireEvent.click(within(sheet).getByRole('link', { name: 'Plan' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Plan' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'More' }).getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('dialog', { name: 'More' })).toBeNull()
  })
})
