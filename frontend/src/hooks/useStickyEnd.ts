import { useEffect, useRef } from "react"

const TOP_GAP = 20
const DOCK_GAP = 80 // clears the dock at the bottom of the panel

/** For a column beside a longer one (with `sticky`): it scrolls until its end is on screen, then stays there, so its
 * last lines, such as an Apply button, stay in reach while the other column is read. A column shorter than the panel
 * stays at the top instead. Does nothing outside the signed-in panel. */
export function useStickyEnd<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const element = ref.current
    const panel = element?.closest("#app-scroll")
    if (!element || !panel) return
    const fit = () => {
      const room = panel.clientHeight - element.offsetHeight - DOCK_GAP
      element.style.top = `${Math.min(TOP_GAP, room)}px`
    }
    const sizes = new ResizeObserver(fit)
    sizes.observe(element)
    sizes.observe(panel)
    return () => sizes.disconnect()
  }, [])
  return ref
}
