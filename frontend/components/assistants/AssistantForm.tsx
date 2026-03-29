"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from "@/components/ui/sheet"
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

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } =
    useForm<FormData>({
      resolver: zodResolver(schema),
      defaultValues: {
        name: assistant?.name ?? "",
        description: assistant?.description ?? "",
        model: (assistant?.context as { model?: string })?.model ?? "",
        system_prompt: (assistant?.context as { system_prompt?: string })?.system_prompt ?? "",
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
        toast.success("Assistente atualizado")
      } else {
        await createAssistant.mutateAsync(payload)
        toast.success("Assistente criado")
      }
      reset()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao salvar assistente")
    }
  }

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[400px] sm:w-[480px]">
        <SheetHeader>
          <SheetTitle className="font-mono">
            {assistant ? "editar assistente" : "novo assistente"}
          </SheetTitle>
        </SheetHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div className="space-y-1">
            <Label>nome</Label>
            <Input {...register("name")} />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="space-y-1">
            <Label>descrição</Label>
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
              placeholder="Você é um assistente útil..."
              className="font-mono text-sm min-h-[120px]"
            />
          </div>
          <div className="flex gap-2 pt-2">
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? "salvando..." : "salvar"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              cancelar
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  )
}
