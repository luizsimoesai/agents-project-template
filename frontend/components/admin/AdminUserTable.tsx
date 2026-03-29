"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Trash2, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useUsers, useActivateUser, useDeactivateUser, useDeleteUser,
} from "@/lib/hooks/useUsers"
import { useAuthStore } from "@/lib/store/auth"

type StatusFilter = "all" | "active" | "inactive"

export function AdminUserTable() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<StatusFilter>("all")
  const currentUser = useAuthStore((s) => s.user)

  const { data: users, isLoading } = useUsers()
  const activateUser = useActivateUser()
  const deactivateUser = useDeactivateUser()
  const deleteUser = useDeleteUser()

  const filtered = (users ?? [])
    .filter((u) => {
      if (filter === "active") return u.is_active
      if (filter === "inactive") return !u.is_active
      return true
    })
    .filter((u) =>
      search ? u.name?.toLowerCase().includes(search.toLowerCase()) : true
    )

  async function handleToggleActive(id: string, isActive: boolean) {
    try {
      if (isActive) {
        await deactivateUser.mutateAsync(id)
        toast.success("Usuário desativado")
      } else {
        await activateUser.mutateAsync(id)
        toast.success("Usuário ativado")
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro")
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteUser.mutateAsync(id)
      toast.success("Usuário apagado")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao apagar usuário")
    }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-2 items-center flex-wrap">
        <Input
          placeholder="buscar por nome..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-[240px] font-mono text-sm"
        />
        {(["all", "active", "inactive"] as StatusFilter[]).map((f) => (
          <Button
            key={f}
            variant={filter === f ? "default" : "outline"}
            size="sm"
            className="font-mono text-xs"
            onClick={() => setFilter(f)}
            style={filter === f ? { backgroundColor: "#136ddd" } : {}}
          >
            {f === "all" ? "todos" : f === "active" ? "ativos" : "inativos"}
          </Button>
        ))}
      </div>

      {/* Table */}
      <div className="border border-border rounded-md overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-mono text-xs">nome</TableHead>
              <TableHead className="font-mono text-xs">email</TableHead>
              <TableHead className="font-mono text-xs">status</TableHead>
              <TableHead className="font-mono text-xs">criado em</TableHead>
              <TableHead className="font-mono text-xs w-[80px]">ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 4 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 5 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : filtered.map((u) => (
                  <TableRow key={u.id} className={u.id === currentUser?.id ? "bg-accent/30" : ""}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-1">
                        {u.name ?? "—"}
                        {u.is_admin && <ShieldCheck size={12} style={{ color: "#136ddd" }} />}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{u.email}</TableCell>
                    <TableCell>
                      <Badge
                        variant={u.is_active ? "outline" : "secondary"}
                        className="font-mono text-xs cursor-pointer"
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                      >
                        {u.is_active ? "ativo" : "inativo"}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {new Date(u.created_at).toLocaleDateString("pt-BR")}
                    </TableCell>
                    <TableCell>
                      <AlertDialog>
                        <AlertDialogTrigger
                          render={
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-destructive hover:bg-destructive/10"
                              disabled={u.id === currentUser?.id}
                            />
                          }
                        >
                          <Trash2 size={12} />
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle className="font-mono">apagar usuário?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Esta ação é permanente. O usuário <strong>{u.email}</strong> será removido.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>cancelar</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(u.id)}
                              className="bg-destructive hover:bg-destructive/90"
                            >
                              apagar
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground font-mono">
        {filtered.length} usuário{filtered.length !== 1 ? "s" : ""}
      </p>
    </div>
  )
}
