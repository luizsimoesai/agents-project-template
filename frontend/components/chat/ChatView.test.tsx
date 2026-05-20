import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createElement } from "react"
import { ChatView } from "./ChatView"
import type { AssistantRead, ModelRead, ThreadRead } from "@/lib/types"

// ---- Mocks -----------------------------------------------------------------
const submitMock = vi.fn()

const { toastErrorMock } = vi.hoisted(() => ({ toastErrorMock: vi.fn() }))
vi.mock("sonner", () => ({
  toast: { error: toastErrorMock },
}))

vi.mock("@langchain/langgraph-sdk/react", () => ({
  useStream: () => ({
    messages: [],
    submit: submitMock,
    isLoading: false,
    stop: () => {},
  }),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}))

const updateMetadataMock = vi.fn().mockResolvedValue({})
vi.mock("@/lib/api/threads", () => ({
  fetchThreads: vi.fn().mockResolvedValue([
    {
      thread_id: "t1",
      status: "idle",
      metadata: {
        thread_assistant_id: "a1",
        thread_model: "anthropic:claude-sonnet-4-6",
        thread_model_base_url: null,
      },
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    } satisfies ThreadRead,
  ]),
  fetchThreadState: vi.fn().mockResolvedValue([]),
  updateThreadMetadata: (...args: unknown[]) => updateMetadataMock(...args),
  deleteThread: vi.fn(),
  createThread: vi.fn(),
}))

const models: ModelRead[] = [
  {
    id: "1", display_name: "Sonnet 4.6", model_id: "anthropic:claude-sonnet-4-6",
    provider: "anthropic", description: null, base_url: null,
    is_active: true, is_default: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "2", display_name: "Llama 3", model_id: "ollama/llama3:8b",
    provider: "ollama", description: null, base_url: "http://localhost:11434",
    is_active: true, is_default: false,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
]

vi.mock("@/lib/hooks/useModels", () => ({
  useModels: () => ({ data: models, isLoading: false }),
}))

vi.mock("@/lib/store/auth", () => ({
  useAuthStore: ((selector: (s: { accessToken: string }) => unknown) =>
    selector({ accessToken: "token" })) as unknown as typeof import("@/lib/store/auth").useAuthStore,
}))

// ---- Helpers ---------------------------------------------------------------
const assistant: AssistantRead = {
  assistant_id: "a1", name: "A", description: null, graph_id: "basic_agent",
  config: {}, context: {}, metadata: {}, version: 1,
  created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
}

function wrap(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(createElement(QueryClientProvider, { client }, ui))
}

beforeEach(() => {
  submitMock.mockClear()
  updateMetadataMock.mockClear()
  toastErrorMock.mockClear()
})

// ---- Tests -----------------------------------------------------------------
describe("ChatView model switching", () => {
  it("switching model persists to thread metadata and uses it in the next submit", async () => {
    wrap(<ChatView threadId="t1" assistant={assistant} />)

    // Wait for the picker to render with the thread's current model.
    await waitFor(() =>
      expect(screen.getByRole("combobox")).toHaveTextContent("anthropic:claude-sonnet-4-6")
    )

    // Switch to llama3.
    // Use pointer-event bypass because Radix portal elements carry pointer-events:none in jsdom.
    const user = userEvent.setup({ pointerEventsCheck: 0 })
    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByText("ollama/llama3:8b"))

    // PATCH was fired with the new model + its base_url.
    await waitFor(() =>
      expect(updateMetadataMock).toHaveBeenCalledWith("t1", {
        thread_model: "ollama/llama3:8b",
        thread_model_base_url: "http://localhost:11434",
      })
    )

    // Type a message and send it.
    const textarea = screen.getByPlaceholderText(/Message/i)
    await user.type(textarea, "with llama")
    await user.keyboard("{Enter}")

    // submit() carried the new model in config.configurable.
    expect(submitMock).toHaveBeenCalledWith(
      { messages: [{ role: "human", content: "with llama" }] },
      { config: { configurable: { model: "ollama/llama3:8b", model_base_url: "http://localhost:11434" } } }
    )
  })

  it("reverts picker and shows toast when the PATCH fails", async () => {
    updateMetadataMock.mockRejectedValueOnce(new Error("network down"))

    const user = userEvent.setup({ pointerEventsCheck: 0 })
    wrap(<ChatView threadId="t1" assistant={assistant} />)

    // Wait for initial seed.
    await waitFor(() =>
      expect(screen.getByRole("combobox")).toHaveTextContent("anthropic:claude-sonnet-4-6")
    )

    // Switch to llama3 — PATCH will reject.
    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByText("ollama/llama3:8b"))

    // Toast was raised with the error message.
    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith("network down")
    )

    // Picker reverted to the original model.
    await waitFor(() =>
      expect(screen.getByRole("combobox")).toHaveTextContent("anthropic:claude-sonnet-4-6")
    )
  })
})
