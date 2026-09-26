// @vitest-environment node
// Design-system rules that code review keeps missing, pinned as tests (docs/design-system.md).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const SRC = fileURLToPath(new URL('..', import.meta.url))

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? files(path) : [path]
  })
}

describe('design rules', () => {
  it('components use tokens, never raw hex colours', () => {
    const offenders = files(SRC)
      .filter((f) => /\.tsx?$/.test(f) && !f.endsWith('.test.ts') && !f.endsWith('.test.tsx'))
      .filter((f) => /#[0-9a-fA-F]{3,8}\b/.test(readFileSync(f, 'utf8')))
    expect(offenders).toEqual([])
  })

  it('keeps screen-reader labels inside scrolling tables (no sideways page scroll on phones)', () => {
    const css = readFileSync(join(SRC, 'styles', 'tokens.css'), 'utf8')
    expect(css).toMatch(/\.table-scroll \{ position: relative;/)
    expect(css).toMatch(/\.panel \{ position: relative;/)
  })
})
