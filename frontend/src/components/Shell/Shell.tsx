import { useRouterState } from "@tanstack/react-router"
import { type ReactNode, useEffect, useRef } from "react"

import { Footer } from "@/components/Common/Footer"
import { Dock } from "./Dock"
import { Rail } from "./Rail"
import { TopBar } from "./TopBar"

/** The signed-in frame: a photo, and over it the top bar, the rail and the dock, which stay put, and one frosted
 * panel whose content is the only thing that scrolls. Tall pages use the dock; nothing scrolls inside the panel. */
export function Shell({ children }: { children: ReactNode }) {
  const scroller = useRef<HTMLElement>(null)
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  // Space, Page Down, Home and End only reach a scrolling panel that has focus. Each page gives it focus, unless
  // something on the page already took it.
  // biome-ignore lint/correctness/useExhaustiveDependencies: runs once per page
  useEffect(() => {
    if (document.activeElement === document.body)
      scroller.current?.focus({ preventScroll: true })
  }, [pathname])

  return (
    <div className="app-shell relative h-dvh overflow-hidden">
      <div className="app-photo absolute inset-0" aria-hidden="true" />
      <TopBar />
      <Rail />
      <div className="glass-panel absolute inset-x-2 top-16 bottom-2 z-10 overflow-hidden rounded-3xl md:inset-x-(--shell-x) md:top-[4.5rem] md:bottom-6 md:rounded-[2rem]">
        <main
          ref={scroller}
          id="app-scroll"
          data-scroll-restoration-id="app-scroll"
          tabIndex={-1}
          className="app-scroll h-full overflow-x-hidden overflow-y-auto outline-none"
        >
          <div
            key={pathname}
            className="mx-auto max-w-[90rem] animate-in fade-in-0 slide-in-from-bottom-1 px-3 pt-4 pb-4 duration-300 motion-reduce:animate-none sm:px-5 md:pt-7 md:pr-8 md:pl-12"
          >
            {children}
          </div>
          <Footer />
        </main>
      </div>
      <Dock scroller={scroller} />
    </div>
  )
}
