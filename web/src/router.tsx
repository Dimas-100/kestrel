import { createRootRoute, createRoute, createRouter, type RouterHistory } from '@tanstack/react-router'
import { Home } from './pages/home/Home'
import { Soon } from './pages/Soon'
import { Strategies } from './pages/strategies/Strategies'
import { Shell } from './shell/Shell'

const root = createRootRoute({
  component: Shell,
  notFoundComponent: () => <Soon title="Not found" text="There is no page here. Pick one from the menu." />,
})

const later = (path: string, title: string, text: string) =>
  createRoute({ getParentRoute: () => root, path, component: () => <Soon title={title} text={text} /> })

const routeTree = root.addChildren([
  createRoute({ getParentRoute: () => root, path: '/', component: Home }),
  later('/accounts', 'Accounts', 'Every account, what it holds, and how much of its growth was your deposits — Phase 4.'),
  later('/books', 'Books', 'Each book, real or paper: equity against its benchmark, drawdown, trades — Phase 3.'),
  createRoute({ getParentRoute: () => root, path: '/strategies', component: Strategies }),
  later('/backtests', 'Backtests', 'What has been tested and what passed — Phase 5.'),
  later('/activity', 'Activity', 'What ran, what is due, what failed — Phase 5.'),
  later('/settings', 'Settings', 'Your profile and the status of every source — Phase 5.'),
])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, history, defaultPreload: 'intent' })
}
