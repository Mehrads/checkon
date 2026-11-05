import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { useEffect, useState } from "react"

import { AccountService, LoginService } from "@/client"
import { usageText } from "@/components/Account/usage"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import { SITE } from "./site"
import { clearToken, saveToken, signedIn } from "./token"

function message(error: Error, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (!error.response)
      return "We couldn't reach CheckON. Check your connection and try again."
  }
  return fallback
}

/** The user's sign-in and their account's checks. An expired or revoked sign-in falls back to the free check. */
export function useAccount() {
  const queryClient = useQueryClient()
  const [isSignedIn, setSignedIn] = useState(signedIn)
  const account = useQuery({
    queryKey: ["account"],
    queryFn: async () => (await AccountService.readAccount()).data,
    enabled: isSignedIn,
    retry: false,
  })
  const failed =
    account.error instanceof AxiosError ? account.error.response?.status : 0
  useEffect(() => {
    if (failed && [401, 403, 404].includes(failed)) {
      clearToken()
      setSignedIn(false)
    }
  }, [failed])

  return {
    isSignedIn,
    usage: isSignedIn ? account.data : undefined,
    signIn: async (token: string) => {
      await saveToken(token)
      setSignedIn(true)
      queryClient.invalidateQueries({ queryKey: ["account"] })
    },
    signOut: async () => {
      await clearToken()
      setSignedIn(false)
      queryClient.removeQueries({ queryKey: ["account"] })
      queryClient.removeQueries({ queryKey: ["workspaces"] })
    },
    refresh: () => queryClient.invalidateQueries({ queryKey: ["account"] }),
  }
}

export type Account = ReturnType<typeof useAccount>

const linkClass = "underline underline-offset-4 hover:text-foreground"

/** One line under the header: log in, or the account's checks in the last 30 days. */
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
        Have a CheckON account?{" "}
        <button type="button" onClick={onLogIn} className={linkClass}>
          Log in
        </button>{" "}
        to use its checks and company profiles here.
      </p>
    )
  }
  const { usage } = account
  if (!usage) return null
  return (
    <p className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
      <span className="tabular-nums">Signed in · {usageText(usage)}</span>
      <button type="button" onClick={account.signOut} className={linkClass}>
        Log out
      </button>
    </p>
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
          {challenge ? "Check your email" : "Log in to your account"}
        </h2>
        <p className="text-xs text-muted-foreground">
          {challenge
            ? `We sent a 6-digit sign-in code to ${email.trim()}.`
            : "Your checks here are then saved to your account, like on the website."}
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
