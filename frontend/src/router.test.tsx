import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, render, screen, waitFor } from "@testing-library/react"
import { createMemoryRouter, RouterProvider } from "react-router"
import { routes } from "@/router"
import { logout } from "@/lib/api/auth"
import { useAuthStore } from "@/lib/store/auth"

const user = {
  id: "1",
  name: "Alice",
  email: "alice@example.com",
  is_admin: false,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

function stubBackend(refresh: () => Promise<Response>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith("/auth/refresh")) return refresh()
      if (url.endsWith("/auth/logout")) return new Response(null, { status: 204 })
      if (url.endsWith("/auth/me")) return json(user)
      return json([])
    }),
  )
}

const validSession = async () => json({ access_token: "tok", expires_in: 3600 })
const noSession = async () => json({ detail: "Refresh token cookie missing" }, 401)

function renderAt(url: string) {
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  const visited: string[] = []
  router.subscribe((state) => visited.push(state.location.pathname))
  render(<RouterProvider router={router} />)
  return { router, visited }
}

describe("route protection", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it.each(["/", "/assistants", "/profile", "/does-not-exist"])(
    "sends %s to /login without a session",
    async (url) => {
      stubBackend(noSession)
      const { router } = renderAt(url)

      await screen.findByText("Welcome back")
      expect(router.state.location.pathname).toBe("/login")
    },
  )

  it.each([
    ["rate limiting", async () => json({ detail: "slow down" }, 429)],
    ["a network failure", async () => { throw new TypeError("Failed to fetch") }],
  ])("falls through to /login on %s", async (_label, refresh) => {
    stubBackend(refresh)
    const { router } = renderAt("/assistants")

    await screen.findByText("Welcome back")
    expect(router.state.location.pathname).toBe("/login")
  })

  it.each(["/login", "/signup"])("sends %s to /assistants with a session", async (url) => {
    stubBackend(validSession)
    const { router } = renderAt(url)

    await waitFor(() => expect(router.state.location.pathname).toBe("/assistants"))
  })

  it("keeps a deep link after restoring the session", async () => {
    stubBackend(validSession)
    const { router, visited } = renderAt("/profile")

    await screen.findByText("account details")
    expect(router.state.location.pathname).toBe("/profile")
    expect(visited).not.toContain("/login")
  })

  it("lets guests reach /signup", async () => {
    stubBackend(noSession)
    const { router } = renderAt("/signup")

    await screen.findByText("Create an account")
    expect(router.state.location.pathname).toBe("/signup")
  })

  it("shows the 404 page to signed-in users", async () => {
    stubBackend(validSession)
    renderAt("/does-not-exist")

    await screen.findByText("Page not found")
  })

  it("clears the session and leaves protected routes on logout", async () => {
    stubBackend(validSession)
    localStorage.setItem("refresh_token", "legacy")
    const { router } = renderAt("/profile")
    await screen.findByText("account details")

    await act(() => logout())

    await screen.findByText("Welcome back")
    expect(router.state.location.pathname).toBe("/login")
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(localStorage.getItem("refresh_token")).toBeNull()
  })
})
