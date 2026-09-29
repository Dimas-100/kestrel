// What every chart shares: its measured width, and a hovered index that the pointer and the keys both move.
import { type KeyboardEvent, useLayoutEffect, useRef, useState } from 'react'

/** A ref for the chart's wrapper and its current width (`fallback` until measured, and in jsdom). */
export function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(fallback)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth || fallback)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [fallback])
  return [ref, width] as const
}

/** The hovered item among `count`: null when none. ←/→ step, Home/End jump, Escape clears. An index only counts
 *  while it names a real item, so an empty chart has none and a refresh that shortens the data can't break it. */
export function useIndex(count: number) {
  const [hovered, setHovered] = useState<number | null>(null)
  const index = hovered != null && hovered >= 0 && hovered < count ? hovered : null
  const onKey = (event: KeyboardEvent<Element>) => {
    const last = count - 1
    const moves: Record<string, number> = {
      ArrowLeft: Math.max(0, (index ?? last) - 1),
      ArrowRight: Math.min(last, (index ?? last - 1) + 1),
      Home: 0,
      End: last,
    }
    if (event.key in moves) {
      event.preventDefault()
      setHovered(count > 0 ? moves[event.key] : null)
    } else if (event.key === 'Escape') setHovered(null)
  }
  return { index, set: setHovered, onKey }
}

/** A ref for a box that flexes to fill its panel, and its current height (`fallback` until measured, never below
 *  `floor`): lets a chart grow to the panel a taller neighbour stretched, instead of leaving a gap above it. */
export function useHeight<T extends HTMLElement>(fallback: number, floor = fallback) {
  const ref = useRef<T>(null)
  const [height, setHeight] = useState(fallback)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setHeight(Math.max(floor, el.clientHeight || fallback))
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [fallback, floor])
  return [ref, height] as const
}
