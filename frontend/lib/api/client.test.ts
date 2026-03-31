import { describe, it, expect, vi, beforeEach } from "vitest"
import { useAuthStore } from "@/lib/store/auth"

// Configure auth state before importing client
beforeEach(() => {
  useAuthStore.setState({ accessToken: null, user: null })
  localStorage.clear()
  vi.restoreAllMocks()
})

describe("apiClient", () => {
  it("injects Authorization header when token exists", async () => {
    useAuthStore.setState({ accessToken: "mytoken", user: null })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    await apiClient("/api/v1/auth/me")

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers["Authorization"]).toBe("Bearer mytoken")
  })

  it("omits Authorization header when no token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    await apiClient("/api/v1/auth/login", { method: "POST" })

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers["Authorization"]).toBeUndefined()
  })

  it("returns response object for successful requests", async () => {
    useAuthStore.setState({ accessToken: "tok", user: null })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1 }), { status: 200 })
    )
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    const res = await apiClient("/assistants")
    const data = await res.json()
    expect(data).toEqual({ id: 1 })
  })

  it("attempts refresh on 401 and retries request with new token", async () => {
    useAuthStore.setState({ accessToken: "expired", user: null })
    localStorage.setItem("refresh_token", "valid-refresh")

    let callCount = 0
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      callCount++
      // First call: original request returns 401
      if (callCount === 1) {
        return Promise.resolve(new Response(null, { status: 401 }))
      }
      // Second call: refresh endpoint returns new tokens
      if (typeof url === "string" && url.includes("/auth/refresh")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: "new-token",
              refresh_token: "new-refresh",
              token_type: "bearer",
              expires_in: 3600,
            }),
            { status: 200 }
          )
        )
      }
      // Third call: /auth/me returns user
      if (typeof url === "string" && url.includes("/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "1", name: "Alice", email: "alice@example.com",
              is_admin: false, is_active: true, created_at: "2026-01-01T00:00:00Z",
            }),
            { status: 200 }
          )
        )
      }
      // Fourth call: original request retried with new token
      return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    })
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    const res = await apiClient("/assistants")
    expect(res.status).toBe(200)

    // Verify the retry used the new token
    const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]
    expect(lastCall[1].headers["Authorization"]).toBe("Bearer new-token")
  })

  it("calls clearAuth and returns 401 when refresh fails", async () => {
    useAuthStore.setState({ accessToken: "expired", user: null })
    localStorage.removeItem("refresh_token") // no refresh token = immediate failure

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 401 })
    )
    vi.stubGlobal("fetch", fetchMock)
    // stub window.location to avoid jsdom errors
    vi.stubGlobal("window", { location: { href: "" } })

    const { apiClient } = await import("./client")
    const res = await apiClient("/assistants")
    expect(res.status).toBe(401)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })
})
