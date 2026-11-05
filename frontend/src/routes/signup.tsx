import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { LockKeyhole, MailCheck } from "lucide-react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { SignupService } from "@/client"
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
import { apiMessage, apiReason } from "@/lib/api"
import { noindex } from "@/lib/seo"
import { handleError } from "@/utils"

const formSchema = z.object({
  email: z.email({ message: "Invalid email address" }),
})

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/signup")({
  component: SignUp,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Create an account - CheckON" }, ...noindex().meta],
  }),
})

const GETS = [
  "Checks by pasting a posting or its link, with fixes you approve one by one",
  "A company profile for each client, and careers page audits",
  "A history of what you checked",
]

/** An account: an email, then a link to set the password. The server can close sign-up (SIGNUP_OPEN); then it
 * answers 403 "signup_closed" with a message to show instead of the form. */
function SignUp() {
  const { showErrorToast } = useCustomToast()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: { email: "" },
  })
  const mutation = useMutation({
    mutationFn: async (data: FormData) =>
      (await SignupService.signUp({ body: { email: data.email } })).data,
    onSuccess: () => track("signup"),
    onError: (error) => {
      if (apiReason(error) !== "signup_closed")
        handleError.call(showErrorToast, error)
    },
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

  if (mutation.error && apiReason(mutation.error) === "signup_closed") {
    return (
      <AuthLayout>
        <div className="flex flex-col gap-6" data-testid="signup-closed">
          <LockKeyhole className="size-9 text-primary" aria-hidden="true" />
          <AuthHeading title="Sign-up is closed">
            {apiMessage(
              mutation.error,
              "Sign-up is closed on this server. Ask its admin for an account.",
            )}
          </AuthHeading>
          <div className="border-t pt-5 text-sm text-muted-foreground">
            Already have an account?{" "}
            <RouterLink to="/login" className="underline underline-offset-4">
              Log in
            </RouterLink>
          </div>
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
          <AuthHeading title="Create an account">
            Just your email. We send a link to set your password.
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
            <RouterLink to="/login" className="underline underline-offset-4">
              Log in
            </RouterLink>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
