"use client"

import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Bot } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { login } from "@/lib/api/auth"

const schema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(1, "Password is required"),
})

type FormData = z.infer<typeof schema>

export function LoginForm({ className, ...props }: React.ComponentProps<"div">) {
  const router = useRouter()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    try {
      await login(data.email, data.password)
      router.push("/assistants")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Login failed")
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card className="overflow-hidden p-0">
        <CardContent className="grid p-0 md:grid-cols-2">
          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="p-6 md:p-8 flex flex-col gap-6">
            <div className="flex flex-col items-center gap-2 text-center">
              <h1 className="text-2xl font-bold">Welcome back</h1>
              <p className="text-sm text-muted-foreground">
                Sign in to your Agent Chat account
              </p>
            </div>

            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" placeholder="m@example.com" {...register("email")} />
                {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" {...register("password")} />
                {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
              </div>

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Signing in…" : "Sign in"}
              </Button>
            </div>

            <p className="text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link href="/signup" className="underline underline-offset-4 hover:text-foreground">
                Sign up
              </Link>
            </p>
          </form>

          {/* Brand panel */}
          <div className="relative hidden md:flex flex-col justify-between p-8 bg-[#07080d] overflow-hidden">
            {/* Dot grid */}
            <div
              className="absolute inset-0"
              style={{
                backgroundImage: "radial-gradient(circle, rgba(42,157,143,0.18) 1px, transparent 1px)",
                backgroundSize: "28px 28px",
              }}
            />
            {/* Glow */}
            <div className="absolute top-0 left-0 w-64 h-64 rounded-full bg-[#2a9d8f]/10 blur-[100px] -translate-x-1/2 -translate-y-1/2" />
            <div className="absolute bottom-0 right-0 w-48 h-48 rounded-full bg-[#2a9d8f]/8 blur-[80px] translate-x-1/3 translate-y-1/3" />

            {/* Logo */}
            <div className="relative z-10 flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-md bg-[#2a9d8f] flex items-center justify-center">
                <Bot size={15} className="text-white" />
              </div>
              <span className="font-mono text-xs tracking-[0.2em] uppercase text-white/50">
                Agent Chat
              </span>
            </div>

            {/* Headline */}
            <div className="relative z-10 space-y-4">
              <p className="font-mono text-[10px] tracking-[0.3em] uppercase text-[#2a9d8f]">
                LangGraph · Aegra
              </p>
              <h2 className="text-3xl font-bold text-white leading-tight tracking-tight">
                Conversation<br />
                at machine<br />
                scale.
              </h2>
              <p className="text-sm text-white/35 leading-relaxed">
                A ReAct agent framework for building intelligent, multi-turn AI workflows.
              </p>
            </div>

            {/* Footer */}
            <div className="relative z-10 font-mono text-[10px] text-white/20 tracking-widest uppercase">
              Powered by LangGraph + Aegra
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
