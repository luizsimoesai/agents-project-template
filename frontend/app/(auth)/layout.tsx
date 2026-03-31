import { Bot } from "lucide-react"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-[45%] flex-col justify-between p-12 bg-[#07080d] relative overflow-hidden shrink-0">
        {/* Dot grid */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: "radial-gradient(circle, rgba(19,109,221,0.18) 1px, transparent 1px)",
            backgroundSize: "28px 28px",
          }}
        />
        {/* Radial glow */}
        <div className="absolute top-0 left-0 w-125 h-125 rounded-full bg-[#136ddd]/10 blur-[120px] -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 right-0 w-75 h-75 rounded-full bg-[#136ddd]/8 blur-[80px] translate-x-1/3 translate-y-1/3" />

        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-md bg-[#136ddd] flex items-center justify-center">
              <Bot size={15} className="text-white" />
            </div>
            <span className="font-mono text-xs tracking-[0.2em] uppercase text-white/50">
              Agent Chat
            </span>
          </div>
        </div>

        {/* Headline */}
        <div className="relative z-10 space-y-5">
          <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-[#136ddd]">
            LangGraph · Aegra
          </p>
          <h2 className="text-[2.6rem] font-bold text-white leading-[1.1] tracking-tight">
            Conversation<br />
            at machine<br />
            scale.
          </h2>
          <p className="text-sm text-white/35 leading-relaxed max-w-xs">
            A ReAct agent framework for building intelligent, multi-turn AI workflows.
          </p>
        </div>

        {/* Footer */}
        <div className="relative z-10 font-mono text-[10px] text-white/20 tracking-widest uppercase">
          Powered by LangGraph + Aegra
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-md bg-[#136ddd] flex items-center justify-center">
              <Bot size={13} className="text-white" />
            </div>
            <span className="font-mono text-sm font-semibold" style={{ color: "#136ddd" }}>
              Agent Chat
            </span>
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
