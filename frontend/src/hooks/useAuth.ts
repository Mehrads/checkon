import { useMutation, useQuery } from "@tanstack/react-query"
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

const useAuth = () => {
  const navigate = useNavigate()
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
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    navigate({ to: "/login" })
  }

  return {
    passwordMutation,
    loginMutation,
    logout,
    user,
  }
}

export { isLoggedIn }
export default useAuth
