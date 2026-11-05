import { useEffect } from "react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, render, screen, waitFor } from "@testing-library/react"
import { createMemoryRouter, RouterProvider } from "react-router"
import ChatLayout from "./ChatLayout"

vi.mock("@/components/layout/DualSidebar", () => ({ DualSidebar: () => null }))

let mounts = 0

function Page() {
  useEffect(() => {
    mounts += 1
  }, [])
  return <p>page</p>
}

function renderAt(url: string) {
  const router = createMemoryRouter(
    [
      {
        element: <ChatLayout />,
        children: [
          { path: "profile", element: <Page /> },
          { path: "assistants/:id/threads", element: <Page /> },
          { path: "assistants/:id/threads/:threadId", element: <Page /> },
        ],
      },
    ],
    { initialEntries: [url] },
  )
  render(<RouterProvider router={router} />)
  return router
}

describe("ChatLayout", () => {
  beforeEach(() => {
    mounts = 0
    document.title = "Agent Studio"
  })

  it("remounts the page when the thread changes", async () => {
    const router = renderAt("/assistants/a/threads/t1")
    await screen.findByText("page")
    expect(mounts).toBe(1)

    await act(() => router.navigate("/assistants/a/threads/t2"))

    await waitFor(() => expect(mounts).toBe(2))
  })

  it("keeps the page mounted when only the query string changes", async () => {
    const router = renderAt("/assistants/a/threads/t1?msg=hi")
    await screen.findByText("page")

    await act(() => router.navigate("/assistants/a/threads/t1", { replace: true }))

    expect(router.state.location.search).toBe("")
    expect(mounts).toBe(1)
  })

  it("titles a thread by its short id", async () => {
    renderAt("/assistants/a/threads/abcdefgh-1234")
    await waitFor(() => expect(document.title).toBe("Conversation abcdefgh · Agent Studio"))
  })

  it("titles an assistant by its short id", async () => {
    renderAt("/assistants/12345678-abcd/threads")
    await waitFor(() => expect(document.title).toBe("Assistant 12345678 · Agent Studio"))
  })

  it("falls back to the default title on pages without an id", async () => {
    const router = renderAt("/assistants/12345678-abcd/threads")
    await waitFor(() => expect(document.title).toBe("Assistant 12345678 · Agent Studio"))

    await act(() => router.navigate("/profile"))

    await waitFor(() => expect(document.title).toBe("Agent Studio"))
  })
})
