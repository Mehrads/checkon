import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

const BASE = "/assets/images/landing"

interface PhotoProps {
  /** File stem in public/assets/images/landing: `<name>-<width>.avif` and `.webp` */
  name: string
  widths: number[]
  /** Intrinsic size of the largest file, so the browser reserves the space */
  width: number
  height: number
  sizes: string
  alt: string
  className?: string
}

/** A photo or screenshot as AVIF with a WebP fallback, sized by `srcset` and loaded lazily. */
export function Photo({
  name,
  widths,
  width,
  height,
  sizes,
  alt,
  className,
}: PhotoProps) {
  const set = (ext: string) =>
    widths.map((w) => `${BASE}/${name}-${w}.${ext} ${w}w`).join(", ")
  return (
    <picture className="contents">
      <source type="image/avif" srcSet={set("avif")} sizes={sizes} />
      <img
        src={`${BASE}/${name}-${widths[widths.length - 1]}.webp`}
        srcSet={set("webp")}
        sizes={sizes}
        width={width}
        height={height}
        alt={alt}
        loading="lazy"
        decoding="async"
        className={className}
      />
    </picture>
  )
}

/** A capture of the checker in both themes; only the one for the current theme loads. */
export function Screenshot({ name, className, ...props }: PhotoProps) {
  return (
    <>
      <Photo
        name={`${name}-light`}
        className={cn("block h-auto w-full dark:hidden", className)}
        {...props}
      />
      <Photo
        name={`${name}-dark`}
        className={cn("hidden h-auto w-full dark:block", className)}
        {...props}
      />
    </>
  )
}

/** A plain browser window around a product screenshot. */
export function BrowserFrame({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border bg-card shadow-[0_30px_60px_-30px_rgb(15_61_56/0.45)] dark:shadow-[0_30px_60px_-30px_rgb(0_0_0/0.8)]",
        className,
      )}
    >
      <div className="flex items-center gap-3 border-b bg-muted px-3 py-2">
        <span className="flex gap-1.5" aria-hidden="true">
          <span className="size-2.5 rounded-full bg-foreground/15" />
          <span className="size-2.5 rounded-full bg-foreground/15" />
          <span className="size-2.5 rounded-full bg-foreground/15" />
        </span>
        <span className="mr-8 flex-1 truncate rounded bg-background px-3 py-0.5 text-center text-xs text-muted-foreground">
          checkon.ca/check
        </span>
      </div>
      {children}
    </div>
  )
}
