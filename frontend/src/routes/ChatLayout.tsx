import { Outlet, useLocation, useParams } from "react-router"
import { DualSidebar } from "@/components/layout/DualSidebar"

function pageTitle(id?: string, threadId?: string): string | null {
  if (threadId) return `Conversation ${threadId.slice(0, 8)} · Agent Studio`
  if (id) return `Assistant ${id.slice(0, 8)} · Agent Studio`
  return null
}

export default function ChatLayout() {
  const { pathname } = useLocation()
  const { id, threadId } = useParams()
  const isUtilityPage = pathname.startsWith("/profile") || pathname.startsWith("/admin")
  const title = pageTitle(id, threadId)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {title && <title>{title}</title>}
      <DualSidebar />
      {/* Keyed by pathname so pages remount (and scroll resets) when a route
          param changes; ChatView keeps per-thread state in refs. Query-string
          changes keep the page mounted, so stripping ?msg= doesn't end a stream. */}
      <main key={pathname} className={isUtilityPage ? "flex-1 overflow-auto flex items-start justify-center p-8" : "flex-1 overflow-hidden"}>
        <Outlet />
      </main>
    </div>
  )
}
