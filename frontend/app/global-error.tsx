"use client"

import { useEffect } from "react"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  // global-error replaces the root layout entirely, so we must render our own
  // <html> and <body>. Keep this file framework-agnostic — no Tailwind layer
  // assumptions, no fonts, no providers — because the root layout failed.
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, -apple-system, sans-serif",
          background: "#0a0a0a",
          color: "#f5f5f5",
          padding: "2rem",
        }}
      >
        <div style={{ maxWidth: 400, textAlign: "center" }}>
          <p
            style={{
              fontFamily: "ui-monospace, SFMono-Regular, monospace",
              fontSize: 11,
              letterSpacing: "0.2em",
              color: "#ef4444",
              textTransform: "uppercase",
              margin: "0 0 0.75rem",
            }}
          >
            Critical error
          </p>
          <h1 style={{ fontSize: 24, fontWeight: 600, margin: "0 0 1rem" }}>
            Application failed to load
          </h1>
          <p style={{ fontSize: 14, color: "#a3a3a3", margin: "0 0 1.5rem" }}>
            A fatal error prevented the app from rendering. Try reloading the
            page.
          </p>
          {error.digest && (
            <p
              style={{
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
                fontSize: 11,
                color: "#737373",
                margin: "0 0 1rem",
              }}
            >
              digest: {error.digest}
            </p>
          )}
          <button
            type="button"
            onClick={reset}
            style={{
              padding: "0.5rem 1rem",
              fontSize: 14,
              borderRadius: 6,
              border: "1px solid #404040",
              background: "transparent",
              color: "#f5f5f5",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  )
}
