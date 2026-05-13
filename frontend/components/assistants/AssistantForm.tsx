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
import { GRAPH_TYPES } from "@/lib/graph-types"
import type { AssistantRead } from "@/lib/types"

const schema = z.object({
  name: z.string().min(1, "Nome obrigatório"),
  description: z.string().optional(),
  graph_id: z.string().min(1),
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
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    values: {
      name: assistant?.name ?? "",
      description: assistant?.description ?? "",
      graph_id: assistant?.graph_id ?? GRAPH_TYPES[0]?.graph_id ?? "agent",
      system_prompt:
        (assistant?.context as { system_prompt?: string })?.system_prompt ?? "",
    },
  })

  const selectedGraphId = watch("graph_id")

  async function onSubmit(data: FormData) {
    const payload = {
      name: data.name,
      description: data.description || undefined,
      graph_id: data.graph_id,
      context: {
        ...(data.system_prompt ? { system_prompt: data.system_prompt } : {}),
      },
    }
    try {
      if (assistant) {
        const { graph_id: _, ...updatePayload } = payload
        await updateAssistant.mutateAsync(updatePayload)
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
          {/* Graph type — cards in create mode, read-only label in edit mode */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">tipo de agente</Label>
            {assistant ? (
              <p className="text-sm text-muted-foreground">
                {GRAPH_TYPES.find((g) => g.graph_id === assistant.graph_id)?.label ?? assistant.graph_id}
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-2">
                {GRAPH_TYPES.map((g) => {
                  const selected = selectedGraphId === g.graph_id
                  return (
                    <button
                      key={g.graph_id}
                      type="button"
                      onClick={() => setValue("graph_id", g.graph_id)}
                      className={[
                        "text-left rounded-lg border px-4 py-3 transition-colors",
                        selected
                          ? "border-[#2a9d8f] bg-[#2a9d8f]/8"
                          : "border-border/60 hover:border-[#2a9d8f]/40 hover:bg-[#2a9d8f]/5",
                      ].join(" ")}
                    >
                      <p className={["text-sm font-medium", selected ? "text-[#2a9d8f]" : "text-foreground"].join(" ")}>
                        {g.label}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">{g.description}</p>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

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
