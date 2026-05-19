import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ChatMessage } from "./ChatMessage"

describe("ChatMessage", () => {
  it("renders assistant message with brand color label", () => {
    render(
      <ChatMessage role="ai" content="Olá! Como posso ajudar?" isStreaming={false} />
    )
    expect(screen.getByText("assistant")).toBeInTheDocument()
    expect(screen.getByText("Olá! Como posso ajudar?")).toBeInTheDocument()
    const label = screen.getByText("assistant")
    expect(label).toHaveClass("text-[#2a9d8f]")
  })

  it("renders human message with neutral label", () => {
    render(
      <ChatMessage role="human" content="Me ajuda com isso" isStreaming={false} />
    )
    expect(screen.getByText("you")).toBeInTheDocument()
  })

  it("shows streaming cursor when isStreaming is true", () => {
    render(
      <ChatMessage role="ai" content="Pensando..." isStreaming={true} />
    )
    expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument()
  })

  it("renders the model chip on AI messages when modelId is provided", () => {
    render(
      <ChatMessage role="ai" content="hi" modelId="anthropic:claude-sonnet-4-6" />
    )
    const chip = screen.getByTestId("model-chip")
    expect(chip).toBeInTheDocument()
    expect(chip).toHaveTextContent("anthropic:claude-sonnet-4-6")
  })

  it("does not render the chip when modelId is missing", () => {
    render(<ChatMessage role="ai" content="hi" />)
    expect(screen.queryByTestId("model-chip")).not.toBeInTheDocument()
  })

  it("does not render the chip on human messages even if modelId provided", () => {
    render(
      <ChatMessage role="human" content="hi" modelId="anthropic:claude-sonnet-4-6" />
    )
    expect(screen.queryByTestId("model-chip")).not.toBeInTheDocument()
  })
})
