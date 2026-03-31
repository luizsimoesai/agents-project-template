import { IconRail } from "@/components/layout/IconRail"

export default function PickerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <IconRail />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  )
}
