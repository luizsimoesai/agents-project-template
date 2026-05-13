"use client"

import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useCreateModel, useUpdateModel } from "@/lib/hooks/useModels"
import type { ModelRead } from "@/lib/types"

const PROVIDERS = ["anthropic", "openai", "ollama", "custom"] as const

const schema = z.object({
  display_name: z.string().min(1, "Nome obrigatório"),
  model_id: z.string().min(1, "Model ID obrigatório"),
  provider: z.enum(PROVIDERS),
  description: z.string().optional(),
  base_url: z.string().url("URL inválida").optional().or(z.literal("")),
  is_active: z.boolean(),
  is_default: z.boolean(),
})

type FormData = z.infer<typeof schema>

interface ModelFormProps {
  open: boolean
  onClose: () => void
  model?: ModelRead
}

export function ModelForm({ open, onClose, model }: ModelFormProps) {
  const createModel = useCreateModel()
  const updateModel = useUpdateModel(model?.id ?? "")

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: "",
      model_id: "",
      provider: "anthropic",
      description: "",
      base_url: "",
      is_active: true,
      is_default: false,
    },
  })

  useEffect(() => {
    if (model) {
      reset({
        display_name: model.display_name,
        model_id: model.model_id,
        provider: model.provider as (typeof PROVIDERS)[number],
        description: model.description ?? "",
        base_url: model.base_url ?? "",
        is_active: model.is_active,
        is_default: model.is_default,
      })
    } else {
      reset({
        display_name: "",
        model_id: "",
        provider: "anthropic",
        description: "",
        base_url: "",
        is_active: true,
        is_default: false,
      })
    }
  }, [model, open, reset])

  const selectedProvider = watch("provider")
  const isActive = watch("is_active")
  const isDefault = watch("is_default")

  async function onSubmit(data: FormData) {
    const payload = {
      display_name: data.display_name,
      model_id: data.model_id,
      provider: data.provider,
      description: data.description || undefined,
      base_url: data.base_url || undefined,
      is_active: data.is_active,
      is_default: data.is_default,
    }
    try {
      if (model) {
        const { model_id: _, provider: __, ...updatePayload } = payload
        await updateModel.mutateAsync(updatePayload)
        toast.success("Modelo atualizado")
      } else {
        await createModel.mutateAsync(payload)
        toast.success("Modelo criado")
      }
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
            {model ? "editar modelo" : "novo modelo"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          <div className="space-y-1">
            <Label className="font-mono text-xs">display_name</Label>
            <Input {...register("display_name")} placeholder="Claude Sonnet 4.6" />
            {errors.display_name && (
              <p className="text-xs text-destructive">{errors.display_name.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">model_id</Label>
            <Input
              {...register("model_id")}
              placeholder="anthropic/claude-sonnet-4-6"
              className="font-mono text-sm"
              disabled={!!model}
            />
            {errors.model_id && (
              <p className="text-xs text-destructive">{errors.model_id.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">provider</Label>
            {model ? (
              <p className="text-sm text-muted-foreground font-mono">{model.provider}</p>
            ) : (
              <Select
                value={selectedProvider}
                onValueChange={(v) => setValue("provider", v as (typeof PROVIDERS)[number])}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">description</Label>
            <Textarea
              {...register("description")}
              placeholder="Descrição opcional"
              className="font-mono text-sm min-h-16"
            />
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">base_url</Label>
            <Input
              {...register("base_url")}
              placeholder="https://litellm.empresa.com/v1"
              className="font-mono text-sm"
            />
            {errors.base_url && (
              <p className="text-xs text-destructive">{errors.base_url.message}</p>
            )}
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setValue("is_active", e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-mono">ativo</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setValue("is_default", e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-mono">padrão</span>
            </label>
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
