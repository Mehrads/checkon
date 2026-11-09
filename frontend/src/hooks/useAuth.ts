import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import {
  type Body_login_login_password as Credentials,
  type LoginCodeIn,
  LoginService,
  type UserPublic,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

// No storage when the public pages are rendered to HTML at build time (src/prerender.tsx): signed out
const isLoggedIn = () => {
  return (
    typeof localStorage !== "undefined" &&
    localStorage.getItem("access_token") !== null
  )
}

/** Where to go once signed in: the page of this site a visitor was sent to log in from (`/login?redirect=`), else
 * the account page. Only a path here: never another site, or a `javascript:` link. */
const afterLogin = (redirect?: string) =>
  redirect?.startsWith("/") && !/^\/[/\\]/.test(redirect) ? redirect : "/"

/** `next`: the `redirect` of /login, to go back to after the emailed code. */
const useAuth = (next?: string) => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: async () => (await UsersService.readUserMe()).data,
    enabled: isLoggedIn(),
  })

  // Step 1: the password. The API emails a sign-in code and returns its challenge.
  const passwordMutation = useMutation({
    mutationFn: async (data: Credentials) =>
      (await LoginService.loginPassword({ body: data })).data,
    onError: handleError.bind(showErrorToast),
  })

  // Step 2: the emailed code, exchanged for the access token
  const login = async (data: LoginCodeIn) => {
    const response = await LoginService.loginAccessToken({
      body: data,
    })
    localStorage.setItem("access_token", response.data.access_token)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ href: afterLogin(next) })
    },
    onError: handleError.bind(showErrorToast),
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    // Nothing of this account stays in memory for whoever signs in next
    queryClient.cancelQueries()
    queryClient.clear()
    navigate({ to: "/login" })
  }

  return {
    passwordMutation,
    loginMutation,
    logout,
    user,
  }
}

export { afterLogin, isLoggedIn }
export default useAuth
