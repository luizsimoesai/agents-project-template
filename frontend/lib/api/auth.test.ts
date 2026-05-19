import { describe, it, expect, vi, beforeEach } from "vitest"
import { useAuthStore } from "@/lib/store/auth"
import { changePassword } from "./auth"

beforeEach(() => {
  useAuthStore.setState({ accessToken: "live-token", user: null })
  localStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe("changePassword", () => {
  it("POSTs current + new password and clears auth on 204", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal("fetch", fetchMock)

    await changePassword("password123", "brand-new-password")

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0]!
    expect(String(url)).toContain("/api/v1/auth/change-password")
    expect(options.method).toBe("POST")
    expect(JSON.parse(options.body as string)).toEqual({
      current_password: "password123",
      new_password: "brand-new-password",
    })
    // Local auth state was wiped — user must re-login.
    expect(useAuthStore.getState().accessToken).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })

  it("throws server detail on 400 and does not clear auth", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Current password is incorrect" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      ),
    )
    vi.stubGlobal("fetch", fetchMock)

    await expect(
      changePassword("wrong", "brand-new-password"),
    ).rejects.toThrow("Current password is incorrect")
    // Auth state untouched on failure.
    expect(useAuthStore.getState().accessToken).toBe("live-token")
  })

  it("falls back to generic message when body is not JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("oops", { status: 500 }),
    )
    vi.stubGlobal("fetch", fetchMock)

    await expect(
      changePassword("password123", "brand-new-password"),
    ).rejects.toThrow("Failed to change password")
  })
})
