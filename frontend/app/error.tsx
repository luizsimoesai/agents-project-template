"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-8">
      <div className="text-center space-y-4 max-w-md">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-destructive">
          Error
        </p>
        <h1 className="text-2xl font-semibold text-foreground">
          Something went wrong
        </h1>
        <p className="text-sm text-muted-foreground">
          An unexpected error occurred. Try again, and if the problem persists
          contact support.
        </p>
        {error.digest && (
          <p className="font-mono text-[11px] text-muted-foreground/70">
            digest: {error.digest}
          </p>
        )}
        <Button variant="outline" className="mt-2" onClick={reset}>
          Try again
        </Button>
      </div>
    </div>
  )
}
