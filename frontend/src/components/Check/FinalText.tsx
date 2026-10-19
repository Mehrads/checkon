import { Check, Copy } from "lucide-react"

import type { FinalOut } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import { STATUS_TEXT } from "./labels"

export function FinalText({ final }: { final: FinalOut }) {
  const [copied, copy] = useCopyToClipboard()
  return (
    <Card className="border-green-600/50">
      <CardHeader>
        <CardTitle>Your updated posting</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm">{STATUS_TEXT[final.report.status]}</p>
        <textarea
          readOnly
          value={final.text}
          className="min-h-72 w-full rounded-md border bg-transparent p-3 font-mono text-sm"
          aria-label="Updated posting"
        />
        <Button className="self-start" onClick={() => copy(final.text)}>
          {copied ? <Check /> : <Copy />}
          {copied ? "Copied" : "Copy posting"}
        </Button>
      </CardContent>
    </Card>
  )
}
