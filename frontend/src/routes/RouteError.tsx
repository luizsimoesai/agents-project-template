import { useEffect } from "react"
import { useRouteError } from "react-router"
import { Button } from "@/components/ui/button"

export default function RouteError() {
  const error = useRouteError()

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
        <Button variant="outline" className="mt-2" onClick={() => window.location.reload()}>
          Try again
        </Button>
      </div>
    </div>
  )
}
