import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { bookFixture, renderApp } from '../../test/renderApp'

describe('Book', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders the header, equity, scorecard, positions and trades', async () => {
    renderApp('/books/rsi2-real')
    expect(await screen.findByRole('heading', { level: 1, name: 'Mean reversion' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Mean reversion' }).getAttribute('href')).toBe('/strategies/rsi2')
    expect(screen.getByRole('heading', { name: 'Equity' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Scorecard' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Open positions' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'All trades' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Runs' })).toBeTruthy()
    // a missing stop is flagged in words, not colour alone
    expect(screen.getByText('No stop')).toBeTruthy()
    expect(screen.getAllByText(`${bookFixture.trades.length} closed trades`)).toHaveLength(2) // scorecard + trades table
  })

  it('says it is loading while the book is on its way', async () => {
    renderApp('/books/rsi2-real', { book: [] }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading the book…')).toBeTruthy()
  })

  it('shows Not found for an unknown book', async () => {
    const answer = () => Promise.resolve(new Response('{"detail":"no such book: nope"}', { status: 404 }))
    renderApp('/books/nope', {}, answer)
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
  })

  it('says so when the book could not load', async () => {
    renderApp('/books/rsi2-real', { book: [] }, () =>
      Promise.resolve(new Response('oops', { status: 500, statusText: 'Server error' })))
    expect((await screen.findByRole('alert')).textContent).toContain('couldn’t load')
  })
})
