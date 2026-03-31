"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { useProfile, useUpdateProfile } from "@/lib/hooks/useProfile"

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email"),
})

type FormData = z.infer<typeof schema>

export default function ProfilePage() {
  const { data: user, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<FormData>({
      resolver: zodResolver(schema),
      values: { name: user?.name ?? "", email: user?.email ?? "" },
    })

  async function onSubmit(data: FormData) {
    try {
      await updateProfile.mutateAsync(data)
      toast.success("Profile updated")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update profile")
    }
  }

  if (isLoading) {
    return (
      <div className="p-8 max-w-3xl space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-2xl w-full">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-xl font-mono font-semibold" style={{ color: "#2a9d8f" }}>
          profile
        </h1>
        {user?.is_admin && <Badge variant="outline" className="font-mono text-xs">admin</Badge>}
        {!user?.is_active && <Badge variant="destructive" className="font-mono text-xs">inactive</Badge>}
      </div>

      <Card className="border-border">
        <CardHeader>
          <CardTitle className="font-mono text-sm">account details</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input {...register("name")} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Email</Label>
              <Input type="email" {...register("email")} />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-1">
              <Label className="text-muted-foreground">id</Label>
              <p className="font-mono text-xs text-muted-foreground">{user?.id}</p>
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "saving..." : "save"}
            </Button>
          </CardContent>
        </form>
      </Card>
    </div>
  )
}
