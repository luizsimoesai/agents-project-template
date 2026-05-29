import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ChatInput } from "./ChatInput"
import type { ModelRead } from "@/lib/types"

const models: ModelRead[] = [
  {
    id: "1", display_name: "Claude", model_id: "anthropic:claude-sonnet-4-6",
    provider: "anthropic", description: null, base_url: null,
    is_active: true, is_default: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
]

describe("ChatInput", () => {
  it("shows a notice and keeps send disabled when no models exist", async () => {
    render(
      <ChatInput
        onSubmit={vi.fn()} onStop={vi.fn()} isStreaming={false}
        models={[]} selectedModelId="" onModelChange={vi.fn()}
      />,
    )
    expect(screen.getByText(/no model configured/i)).toBeInTheDocument()
    await userEvent.type(screen.getByPlaceholderText(/message/i), "hello")
    // Only the send button is present (no model-picker combobox).
    expect(screen.getByRole("button")).toBeDisabled()
  })

  it("enables send after typing when models exist", async () => {
    render(
      <ChatInput
        onSubmit={vi.fn()} onStop={vi.fn()} isStreaming={false}
        models={models} selectedModelId="anthropic:claude-sonnet-4-6"
        onModelChange={vi.fn()}
      />,
    )
    expect(screen.queryByText(/no model configured/i)).not.toBeInTheDocument()
    await userEvent.type(screen.getByPlaceholderText(/message/i), "hello")
    expect(screen.getByRole("button")).not.toBeDisabled()
  })
})
