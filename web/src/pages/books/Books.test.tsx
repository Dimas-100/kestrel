import { screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { booksFixture, renderApp } from '../../test/renderApp'

describe('Books', { timeout: 15_000 }, () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lists real books first, then paper, with totals and a sparkline, and links to the book', async () => {
    renderApp('/books')
    expect(await screen.findByRole('heading', { level: 1, name: 'Books' })).toBeTruthy()
    expect(screen.getByText(/^Real \$18,467\.71 · Paper \$269,609\.85 · equity is the money each book works with/))
      .toBeTruthy()
    const rows = screen.getAllByRole('row').slice(1) // drop the header row
    expect(rows).toHaveLength(booksFixture.rows.length)
    const first = within(rows[0])
    expect(first.getByText('Mean reversion')).toBeTruthy()
    // equity and invested side by side, the same two figures on every book, and the basis the return rests on
    const headers = screen.getAllByRole('columnheader').map((h) => h.textContent)
    expect(headers.slice(3, 6)).toEqual(['Equity', 'Invested', 'Since start'])
    expect(rows[0].textContent).toContain('$18,467.71$12,004.20')
    expect(rows[0].textContent).toContain("on The trading account's value")
    expect(rows[2].textContent).toContain('$3,200.00$877.54') // the IBS book: its $3,200 book, $878 of it invested
    expect(first.getByRole('link', { name: 'Mean reversion' }).getAttribute('href')).toBe('/books/rsi2-real')
    expect(first.getByRole('img', { name: /(up|down) since it started/ })).toBeTruthy()
    expect(within(rows[1]).getByText('PAPER')).toBeTruthy() // the second row is the first paper book
  })

  it('colours the sparkline by the return since the book started, not by where the line ends', async () => {
    // a line that ends above where it starts, on a book that is down since it started: down, in words and colour
    const row = { ...booksFixture.rows[0], since_pct: -3.42, spark: [-6.18, -5.02, -3.42] }
    renderApp('/books', { books: { ...booksFixture, rows: [row] } })
    const spark = await screen.findByRole('img', { name: 'down since it started' })
    expect(spark.querySelector('path')?.getAttribute('stroke')).toBe('var(--down)')
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
