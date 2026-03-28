import { describe, it, expectTypeOf } from "vitest"
import type { UserRead, AssistantRead, ThreadRead, MessageRead } from "./types"

describe("types", () => {
  it("UserRead has required fields", () => {
    const user: UserRead = {
      id: "123",
      name: "Test",
      email: "test@example.com",
      is_admin: false,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    }
    expectTypeOf(user.is_admin).toBeBoolean()
    expectTypeOf(user.is_active).toBeBoolean()
  })

  it("AssistantRead has assistant_id not id", () => {
    const a: AssistantRead = {
      assistant_id: "abc",
      name: "My Assistant",
      description: null,
      graph_id: "agent",
      config: {},
      context: {},
      metadata: {},
      version: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    }
    expectTypeOf(a.assistant_id).toBeString()
  })
})
