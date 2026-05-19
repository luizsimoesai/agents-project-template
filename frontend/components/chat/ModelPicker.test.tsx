import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ModelPicker } from "./ModelPicker"
import type { ModelRead } from "@/lib/types"

const models: ModelRead[] = [
  {
    id: "1", display_name: "Claude Sonnet 4.6", model_id: "anthropic:claude-sonnet-4-6",
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

describe("ModelPicker", () => {
  it("renders the currently selected model", () => {
    render(<ModelPicker models={models} value="anthropic:claude-sonnet-4-6" onChange={() => {}} />)
    expect(screen.getByRole("combobox")).toHaveTextContent("anthropic:claude-sonnet-4-6")
  })

  it("calls onChange when the user picks a different model", async () => {
    const onChange = vi.fn()
    render(<ModelPicker models={models} value="anthropic:claude-sonnet-4-6" onChange={onChange} />)
    // Open the dropdown and pick the second model.
    await userEvent.click(screen.getByRole("combobox"))
    await userEvent.click(screen.getByText("ollama/llama3:8b"))
    expect(onChange).toHaveBeenCalledWith("ollama/llama3:8b")
  })

  it("renders nothing when models list is empty", () => {
    const { container } = render(<ModelPicker models={[]} value="" onChange={() => {}} />)
    expect(container.firstChild).toBeNull()
  })
})
