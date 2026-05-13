"use client"

import { useState } from "react"
import { toast } from "sonner"
import { Pencil, Plus, Star, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { useAllModels, useDeleteModel, useSetModelDefault } from "@/lib/hooks/useModels"
import { ModelForm } from "./ModelForm"
import type { ModelRead } from "@/lib/types"

export function AdminModelTable() {
  const [formOpen, setFormOpen] = useState(false)
  const [editingModel, setEditingModel] = useState<ModelRead | undefined>()
  const { data: models, isLoading } = useAllModels()
  const deleteModel = useDeleteModel()
  const setDefault = useSetModelDefault()

  function handleEdit(model: ModelRead) {
    setEditingModel(model)
    setFormOpen(true)
  }

  function handleNew() {
    setEditingModel(undefined)
    setFormOpen(true)
  }

  async function handleDelete(id: string) {
    try {
      await deleteModel.mutateAsync(id)
      toast.success("Modelo removido")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao remover")
    }
  }

  async function handleSetDefault(model: ModelRead) {
    try {
      await setDefault.mutateAsync(model.id)
      toast.success(`"${model.display_name}" definido como padrão`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao definir padrão")
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button
          size="sm"
          className="font-mono text-xs gap-1"
          style={{ backgroundColor: "#2a9d8f" }}
          onClick={handleNew}
        >
          <Plus size={12} />
          novo modelo
        </Button>
      </div>

      <div className="border border-border rounded-md overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-mono text-xs">nome</TableHead>
              <TableHead className="font-mono text-xs">model_id</TableHead>
              <TableHead className="font-mono text-xs">provider</TableHead>
              <TableHead className="font-mono text-xs">base_url</TableHead>
              <TableHead className="font-mono text-xs">status</TableHead>
              <TableHead className="font-mono text-xs w-[120px]">ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-full" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : (models ?? []).map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-1">
                        {m.display_name}
                        {m.is_default && (
                          <Star size={12} style={{ color: "#2a9d8f" }} />
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{m.model_id}</TableCell>
                    <TableCell className="font-mono text-xs">{m.provider}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground truncate max-w-[160px]">
                      {m.base_url ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={m.is_active ? "outline" : "secondary"}
                        className="font-mono text-xs"
                      >
                        {m.is_active ? "ativo" : "inativo"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleEdit(m)}
                        >
                          <Pencil size={12} />
                        </Button>
                        {!m.is_default && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-foreground"
                            title="Definir como padrão"
                            onClick={() => handleSetDefault(m)}
                          >
                            <Star size={12} />
                          </Button>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger
                            render={
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 text-destructive hover:bg-destructive/10"
                                disabled={m.is_default}
                                title={
                                  m.is_default
                                    ? "Não é possível deletar o modelo padrão"
                                    : "Deletar"
                                }
                              />
                            }
                          >
                            <Trash2 size={12} />
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle className="font-mono">
                                deletar modelo?
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                O modelo <strong>{m.display_name}</strong> será removido
                                permanentemente.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>cancelar</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDelete(m.id)}
                                className="bg-destructive hover:bg-destructive/90"
                              >
                                deletar
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground font-mono">
        {(models ?? []).length} modelo{(models ?? []).length !== 1 ? "s" : ""}
      </p>

      <ModelForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        model={editingModel}
      />
    </div>
  )
}
