// A paying customer's sign-in, kept in the extension's own storage (chrome.storage.local), so their
// checks in the side panel count against their plan. Visitors who never sign in get the free check.
// The API client reads the token through `currentToken`, which must answer synchronously, so the
// stored value is loaded once before the panel renders.

const KEY = "access_token"
let token: string | null = null

export async function loadToken(): Promise<void> {
  const stored = await chrome.storage.local.get(KEY)
  token = typeof stored[KEY] === "string" ? stored[KEY] : null
}

export const currentToken = () => token ?? ""
export const signedIn = () => token !== null

export async function saveToken(value: string): Promise<void> {
  token = value
  await chrome.storage.local.set({ [KEY]: value })
}

export async function clearToken(): Promise<void> {
  token = null
  await chrome.storage.local.remove(KEY)
}
