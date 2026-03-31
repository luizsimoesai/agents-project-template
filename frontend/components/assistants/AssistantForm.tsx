"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useCreateAssistant, useUpdateAssistant } from "@/lib/hooks/useAssistants"
import type { AssistantRead } from "@/lib/types"

const schema = z.object({
  name: z.string().min(1, "Nome obrigatório"),
  description: z.string().optional(),
  model: z.string().optional(),
  system_prompt: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface AssistantFormProps {
  open: boolean
  onClose: () => void
  assistant?: AssistantRead
}

export function AssistantForm({ open, onClose, assistant }: AssistantFormProps) {
  const createAssistant = useCreateAssistant()
  const updateAssistant = useUpdateAssistant(assistant?.assistant_id ?? "")

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    values: {
      name: assistant?.name ?? "",
      description: assistant?.description ?? "",
      model: (assistant?.context as { model?: string })?.model ?? "",
      system_prompt:
        (assistant?.context as { system_prompt?: string })?.system_prompt ?? "",
    },
  })

  async function onSubmit(data: FormData) {
    const payload = {
      name: data.name,
      description: data.description || undefined,
      context: {
        ...(data.model ? { model: data.model } : {}),
        ...(data.system_prompt ? { system_prompt: data.system_prompt } : {}),
      },
    }
    try {
      if (assistant) {
        await updateAssistant.mutateAsync(payload)
        toast.success("Assistant atualizado")
      } else {
        await createAssistant.mutateAsync(payload)
        toast.success("Assistant criado")
      }
      reset()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Falha ao salvar")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">
            {assistant ? "editar assistant" : "novo assistant"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          <div className="space-y-1">
            <Label>Nome</Label>
            <Input {...register("name")} />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>
          <div className="space-y-1">
            <Label>Descrição</Label>
            <Input {...register("description")} />
          </div>
          <div className="space-y-1">
            <Label className="font-mono text-xs">model</Label>
            <Input
              {...register("model")}
              placeholder="anthropic/claude-sonnet-4-6"
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label className="font-mono text-xs">system_prompt</Label>
            <Textarea
              {...register("system_prompt")}
              placeholder="You are a helpful assistant..."
              className="font-mono text-sm min-h-28"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
              style={{ backgroundColor: "#2a9d8f" }}
            >
              {isSubmitting ? "salvando..." : "salvar"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              cancelar
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
