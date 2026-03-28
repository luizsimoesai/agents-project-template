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
    const res = await apiClient("/api/v1/assistants")
    const data = await res.json()
    expect(data).toEqual({ id: 1 })
  })
})
