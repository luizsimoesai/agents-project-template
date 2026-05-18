import { Workflow } from "lucide-react"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <div className="w-full max-w-sm flex flex-col items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-md bg-[#2a9d8f] flex items-center justify-center shrink-0">
            <Workflow size={16} className="text-white" />
          </div>
          <span className="font-semibold text-sm tracking-tight">Agent Studio</span>
        </div>
        {children}
      </div>
    </div>
  )
}
