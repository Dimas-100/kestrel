import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { booksFixture, renderApp } from '../../test/renderApp'

describe('Books', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists real books first, then paper, with totals and a sparkline, and links to the book', async () => {
    renderApp('/books')
    expect(await screen.findByRole('heading', { level: 1, name: 'Books' })).toBeTruthy()
    expect(screen.getByText('Real $18,467.71 · Paper $269,609.85')).toBeTruthy()
    const rows = screen.getAllByRole('row').slice(1) // drop the header row
    expect(rows).toHaveLength(booksFixture.rows.length)
    const first = within(rows[0])
    expect(first.getByText('Mean reversion')).toBeTruthy()
    expect(first.getByRole('link', { name: 'Mean reversion' }).getAttribute('href')).toBe('/books/rsi2-real')
    expect(first.getByRole('img', { name: /trending (up|down)/ })).toBeTruthy()
    expect(within(rows[1]).getByText('PAPER')).toBeTruthy() // the second row is the first paper book
  })

  it('says so when there are no books yet', async () => {
    renderApp('/books', { books: { as_of: booksFixture.as_of, real_value: 0, paper_value: 0, rows: [] } })
    expect(await screen.findByText('No books yet. A book appears once a trading feed reports one.')).toBeTruthy()
  })

  it('says it is loading while the list is on its way', async () => {
    renderApp('/books', { books: null }, () => new Promise<Response>(() => {}))
    expect(await screen.findByText('Loading books…')).toBeTruthy()
  })

  it('says so when the list could not load', async () => {
    renderApp('/books', { books: null })
    expect((await screen.findByRole('alert')).textContent).toBe('Books couldn’t load: network is off in tests')
  })
})
