import { describe, it, expect, beforeEach, vi } from "vitest"
import { useAuthStore } from "./auth"

// Cookie mock
vi.stubGlobal("document", {
  cookie: "",
})

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, user: null })
    document.cookie = ""
  })

  it("starts with no auth", () => {
    const { accessToken, user } = useAuthStore.getState()
    expect(accessToken).toBeNull()
    expect(user).toBeNull()
  })

  it("setAuth stores token and user", () => {
    const user = {
      id: "1",
      name: "Alice",
      email: "alice@example.com",
      is_admin: false,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    }
    useAuthStore.getState().setAuth("tok123", user)
    const state = useAuthStore.getState()
    expect(state.accessToken).toBe("tok123")
    expect(state.user).toEqual(user)
  })

  it("clearAuth removes token and user", () => {
    useAuthStore.getState().setAuth("tok123", {
      id: "1", name: "Alice", email: "alice@example.com",
      is_admin: false, is_active: true, created_at: "2026-01-01T00:00:00Z",
    })
    useAuthStore.getState().clearAuth()
    const state = useAuthStore.getState()
    expect(state.accessToken).toBeNull()
    expect(state.user).toBeNull()
  })
})
