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
    expect(label).toHaveClass("text-[#136ddd]")
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
})
