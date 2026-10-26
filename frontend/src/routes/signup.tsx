import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { MailCheck } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { SignupService } from "@/client"
import { FREE_ACCOUNT_CHECKS } from "@/components/Billing/UsageMeter"
import { AuthHeading, AuthLayout } from "@/components/Common/AuthLayout"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { track } from "@/lib/analytics"
import { noindex } from "@/lib/seo"
import { handleError } from "@/utils"

const formSchema = z.object({
  email: z.email({ message: "Invalid email address" }),
})

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/signup")({
  component: SignUp,
  // An outreach report's token: it's saved to the account after the first log-in
  validateSearch: z.object({ report: z.string().optional().catch(undefined) }),
  beforeLoad: async ({ search }) => {
    if (isLoggedIn()) {
      throw redirect(
        search.report
          ? { to: "/report/$token", params: { token: search.report } }
          : { to: "/" },
      )
    }
  },
  head: () => ({
    meta: [{ title: "Create a free account - CheckON" }, ...noindex().meta],
  }),
})

const GETS = [
  `${FREE_ACCOUNT_CHECKS} checks every 30 days, by pasting a posting or its link`,
  "Fixes you approve one by one, then copy",
  "A history of what you checked",
]

/** A free account: an email, then a link to set the password. No card. */
function SignUp() {
  const { report } = Route.useSearch()
  const { showErrorToast } = useCustomToast()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { email: "" },
  })
  const mutation = useMutation({
    mutationFn: async (data: FormData) =>
      (await SignupService.signUp({ body: { email: data.email, report } }))
        .data,
    onSuccess: () => track("signup"),
    onError: handleError.bind(showErrorToast),
  })

  if (mutation.isSuccess) {
    return (
      <AuthLayout>
        <div className="flex flex-col gap-6">
          <MailCheck className="size-9 text-primary" aria-hidden="true" />
          <AuthHeading title="Check your email">
            We sent a link to {mutation.variables.email}. Open it to set your
            password, then log in with it and a code we email you.
          </AuthHeading>
          <p className="border-t pt-5 text-xs text-muted-foreground">
            No email after a few minutes? Check your spam folder, or use "Forgot
            your password?" on the log-in page with the same address.
          </p>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((data) => mutation.mutate(data))}
          className="flex flex-col gap-6"
        >
          <AuthHeading title="Create a free account">
            {report
              ? "Your report is saved to it, and you can fix each posting from there."
              : "No card, no plan to choose."}
          </AuthHeading>

          <ul className="space-y-2 text-sm">
            {GETS.map((item) => (
              <li key={item} className="flex gap-2">
                <span
                  className="mt-2 size-1.5 shrink-0 rounded-full bg-primary"
                  aria-hidden="true"
                />
                {item}
              </li>
            ))}
          </ul>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Work email</FormLabel>
                  <FormControl>
                    <Input
                      data-testid="email-input"
                      placeholder="you@company.ca"
                      type="email"
                      autoComplete="email"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <LoadingButton
              type="submit"
              className="w-full"
              loading={mutation.isPending}
            >
              Email me a link
            </LoadingButton>
          </div>

          <p className="text-xs text-muted-foreground">
            By creating an account you agree to the{" "}
            <a href="/terms" className="underline underline-offset-4">
              Terms
            </a>{" "}
            and the{" "}
            <a href="/privacy" className="underline underline-offset-4">
              Privacy policy
            </a>
            .
          </p>

          <div className="border-t pt-5 text-sm text-muted-foreground">
            Already have an account?{" "}
            <RouterLink
              to="/login"
              search={
                report ? { redirect: `/report/${report}?save=1` } : undefined
              }
              className="underline underline-offset-4"
            >
              Log in
            </RouterLink>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
