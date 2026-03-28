export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm px-4">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-mono font-bold" style={{ color: "#136ddd" }}>
            agent_chat
          </h1>
        </div>
        {children}
      </div>
    </div>
  )
}
