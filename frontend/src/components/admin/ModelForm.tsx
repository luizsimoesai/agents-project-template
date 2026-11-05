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
import { useCreateModel, useUpdateModel } from "@/lib/hooks/useModels"
import type { ModelRead } from "@/lib/types"

const schema = z.object({
  display_name: z.string().min(1, "Name is required"),
  model_id: z.string().min(1, "Model ID is required"),
  provider: z.string().min(1, "Provider is required"),
  description: z.string().optional(),
  base_url: z.string().url("Invalid URL").optional().or(z.literal("")),
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
      provider: "",
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
        provider: model.provider,
        description: model.description ?? "",
        base_url: model.base_url ?? "",
        is_active: model.is_active,
        is_default: model.is_default,
      })
    } else {
      reset({
        display_name: "",
        model_id: "",
        provider: "",
        description: "",
        base_url: "",
        is_active: true,
        is_default: false,
      })
    }
  }, [model, open, reset])

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
        toast.success("Model updated")
      } else {
        await createModel.mutateAsync(payload)
        toast.success("Model created")
      }
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm">
            {model ? "edit model" : "new model"}
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
            <p className="text-xs text-muted-foreground">
              Format{" "}
              <code className="font-mono text-foreground/70">provider/model</code>{" "}
              — the prefix is the LangChain integration that builds the client
              (anthropic, openai, ollama, openrouter), not the vendor&apos;s
              catalog label. For OpenRouter, keep their slug after the prefix:{" "}
              <code className="font-mono text-foreground/70">
                openrouter/openai/gpt-4.1-mini
              </code>
              .
            </p>
            {errors.model_id && (
              <p className="text-xs text-destructive">{errors.model_id.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">provider</Label>
            {model ? (
              <p className="text-sm text-muted-foreground font-mono">{model.provider}</p>
            ) : (
              <Input
                {...register("provider")}
                placeholder="anthropic"
                className="font-mono text-sm"
              />
            )}
            <p className="text-xs text-muted-foreground">
              Label for display only — routing is driven by the{" "}
              <code className="font-mono text-foreground/70">model_id</code> prefix.
            </p>
            {errors.provider && (
              <p className="text-xs text-destructive">{errors.provider.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <Label className="font-mono text-xs">description</Label>
            <Textarea
              {...register("description")}
              placeholder="Optional description"
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
              <span className="text-sm font-mono">active</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setValue("is_default", e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-mono">default</span>
            </label>
          </div>

          <div className="flex gap-2 pt-1">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
              style={{ backgroundColor: "#2a9d8f" }}
            >
              {isSubmitting ? "saving..." : "save"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              cancel
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
