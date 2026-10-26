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

/** A photo as AVIF with a WebP fallback, sized by `srcset` and loaded lazily. */
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
