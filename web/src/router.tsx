import { createRootRoute, createRoute, createRouter, type RouterHistory, useNavigate } from '@tanstack/react-router'
import type { Money } from './lib/api'
import { Account } from './pages/account/Account'
import { Accounts } from './pages/accounts/Accounts'
import { Activity } from './pages/activity/Activity'
import { Backtests } from './pages/backtests/Backtests'
import { Book } from './pages/book/Book'
import { Books } from './pages/books/Books'
import { Calendar } from './pages/calendar/Calendar'
import { Home } from './pages/home/Home'
import { Soon } from './pages/Soon'
import { Settings } from './pages/settings/Settings'
import { Strategies } from './pages/strategies/Strategies'
import { Strategy } from './pages/strategy/Strategy'
import { Shell } from './shell/Shell'

const root = createRootRoute({
  component: Shell,
  notFoundComponent: () => <Soon title="Not found" text="There is no page here. Pick one from the menu." />,
})

/** `?book=real|paper` picks the money the page focuses on; anything else is dropped (the page defaults to real). */
function bookSearch(search: Record<string, unknown>): { book?: Money } {
  return search.book === 'real' || search.book === 'paper' ? { book: search.book } : {}
}

const accountRoute = createRoute({
  getParentRoute: () => root,
  path: '/accounts/$accountId',
  component: AccountRoute,
})

function AccountRoute() {
  const { accountId } = accountRoute.useParams()
  return <Account key={accountId} id={accountId} /> // another account starts on its own default window
}

const bookRoute = createRoute({
  getParentRoute: () => root,
  path: '/books/$bookId',
  component: BookRoute,
})

function BookRoute() {
  const { bookId } = bookRoute.useParams()
  return <Book key={bookId} id={bookId} />
}

const strategyRoute = createRoute({
  getParentRoute: () => root,
  path: '/strategies/$strategyId',
  validateSearch: bookSearch,
  component: StrategyRoute,
})

function StrategyRoute() {
  const { strategyId } = strategyRoute.useParams()
  const { book } = strategyRoute.useSearch()
  const navigate = useNavigate()
  return (
    <Strategy id={strategyId} book={book ?? 'real'}
      onBook={(next) => navigate({ to: '/strategies/$strategyId', params: { strategyId }, search: { book: next } })} />
  )
}

const routeTree = root.addChildren([
  createRoute({ getParentRoute: () => root, path: '/', component: Home }),
  createRoute({ getParentRoute: () => root, path: '/accounts', component: Accounts }),
  accountRoute,
  createRoute({ getParentRoute: () => root, path: '/books', component: Books }),
  bookRoute,
  createRoute({ getParentRoute: () => root, path: '/strategies', component: Strategies }),
  strategyRoute,
  createRoute({ getParentRoute: () => root, path: '/backtests', component: Backtests }),
  createRoute({ getParentRoute: () => root, path: '/calendar', component: Calendar }),
  createRoute({ getParentRoute: () => root, path: '/activity', component: Activity }),
  createRoute({ getParentRoute: () => root, path: '/settings', component: Settings }),
])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, history, defaultPreload: 'intent' })
}
