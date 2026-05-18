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

    const [, options] = fetchMock.mock.calls[0]!
    expect(options.headers["Authorization"]).toBe("Bearer mytoken")
    // credentials:include is required so the HttpOnly refresh cookie is
    // sent on cross-origin requests (and matches CORS allow_credentials).
    expect(options.credentials).toBe("include")
  })

  it("omits Authorization header when no token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    )
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    await apiClient("/api/v1/auth/login", { method: "POST" })

    const [, options] = fetchMock.mock.calls[0]!
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

    let callCount = 0
    const fetchMock = vi.fn().mockImplementation((url: string) => {
      callCount++
      // First call: original request returns 401
      if (callCount === 1) {
        return Promise.resolve(new Response(null, { status: 401 }))
      }
      // /auth/refresh — server reads cookie (we don't send a body)
      if (typeof url === "string" && url.includes("/auth/refresh")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: "new-token",
              token_type: "bearer",
              expires_in: 3600,
            }),
            { status: 200 }
          )
        )
      }
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
      return Promise.resolve(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    })
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    const res = await apiClient("/assistants")
    expect(res.status).toBe(200)

    // Verify the retry used the new token
    const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1]!
    expect(lastCall[1].headers["Authorization"]).toBe("Bearer new-token")

    // The refresh call was made WITHOUT a body — the cookie is the sole carrier
    const refreshCall = fetchMock.mock.calls.find(
      (c: unknown[]) => typeof c[0] === "string" && (c[0] as string).includes("/auth/refresh")
    )
    expect(refreshCall?.[1]?.body).toBeUndefined()
    expect(refreshCall?.[1]?.credentials).toBe("include")
  })

  it("clears auth and throws ApiAuthError when refresh fails", async () => {
    useAuthStore.setState({ accessToken: "expired", user: null })

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 401 })
    )
    vi.stubGlobal("fetch", fetchMock)
    vi.stubGlobal("window", { location: { href: "" } })

    const { apiClient, ApiAuthError } = await import("./client")
    await expect(apiClient("/assistants")).rejects.toBeInstanceOf(ApiAuthError)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })

  it("deduplicates concurrent 401s into a single /auth/refresh call", async () => {
    useAuthStore.setState({ accessToken: "expired", user: null })

    let refreshCalls = 0
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (typeof url === "string" && url.includes("/auth/refresh")) {
        refreshCalls++
        return Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: "new-token",
              token_type: "bearer",
              expires_in: 3600,
            }),
            { status: 200 }
          )
        )
      }
      if (typeof url === "string" && url.includes("/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              id: "1",
              name: "Alice",
              email: "alice@example.com",
              is_admin: false,
              is_active: true,
              created_at: "2026-01-01T00:00:00Z",
            }),
            { status: 200 }
          )
        )
      }
      const headers = init?.headers as Record<string, string> | undefined
      if (headers?.["Authorization"] === "Bearer expired") {
        return Promise.resolve(new Response(null, { status: 401 }))
      }
      return Promise.resolve(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )
    })
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    const [a, b] = await Promise.all([
      apiClient("/assistants"),
      apiClient("/threads"),
    ])
    expect(a.status).toBe(200)
    expect(b.status).toBe(200)
    expect(refreshCalls).toBe(1)
  })

  it("retries with the new token without refreshing if the store already rotated", async () => {
    useAuthStore.setState({ accessToken: "old-token", user: null })

    let refreshCalls = 0
    let firstCall = true
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (typeof url === "string" && url.includes("/auth/refresh")) {
        refreshCalls++
      }
      if (firstCall) {
        firstCall = false
        // Simulate a parallel refresh that just landed: rotate the store
        // token before returning 401 on the in-flight request.
        useAuthStore.setState({
          accessToken: "freshly-rotated",
          user: { id: "1", name: "x", email: "x@x", is_admin: false, is_active: true, created_at: "2026-01-01T00:00:00Z" },
        })
        return Promise.resolve(new Response(null, { status: 401 }))
      }
      // Retry should carry the fresh token.
      const auth = (init?.headers as Record<string, string>)?.["Authorization"]
      expect(auth).toBe("Bearer freshly-rotated")
      return Promise.resolve(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      )
    })
    vi.stubGlobal("fetch", fetchMock)

    const { apiClient } = await import("./client")
    const res = await apiClient("/assistants")
    expect(res.status).toBe(200)
    expect(refreshCalls).toBe(0)
  })
})
