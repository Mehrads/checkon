import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { useEffect, useState } from "react"

import { BillingService, LoginService } from "@/client"
import { UsageMeter } from "@/components/Billing/UsageMeter"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { clearToken, saveToken, signedIn } from "./token"

const SITE = new URL(import.meta.env.VITE_API_URL ?? "https://checkon.ca")
  .origin

function message(error: Error, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (!error.response)
      return "We couldn't reach CheckON. Check your connection and try again."
  }
  return fallback
}

/** The customer's sign-in and plan. An expired or revoked sign-in falls back to the free check. */
export function useAccount() {
  const queryClient = useQueryClient()
  const [isSignedIn, setSignedIn] = useState(signedIn)
  const billing = useQuery({
    queryKey: ["billing"],
    queryFn: async () => (await BillingService.readBilling()).data,
    enabled: isSignedIn,
    retry: false,
  })
  const failed =
    billing.error instanceof AxiosError ? billing.error.response?.status : 0
  useEffect(() => {
    if (failed && [401, 403, 404].includes(failed)) {
      clearToken()
      setSignedIn(false)
    }
  }, [failed])

  return {
    isSignedIn,
    billing: isSignedIn ? billing.data : undefined,
    signIn: async (token: string) => {
      await saveToken(token)
      setSignedIn(true)
      queryClient.invalidateQueries({ queryKey: ["billing"] })
    },
    signOut: async () => {
      await clearToken()
      setSignedIn(false)
      queryClient.removeQueries({ queryKey: ["billing"] })
    },
    refresh: () => queryClient.invalidateQueries({ queryKey: ["billing"] }),
  }
}

export type Account = ReturnType<typeof useAccount>

const linkClass = "underline underline-offset-4 hover:text-foreground"

/** One line under the header: log in, or the plan and its checks this period. */
export function AccountBar({
  account,
  onLogIn,
}: {
  account: Account
  onLogIn: () => void
}) {
  if (!account.isSignedIn) {
    return (
      <p className="text-xs text-muted-foreground">
        On a CheckON plan?{" "}
        <button type="button" onClick={onLogIn} className={linkClass}>
          Log in
        </button>{" "}
        to use its checks here.
      </p>
    )
  }
  const { billing } = account
  const logOut = (
    <button type="button" onClick={account.signOut} className={linkClass}>
      Log out
    </button>
  )
  if (!billing) return null
  if (!billing.plan) {
    return (
      <p className="text-xs text-muted-foreground">
        You're signed in without an active plan, so the free check applies.{" "}
        <a href={SITE} target="_blank" rel="noreferrer" className={linkClass}>
          Choose a plan
        </a>{" "}
        · {logOut}
      </p>
    )
  }
  return (
    <section className="space-y-2 rounded-xl border bg-card p-3 shadow-sm">
      <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span>
          <span className="font-medium text-foreground">
            {billing.plan_name}
          </span>{" "}
          plan
          {billing.status === "past_due" && (
            <span className="text-destructive">
              {" "}
              · payment failed, update your card on{" "}
              <a
                href={SITE}
                target="_blank"
                rel="noreferrer"
                className={linkClass}
              >
                checkon.ca
              </a>
            </span>
          )}
        </span>
        {logOut}
      </div>
      <UsageMeter billing={billing} className="text-xs [&_p]:text-xs" />
    </section>
  )
}

/** Password, then the emailed code: the same two steps as the website. */
export function SignIn({
  onSignedIn,
  onCancel,
}: {
  onSignedIn: (token: string) => void
  onCancel: () => void
}) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [challenge, setChallenge] = useState<string | null>(null)
  const [code, setCode] = useState("")
  const [error, setError] = useState<string | null>(null)

  const sendPassword = useMutation({
    mutationFn: async () =>
      (
        await LoginService.loginPassword({
          body: { username: email.trim(), password },
        })
      ).data,
    onSuccess: (data) => {
      setError(null)
      setChallenge(data.challenge)
    },
    onError: (err) => setError(message(err, "Incorrect email or password")),
  })

  const sendCode = useMutation({
    mutationFn: async () =>
      (
        await LoginService.loginAccessToken({
          body: { challenge: challenge ?? "", code },
        })
      ).data,
    onSuccess: (data) => onSignedIn(data.access_token),
    onError: (err) => setError(message(err, "Incorrect code")),
  })

  return (
    <section className="space-y-4 rounded-xl border bg-card p-4 shadow-sm">
      <div>
        <h2 className="text-sm font-semibold">
          {challenge ? "Check your email" : "Log in to your plan"}
        </h2>
        <p className="text-xs text-muted-foreground">
          {challenge
            ? `We sent a 6-digit sign-in code to ${email.trim()}.`
            : "Your checks here then count toward your plan, like on checkon.ca."}
        </p>
      </div>
      {challenge ? (
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (!sendCode.isPending) sendCode.mutate()
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="code">Sign-in code</Label>
            <Input
              id="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              autoFocus
              placeholder="123456"
              value={code}
              onChange={(event) =>
                setCode(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
            />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              className="text-xs text-muted-foreground underline underline-offset-4"
              onClick={() => {
                setChallenge(null)
                setCode("")
                setError(null)
              }}
            >
              Start again
            </button>
            <LoadingButton
              type="submit"
              size="sm"
              loading={sendCode.isPending}
              disabled={code.length !== 6}
            >
              Verify
            </LoadingButton>
          </div>
        </form>
      ) : (
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (!sendPassword.isPending) sendPassword.mutate()
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              autoFocus
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex items-center justify-between gap-3">
            <a
              href={`${SITE}/recover-password`}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-muted-foreground underline underline-offset-4"
            >
              Forgot your password?
            </a>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onCancel}
                className="text-xs text-muted-foreground underline underline-offset-4"
              >
                Cancel
              </button>
              <LoadingButton
                type="submit"
                size="sm"
                loading={sendPassword.isPending}
                disabled={!email.trim() || password.length < 8}
              >
                Log in
              </LoadingButton>
            </div>
          </div>
        </form>
      )}
    </section>
  )
}
