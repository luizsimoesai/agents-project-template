import { StrictMode } from "react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, render, screen, waitFor } from "@testing-library/react"
import { AuthProvider } from "./AuthProvider"
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

function renderProvider() {
  return render(
    <StrictMode>
      <AuthProvider>
        <p>app</p>
      </AuthProvider>
    </StrictMode>,
  )
}

describe("AuthProvider", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it("restores the session with a single refresh call", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith("/auth/refresh")
        ? json({ access_token: "restored", expires_in: 3600 })
        : json(user),
    )
    vi.stubGlobal("fetch", fetchMock)

    renderProvider()

    await screen.findByText("app")
    expect(useAuthStore.getState().accessToken).toBe("restored")
    const refreshCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).endsWith("/auth/refresh"),
    )
    expect(refreshCalls).toHaveLength(1)
  })

  it("holds the app back until the refresh settles", async () => {
    let settle: (response: Response) => void = () => {}
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((resolve) => { settle = resolve })),
    )

    renderProvider()
    expect(screen.queryByText("app")).not.toBeInTheDocument()

    // Settling also releases the module-level single-flight in client.ts.
    settle(json({ detail: "nope" }, 401))
    await screen.findByText("app")
  })

  describe("when the backend never answers", () => {
    let settle: (response: Response) => void = () => {}

    beforeEach(() => {
      vi.useFakeTimers()
      vi.stubGlobal(
        "fetch",
        vi.fn(() => new Promise<Response>((resolve) => { settle = resolve })),
      )
    })

    it("stops waiting after 8 seconds", async () => {
      renderProvider()

      act(() => { vi.advanceTimersByTime(7999) })
      expect(screen.queryByText("app")).not.toBeInTheDocument()

      act(() => { vi.advanceTimersByTime(1) })
      expect(screen.getByText("app")).toBeInTheDocument()

      vi.useRealTimers()
      settle(json({ detail: "nope" }, 401))
      await waitFor(() => expect(useAuthStore.getState().accessToken).toBeNull())
    })

    it("does not let a late failure end a newer login", async () => {
      renderProvider()
      act(() => { vi.advanceTimersByTime(8000) })
      useAuthStore.setState({ accessToken: "fresh-login", user })

      vi.useRealTimers()
      await act(async () => {
        settle(json({ detail: "nope" }, 401))
        await new Promise((resolve) => setTimeout(resolve))
      })

      expect(useAuthStore.getState().accessToken).toBe("fresh-login")
    })
  })

  it("skips the refresh when a token is already in memory", async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal("fetch", fetchMock)
    useAuthStore.setState({ accessToken: "live", user })

    renderProvider()

    await screen.findByText("app")
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it.each([
    ["a rejected refresh", async () => json({ detail: "nope" }, 401)],
    ["rate limiting", async () => json({ detail: "slow down" }, 429)],
    ["a network failure", async () => { throw new TypeError("Failed to fetch") }],
  ])("stops loading after %s", async (_label, respond) => {
    vi.stubGlobal("fetch", vi.fn(respond))

    renderProvider()

    await screen.findByText("app")
    expect(useAuthStore.getState().accessToken).toBeNull()
  })
})
