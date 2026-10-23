/** After the build: write each public page as HTML next to index.html (src/prerender.tsx renders them). The page's
 * title, description, canonical link and Open Graph tags go into the head, in place of index.html's, marked so the
 * app removes them when it starts (its routes render their own); its content goes inside #root, marked so index.html
 * can hide it from someone signed in until the app has rendered. */

import { readFile, writeFile } from "node:fs/promises"
import { join } from "node:path"

// @ts-expect-error: built by `vite build --ssr src/prerender.tsx --outDir .prerender`
import { PAGES, render } from "../.prerender/prerender.js"

const OUT = join(import.meta.dir, "..", "..", "backend", "app", "frontend")
const HEAD_TAG = /<(title)>[^<]*<\/title>|<(meta|link)\b[^>]*\/?>/g

const shell = await readFile(join(OUT, "index.html"), "utf8")
for (const [path, file] of Object.entries(PAGES as Record<string, string>)) {
  const rendered: string = await render(path)
  // React writes the route's <title>, <meta> and <link> tags where they're rendered; they belong in the head
  const head = rendered.match(HEAD_TAG) ?? []
  const body = rendered.replace(HEAD_TAG, "")
  if (!head.some((tag) => tag.startsWith("<title>")) || body.length < 1000) {
    throw new Error(`Prerendering ${path} produced no page`)
  }
  const marked = head.map((tag) =>
    tag.replace(/^<(\w+)/, "<$1 data-static-head"),
  )
  const page = shell
    .replace(/<title data-static-head>[^<]*<\/title>/, "")
    .replace(/<meta\s+data-static-head[^>]*>/, "")
    .replace("</head>", `${marked.join("")}</head>`)
    .replace(
      '<div id="root"></div>',
      `<div id="root"><div data-prerendered>${body}</div></div>`,
    )
  await writeFile(join(OUT, file), page)
  console.log(
    `prerendered ${path} -> ${file} (${body.length.toLocaleString()} characters)`,
  )
}
