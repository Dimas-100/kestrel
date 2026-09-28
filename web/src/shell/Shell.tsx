// The frame around every page: sidebar (greeting, navigation, sources), top bar, phone tab bar.
import { useQueryClient } from '@tanstack/react-query'
import { Link, Outlet, useRouterState } from '@tanstack/react-router'
import { type Ref, useEffect, useRef, useState } from 'react'
import { Icon, type IconName, Mark } from '../components/Icon'
import { type ShellView, type Source, useShell } from '../lib/api'
import { ago, setCurrency, timeHM } from '../lib/format'
import { clockLine, greeting } from '../lib/greeting'
import { useTheme } from '../lib/theme'

type CountKey = keyof ShellView['counts']
interface NavItem { to: string; label: string; icon: IconName; count?: CountKey }

export const NAV: { group: string; items: NavItem[] }[] = [
  { group: 'Overview', items: [{ to: '/', label: 'Home', icon: 'home' }] },
  {
    group: 'Money',
    items: [
      { to: '/accounts', label: 'Accounts', icon: 'accounts', count: 'accounts' },
      { to: '/plan', label: 'Plan', icon: 'target' },
      { to: '/reserves', label: 'Reserves', icon: 'scale' },
    ],
  },
  {
    group: 'Trading',
    items: [
      { to: '/books', label: 'Books', icon: 'books', count: 'books' },
      { to: '/strategies', label: 'Strategies', icon: 'strategy', count: 'strategies' },
    ],
  },
  {
    group: 'Research',
    items: [
      { to: '/backtests', label: 'Backtests', icon: 'backtests' },
      { to: '/calendar', label: 'Calendar', icon: 'calendar' },
    ],
  },
  {
    group: 'System',
    items: [
      { to: '/activity', label: 'Activity', icon: 'activity' },
      { to: '/settings', label: 'Settings', icon: 'settings' },
    ],
  },
]

const SIDEBAR_ID = 'sidebar'

const TABS: NavItem[] = [
  { to: '/', label: 'Home', icon: 'home' },
  { to: '/accounts', label: 'Accounts', icon: 'accounts' },
  { to: '/books', label: 'Books', icon: 'books' },
  { to: '/strategies', label: 'Strategies', icon: 'strategy' },
  { to: '/settings', label: 'More', icon: 'more' },
]

/** The breadcrumb for a path: its section and page. A page inside a section (/strategies/rsi2) keeps the section's
 *  crumb, as a link back to the section (`parent`). */
export function crumbs(pathname: string): { group: string; page: string; parent: string | null } {
  for (const { group, items } of NAV) {
    const item = items.find((i) => i.to === pathname || (i.to !== '/' && pathname.startsWith(`${i.to}/`)))
    if (item) return { group, page: item.label, parent: item.to === pathname ? null : item.to }
  }
  return { group: 'kestrel', page: 'Not found', parent: null }
}

export const STATUS_ICON: Record<Source['status'], { name: IconName; color: string; text: string }> = {
  ok: { name: 'checkCircle', color: 'var(--good)', text: 'up to date' },
  stale: { name: 'clock', color: 'var(--warn)', text: 'stale' },
  error: { name: 'alert', color: 'var(--serious)', text: 'error' },
}

function SourceRow({ source, now }: { source: Source; now: Date }) {
  const status = STATUS_ICON[source.status]
  return (
    <div className="flex items-center gap-2.5 h-7 text-xs" title={source.detail || undefined}>
      <Icon name={status.name} size={14} style={{ color: status.color }} />
      <span className="text-ink2">{source.label}</span>
      <span className="text-ink3 text-[11px] truncate">{source.kind}</span>
      <span className="sr-only">{status.text}</span>
      <span className="num ml-auto text-[11px]" style={{ color: source.status === 'ok' ? 'var(--ink3)' : status.color }}>
        {ago(source.last_success, now)}
      </span>
    </div>
  )
}

function Sidebar({ shell, ref }: { shell?: ShellView; ref: Ref<HTMLElement> }) {
  const now = shell ? new Date(shell.now) : null
  const tz = shell?.app.timezone ?? 'UTC'
  return (
    <aside className="sidebar" id={SIDEBAR_ID} aria-label="Sidebar" ref={ref}>
      <div className="flex items-center gap-2.5 px-1.5 h-9">
        <Mark />
        <span className="text-base font-semibold tracking-tight">{shell?.app.name ?? 'kestrel'}</span>
      </div>
      <div className="px-2 pt-6 pb-2">
        <div className="text-[13px] text-ink3">{now ? `${greeting(now, tz)},` : ' '}</div>
        <div className="text-[26px] font-semibold tracking-[-0.03em] mt-0.5">{shell?.name ?? ' '}</div>
        <div className="num text-[11px] text-ink3 mt-1.5">{now ? clockLine(now, tz) : ' '}</div>
      </div>
      <nav aria-label="Main" className="flex flex-col gap-0.5">
        {NAV.map(({ group, items }) => (
          <div key={group} className="flex flex-col gap-0.5">
            <div className="label px-2.5 pt-4 pb-1.5">{group}</div>
            {items.map((item) => (
              <Link key={item.to} to={item.to} className="nav-item ease"
                activeOptions={{ exact: item.to === '/' }} activeProps={{ 'aria-current': 'page' }}>
                <Icon name={item.icon} size={17} />
                <span>{item.label}</span>
                {item.count && shell && <span className="num ml-auto text-[11px] text-ink3">{shell.counts[item.count]}</span>}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="mt-auto border-t border-line pt-3.5 px-1.5">
        <div className="label mb-1.5">Sources</div>
        {now && shell?.sources.map((s) => <SourceRow key={s.id} source={s} now={now} />)}
      </div>
    </aside>
  )
}

function TopBar({ pathname, shell, theme, onToggleTheme, onMenu, menuOpen, menuRef }: {
  pathname: string; shell?: ShellView; theme: 'dark' | 'light'; onToggleTheme: () => void; onMenu: () => void
  menuOpen: boolean; menuRef: Ref<HTMLButtonElement>
}) {
  const client = useQueryClient()
  const { group, page, parent } = crumbs(pathname)
  return (
    <header className="topbar">
      <button type="button" className="icon-btn menu-btn" aria-label="Open menu" onClick={onMenu} ref={menuRef}
        aria-expanded={menuOpen} aria-controls={SIDEBAR_ID}>
        <Icon name="menu" size={18} />
      </button>
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-[13px]">
        <span className="text-ink3 hide-narrow">{group}</span>
        <Icon name="chevron" size={14} style={{ color: 'var(--ink3)' }} />
        {parent ? <Link to={parent} className="font-medium">{page}</Link> : <span className="font-medium">{page}</span>}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        {shell && (
          <span className="text-xs text-ink3 hide-narrow">Updated {timeHM(shell.now, shell.app.timezone)}</span>
        )}
        <button type="button" className="icon-btn" aria-label="Refresh data" onClick={() => client.invalidateQueries()}>
          <Icon name="refresh" size={16} />
        </button>
        <button type="button" className="icon-btn" onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={16} />
        </button>
      </div>
    </header>
  )
}

function TabBar() {
  return (
    <nav className="tabbar" aria-label="Tabs">
      {TABS.map((tab) => (
        <Link key={tab.to} to={tab.to} activeOptions={{ exact: tab.to === '/' }} activeProps={{ 'aria-current': 'page' }}
          className="flex flex-col items-center justify-center gap-1 min-h-12 text-[11px] font-medium text-ink3 aria-[current=page]:text-ink1">
          <Icon name={tab.icon} size={20} />
          {tab.label}
        </Link>
      ))}
    </nav>
  )
}

export function Shell() {
  const shell = useShell()
  const app = shell.data?.app
  const [theme, toggleTheme] = useTheme(app?.theme ?? 'system')
  const [drawer, setDrawer] = useState(false)
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const menuRef = useRef<HTMLButtonElement>(null)
  const sidebarRef = useRef<HTMLElement>(null)
  const drawerWasOpen = useRef(false)

  // during render, not in an effect: the page below renders after this line and must format in this currency
  // from its first paint (setCurrency is idempotent)
  if (app) setCurrency(app.currency)

  useEffect(() => setDrawer(false), [pathname]) // navigating closes the phone drawer
  useEffect(() => {
    document.title = app?.name ?? 'kestrel'
  }, [app])
  useEffect(() => {
    // opening the drawer moves focus into it; closing hands focus back to the menu button; Escape closes it
    if (drawer) sidebarRef.current?.querySelector<HTMLElement>('nav a')?.focus()
    else if (drawerWasOpen.current) menuRef.current?.focus()
    drawerWasOpen.current = drawer
    if (!drawer) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setDrawer(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [drawer])
  useEffect(() => {
    // theme the whole document so overscroll and scrollbars match
    const root = document.documentElement
    root.classList.add('k')
    root.dataset.theme = theme
    root.dataset.accent = app?.accent ?? 'rufous'
    root.dataset.gl = app?.gain_loss ?? 'green-red'
    root.dataset.density = app?.density ?? 'comfortable'
  }, [theme, app])

  return (
    <div className="shell" data-drawer={drawer ? 'open' : 'closed'}>
      <Sidebar shell={shell.data} ref={sidebarRef} />
      <div className="scrim" aria-hidden="true" onClick={() => setDrawer(false)} />
      <div className="main">
        <TopBar pathname={pathname} shell={shell.data} theme={theme} onToggleTheme={toggleTheme}
          onMenu={() => setDrawer(true)} menuOpen={drawer} menuRef={menuRef} />
        <main className="content" id="main">
          {shell.isError && (
            <div role="alert" className="panel mb-4" style={{ borderColor: 'var(--serious)' }}>
              kestrel&rsquo;s server didn&rsquo;t answer. Is <code>kestrel serve</code> running?
            </div>
          )}
          {/* pages wait for the profile's settings (currency, time zone) so they never paint with the defaults */}
          {shell.data || shell.isError ? <Outlet /> : <p className="text-ink3" role="status">Loading…</p>}
        </main>
      </div>
      <TabBar />
    </div>
  )
}
