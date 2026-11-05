import { Outlet } from "react-router"
import { IconRail } from "@/components/layout/IconRail"

export default function PickerLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <IconRail />
      <main className="flex-1 overflow-auto"><Outlet /></main>
    </div>
  )
}
