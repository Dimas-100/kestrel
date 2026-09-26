import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderApp, strategiesFixture } from '../../test/renderApp'
import { chipText, verdictText } from './Strategies'

describe('Strategies', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows a card per strategy with its books, its band and a way in', async () => {
    renderApp('/strategies')
    expect(await screen.findByRole('heading', { level: 1, name: 'Strategies' })).toBeTruthy()
    expect(screen.getByText('How each strategy trades, and whether it is behaving the way its backtest said it would.'))
      .toBeTruthy()
    const cards = screen.getAllByRole('article')
    expect(cards).toHaveLength(4)
    const rsi2 = within(cards[0])
    expect(rsi2.getByRole('heading', { name: 'Mean reversion' })).toBeTruthy()
    expect(rsi2.getByText('Real · running · 4 open')).toBeTruthy()
    expect(rsi2.getByText('Paper · running · 5 open')).toBeTruthy()
    expect(cards[0].textContent).toContain('In band · ▲ up +0.79%')
    expect(rsi2.getByText('Per trade vs expected · real book')).toBeTruthy()
    expect(rsi2.getByText('34 closed trades')).toBeTruthy()
    expect(rsi2.getByRole('link', { name: 'Open Mean reversion' }).getAttribute('href')).toBe('/strategies/rsi2')
  })

  it('words the verdict the way Home does', () => {
    const [rsi2, ibs, leader] = strategiesFixture.strategies
    expect(verdictText(ibs)).toBe('Too early · 7 trades')
    expect(verdictText(leader)).toBe('Below band')
    expect(verdictText(rsi2)).toBe('In band')
    expect(verdictText({ ...ibs, verdict: 'none', trades: 0 })).toBe('No closed trades yet')
    expect(verdictText({ ...ibs, verdict: 'none', trades: 3 })).toBe('No backtest to compare with')
    expect(chipText(rsi2.books[1])).toBe('Paper · running · 5 open')
  })

  it('says so when there are no strategies yet', async () => {
    renderApp('/strategies', { strategies: { strategies: [] } })
    expect(await screen.findByText('No strategies yet.')).toBeTruthy()
  })

  it('says it is loading while the list is on its way', async () => {
    renderApp('/strategies', { strategies: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading strategies…')).toBeTruthy()
  })

  it('says so when the list could not load', async () => {
    renderApp('/strategies', { strategies: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Strategies couldn’t load: network is off in tests')
  })
})
