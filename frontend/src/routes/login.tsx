import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { Body_login_login_password as Credentials } from "@/client"
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
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { afterLogin, isLoggedIn } from "@/hooks/useAuth"
import { noindex } from "@/lib/seo"

const formSchema = z.object({
  username: z.email({ message: "Invalid email address" }),
  password: z
    .string()
    .min(1, { message: "Password is required" })
    .min(8, { message: "Password must be at least 8 characters" }),
}) satisfies z.ZodType<Credentials>

type FormData = z.infer<typeof formSchema>

const codeSchema = z.object({
  code: z.string().regex(/^\d{6}$/, { message: "Enter the 6-digit code" }),
})

type CodeData = z.infer<typeof codeSchema>

type Pending = { email: string; challenge: string }

export const Route = createFileRoute("/login")({
  component: Login,
  // The account page a signed-out visitor opened, e.g. the extension's link to an archived posting
  validateSearch: z.object({ redirect: z.string().optional() }),
  beforeLoad: async ({ search }) => {
    if (isLoggedIn()) {
      throw redirect({
        href: afterLogin(search.redirect),
      })
    }
  },
  head: () => ({
    meta: [{ title: "Log in - CheckON" }, ...noindex().meta],
  }),
})

function Login() {
  const [email, setEmail] = useState("")
  const [pending, setPending] = useState<Pending | null>(null)

  const onCodeSent = (sent: Pending) => {
    setEmail(sent.email)
    setPending(sent)
  }

  return (
    <AuthLayout>
      {pending ? (
        <CodeForm pending={pending} onRestart={() => setPending(null)} />
      ) : (
        <PasswordForm email={email} onCodeSent={onCodeSent} />
      )}
    </AuthLayout>
  )
}

function PasswordForm({
  email,
  onCodeSent,
}: {
  email: string
  onCodeSent: (sent: Pending) => void
}) {
  const { passwordMutation } = useAuth()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: email,
      password: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (passwordMutation.isPending) return
    passwordMutation.mutate(data, {
      onSuccess: ({ challenge }) =>
        onCodeSent({ email: data.username, challenge }),
    })
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="flex flex-col gap-6"
      >
        <AuthHeading title="Log in to CheckON">
          Use your account's email. We'll email you a sign-in code.
        </AuthHeading>

        <div className="grid gap-4">
          <FormField
            control={form.control}
            name="username"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input
                    data-testid="email-input"
                    placeholder="user@example.com"
                    type="email"
                    {...field}
                  />
                </FormControl>
                <FormMessage className="text-xs" />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center">
                  <FormLabel>Password</FormLabel>
                  <RouterLink
                    to="/recover-password"
                    className="ml-auto text-sm underline-offset-4 hover:underline"
                  >
                    Forgot your password?
                  </RouterLink>
                </div>
                <FormControl>
                  <PasswordInput
                    data-testid="password-input"
                    placeholder="Password"
                    {...field}
                  />
                </FormControl>
                <FormMessage className="text-xs" />
              </FormItem>
            )}
          />

          <LoadingButton type="submit" loading={passwordMutation.isPending}>
            Log in
          </LoadingButton>
        </div>

        <p className="border-t pt-5 text-sm text-muted-foreground">
          No account yet?{" "}
          <RouterLink
            to="/signup"
            className="font-medium text-foreground underline underline-offset-4"
          >
            Create a free one
          </RouterLink>
          , or{" "}
          <a href="/check#pricing" className="underline underline-offset-4">
            see the plans
          </a>
          .
        </p>
      </form>
    </Form>
  )
}

function CodeForm({
  pending,
  onRestart,
}: {
  pending: Pending
  onRestart: () => void
}) {
  const { redirect: next } = Route.useSearch()
  const { loginMutation } = useAuth(next)
  const form = useForm<CodeData>({
    resolver: zodResolver(codeSchema),
    defaultValues: { code: "" },
  })

  const onSubmit = (data: CodeData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate({ challenge: pending.challenge, code: data.code })
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="flex flex-col gap-6"
      >
        <AuthHeading title="Check your email">
          We sent a 6-digit sign-in code to {pending.email}. It works for 10
          minutes.
        </AuthHeading>

        <div className="grid gap-4">
          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Sign-in code</FormLabel>
                <FormControl>
                  <Input
                    data-testid="code-input"
                    placeholder="123456"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    autoFocus
                    {...field}
                    onChange={(event) =>
                      field.onChange(
                        event.target.value.replace(/\D/g, "").slice(0, 6),
                      )
                    }
                  />
                </FormControl>
                <FormMessage className="text-xs" />
              </FormItem>
            )}
          />

          <LoadingButton type="submit" loading={loginMutation.isPending}>
            Verify
          </LoadingButton>
        </div>

        <div className="text-sm text-muted-foreground">
          Code expired or didn't arrive?{" "}
          <button
            type="button"
            onClick={onRestart}
            className="underline underline-offset-4"
          >
            Log in again
          </button>
        </div>
      </form>
    </Form>
  )
}
