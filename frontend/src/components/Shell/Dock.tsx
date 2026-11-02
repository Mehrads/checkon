import { useNavigate, useRouterState } from "@tanstack/react-router"
import { ArrowUp, Plus } from "lucide-react"
import { type RefObject, useEffect, useRef, useState } from "react"

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

// How far under the panel's top edge a section's top counts as "here"
const READING_LINE = 120
const SHOW_TOP_BUTTON_AFTER = 320
// A jump's smooth scroll passes the sections in between; the tab that was clicked stays lit meanwhile
const JUMP_MS = 900

type Section = { label: string; element: HTMLElement }

function behavior(): ScrollBehavior {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? "auto"
    : "smooth"
}

/** The sections a page marks with `data-dock`, in page order, skipping any that are hidden, and the one being read.
 * Pages add and remove them as they go (results appear after a check), so this watches the panel's content. A page
 * that fits on screen has nothing to jump to, so it lists none. */
function useSections(scroller: RefObject<HTMLElement | null>) {
  const [sections, setSections] = useState<Section[]>([])
  const [active, setActive] = useState(0)
  const [scrolled, setScrolled] = useState(false)
  const [overflows, setOverflows] = useState(false)
  const jumping = useRef<ReturnType<typeof setTimeout>>(undefined)
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  // biome-ignore lint/correctness/useExhaustiveDependencies: a new page means new sections to read
  useEffect(() => {
    const root = scroller.current
    if (!root) return
    let frame = 0

    const update = () => {
      frame = 0
      // On the page, not in the markup: a page can reorder its sections (a report's link puts the check first)
      const found = [...root.querySelectorAll<HTMLElement>("[data-dock]")]
        .filter((element) => element.offsetParent !== null)
        .map((element) => ({
          label: element.dataset.dock ?? "",
          element,
          top: element.getBoundingClientRect().top,
        }))
        .sort((one, other) => one.top - other.top)
      setSections((previous) =>
        previous.length === found.length &&
        previous.every(
          (section, index) => section.element === found[index].element,
        )
          ? previous
          : found,
      )
      setScrolled(root.scrollTop > SHOW_TOP_BUTTON_AFTER)
      setOverflows(root.scrollHeight > root.clientHeight)
      if (jumping.current) return
      const line = root.getBoundingClientRect().top + READING_LINE
      const atEnd =
        root.scrollTop + root.clientHeight >= root.scrollHeight - 2 &&
        root.scrollTop > 0
      const above = found.filter((section) => section.top <= line)
      setActive(atEnd ? found.length - 1 : Math.max(above.length - 1, 0))
    }
    const schedule = () => {
      frame ||= requestAnimationFrame(update)
    }

    update()
    root.addEventListener("scroll", schedule, { passive: true })
    const changes = new MutationObserver(schedule)
    changes.observe(root, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["data-dock", "hidden"],
    })
    const sizes = new ResizeObserver(schedule)
    sizes.observe(root)
    if (root.firstElementChild) sizes.observe(root.firstElementChild)
    return () => {
      cancelAnimationFrame(frame)
      root.removeEventListener("scroll", schedule)
      changes.disconnect()
      sizes.disconnect()
    }
  }, [scroller, pathname])

  const jump = (index: number) => {
    setActive(index)
    clearTimeout(jumping.current)
    jumping.current = setTimeout(() => {
      jumping.current = undefined
      // Someone may have scrolled on during the jump
      scroller.current?.dispatchEvent(new Event("scroll"))
    }, JUMP_MS)
    sections[index].element.scrollIntoView({
      behavior: behavior(),
      block: "start",
    })
  }
  return { sections: overflows ? sections : [], active, scrolled, jump }
}

function RoundButton({
  label,
  onClick,
  className,
  children,
}: {
  label: string
  onClick: () => void
  className?: string
  children: React.ReactNode
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={label}
          onClick={onClick}
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-full outline-none transition-colors focus-visible:ring-2 focus-visible:ring-white/80",
            className,
          )}
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={10}>
        {label}
      </TooltipContent>
    </Tooltip>
  )
}

/** The pill at the bottom of the frame: a tab for each section of the page, lit for the one on screen, then back to
 * the top and a new check, whichever page you're on. It's the one place to move around a long page. */
export function Dock({
  scroller,
}: {
  scroller: RefObject<HTMLElement | null>
}) {
  const navigate = useNavigate()
  const { sections, active, scrolled, jump } = useSections(scroller)
  const tabs = useRef<HTMLUListElement>(null)

  // On a phone the tabs can run past the dock's width: the lit one stays in sight
  useEffect(() => {
    const list = tabs.current
    const tab = list?.children[active] as HTMLElement | undefined
    if (!list || !tab) return
    list.scrollTo({
      left: tab.offsetLeft - (list.clientWidth - tab.offsetWidth) / 2,
      behavior: behavior(),
    })
  }, [active])

  const newCheck = async () => {
    if (window.location.pathname !== "/") await navigate({ to: "/" })
    const box = document.querySelector<HTMLElement>("#posting, #posting-link")
    box?.closest("section")?.scrollIntoView({
      behavior: behavior(),
      block: "start",
    })
    box?.focus({ preventScroll: true })
  }

  return (
    <nav
      aria-label="On this page"
      className="glass-bar absolute bottom-3 left-1/2 z-20 flex max-w-[calc(100%-1.5rem)] -translate-x-1/2 items-center gap-1 rounded-full p-1 md:bottom-2"
    >
      {sections.length > 1 && (
        <ul
          ref={tabs}
          className="relative flex min-w-0 items-center gap-0.5 overflow-x-auto no-scrollbar"
        >
          {sections.map((section, index) => (
            <li key={section.label} className="shrink-0">
              <button
                type="button"
                aria-current={index === active ? "true" : undefined}
                onClick={() => jump(index)}
                className={cn(
                  "h-9 rounded-full px-2.5 text-sm font-medium whitespace-nowrap outline-none transition-colors focus-visible:ring-2 focus-visible:ring-white/80 sm:px-3.5",
                  index === active
                    ? "bg-solid text-on-solid shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {section.label}
              </button>
            </li>
          ))}
        </ul>
      )}
      {scrolled && (
        <RoundButton
          label="Back to the top"
          onClick={() =>
            scroller.current?.scrollTo({ top: 0, behavior: behavior() })
          }
          className="bg-white/15 text-foreground hover:bg-white/25"
        >
          <ArrowUp className="size-4.5" aria-hidden="true" />
        </RoundButton>
      )}
      <RoundButton
        label="Check a posting"
        onClick={newCheck}
        className="bg-solid text-on-solid hover:bg-solid/85"
      >
        <Plus className="size-4.5" aria-hidden="true" />
      </RoundButton>
    </nav>
  )
}
