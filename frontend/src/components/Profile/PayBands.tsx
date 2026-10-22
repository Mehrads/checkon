import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"

import { type BandPublic, PayService } from "@/client"
import { Button } from "@/components/ui/button"
import { apiMessage } from "@/hooks/useBilling"
import useCustomToast from "@/hooks/useCustomToast"
import { formatDay } from "../Billing/UsageMeter"

const PER = {
  hour: "an hour",
  week: "a week",
  month: "a month",
  year: "a year",
}

function range(band: BandPublic): string {
  const money = (value: string) => {
    const amount = Number(value)
    const cents = Number.isInteger(amount) ? 0 : 2
    return `$${amount.toLocaleString("en-CA", { minimumFractionDigits: cents, maximumFractionDigits: cents })}`
  }
  const amount =
    band.min === band.max
      ? money(band.min)
      : `${money(band.min)}–${money(band.max)}`
  return `${amount} ${PER[band.unit]}`
}

/** The pay ranges confirmed in a workspace, by job title: the next pay suggestion for that title starts there. */
export function PayBands({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()
  const { data } = useQuery({
    queryKey: ["payBands", workspaceId],
    queryFn: async () =>
      (await PayService.readBands({ query: { workspace_id: workspaceId } }))
        .data,
  })
  const remove = useMutation({
    mutationFn: (bandId: string) =>
      PayService.deleteBand({ path: { band_id: bandId } }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["payBands", workspaceId] }),
    onError: (error) =>
      showErrorToast(apiMessage(error, "We couldn't remove that pay range.")),
  })
  const bands = data?.data ?? []

  return (
    <section className="space-y-3 rounded-xl border bg-card p-5 shadow-sm sm:p-6">
      <div>
        <h2 className="text-sm font-semibold">Pay ranges</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          When you confirm a pay range during a check, it's saved here for that
          job title, and the next suggestion for the title starts from it.
        </p>
      </div>
      {bands.length === 0 ? (
        <p className="text-sm text-muted-foreground">No pay ranges yet.</p>
      ) : (
        <ul className="divide-y">
          {bands.map((band) => (
            <li
              key={band.id}
              className="flex flex-wrap items-center justify-between gap-3 py-2 text-sm"
            >
              <span className="min-w-0">
                <span className="font-medium">{band.title}</span>: {range(band)}
                <span className="ml-2 text-xs text-muted-foreground">
                  Confirmed {formatDay(band.confirmed_at)}
                </span>
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={remove.isPending}
                onClick={() => remove.mutate(band.id)}
                aria-label={`Remove the pay range for ${band.title}`}
              >
                <Trash2 />
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
