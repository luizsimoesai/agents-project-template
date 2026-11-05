import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createElement } from "react"
import { useAssistants } from "./useAssistants"
import type { AssistantRead } from "@/lib/types"

vi.mock("@/lib/api/assistants", () => ({
  fetchAssistants: vi.fn().mockResolvedValue([
    {
      assistant_id: "a1",
      name: "Test",
      description: null,
      graph_id: "agent",
      config: {},
      context: {},
      metadata: {},
      version: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ] as AssistantRead[]),
}))

function createWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client }, children)
}

describe("useAssistants", () => {
  it("returns list of assistants", async () => {
    const { result } = renderHook(() => useAssistants(), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(1)
    expect(result.current.data![0]!.name).toBe("Test")
  })
})
