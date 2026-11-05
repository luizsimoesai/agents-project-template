import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { ChevronDown } from "lucide-react"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import {
  Popover, PopoverContent, PopoverTrigger,
} from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import { useCreateAssistant, useUpdateAssistant } from "@/lib/hooks/useAssistants"
import { GRAPH_TYPES } from "@/lib/graph-types"
import { ASSISTANT_ICONS, DEFAULT_ICON_KEY, getAssistantIcon } from "@/lib/icon-map"
import type { AssistantRead } from "@/lib/types"

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  graph_id: z.string().min(1),
  system_prompt: z.string().optional(),
  icon: z.string().optional(),
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
  const [popoverOpen, setPopoverOpen] = useState(false)

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
      icon: (assistant?.metadata?.icon as string) ?? DEFAULT_ICON_KEY,
    },
  })

  const selectedGraphId = watch("graph_id")
  const selectedIconKey = watch("icon") ?? DEFAULT_ICON_KEY
  const SelectedIcon = getAssistantIcon(selectedIconKey)
  const selectedIconLabel = ASSISTANT_ICONS.find((i) => i.key === selectedIconKey)?.label ?? "Sparkles"

  async function onSubmit(data: FormData) {
    // Aegra enforces a UNIQUE (user_id, graph_id, config) index. Without a
    // discriminator, two assistants of the same graph type with the same
    // system_prompt (or both empty) collide with 409. We stamp a per-assistant
    // uuid as context.client_id — generated on create, preserved on edit so
    // the row's identity stays stable and edits don't collide with siblings.
    const existingClientId =
      typeof assistant?.context?.["client_id"] === "string"
        ? (assistant.context["client_id"] as string)
        : undefined
    const clientId = existingClientId ?? crypto.randomUUID()

    const payload = {
      name: data.name,
      description: data.description || undefined,
      graph_id: data.graph_id,
      context: {
        client_id: clientId,
        ...(data.system_prompt ? { system_prompt: data.system_prompt } : {}),
      },
      metadata: { icon: data.icon ?? DEFAULT_ICON_KEY },
    }
    try {
      if (assistant) {
        await updateAssistant.mutateAsync(payload)
        toast.success("Assistant updated")
      } else {
        await createAssistant.mutateAsync(payload)
        toast.success("Assistant created")
      }
      reset()
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
            {assistant ? "edit assistant" : "new assistant"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          {/* Graph type */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">agent type</Label>
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

          {/* Icon picker */}
          <div className="space-y-1.5">
            <Label>Icon</Label>
            <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
              <PopoverTrigger className="flex items-center gap-2.5 rounded-md border border-input bg-background px-3 py-2 text-sm hover:bg-accent transition-colors w-full">
                <div className="w-7 h-7 rounded-md bg-[#2a9d8f] flex items-center justify-center shrink-0">
                  <SelectedIcon size={14} className="text-white" />
                </div>
                <span className="flex-1 text-left text-foreground">{selectedIconLabel}</span>
                <ChevronDown size={14} className="text-muted-foreground shrink-0" />
              </PopoverTrigger>
              <PopoverContent className="w-auto p-2" align="start">
                <div className="grid grid-cols-6 gap-1.5">
                  {ASSISTANT_ICONS.map((item) => {
                    const Icon = item.icon
                    const isSelected = item.key === selectedIconKey
                    return (
                      <button
                        key={item.key}
                        type="button"
                        title={item.label}
                        onClick={() => {
                          setValue("icon", item.key)
                          setPopoverOpen(false)
                        }}
                        className={cn(
                          "w-9 h-9 rounded-md flex items-center justify-center transition-colors",
                          isSelected
                            ? "bg-[#2a9d8f] text-white"
                            : "text-muted-foreground hover:bg-accent hover:text-foreground"
                        )}
                      >
                        <Icon size={16} />
                      </button>
                    )
                  })}
                </div>
              </PopoverContent>
            </Popover>
          </div>

          {/* Name */}
          <div className="space-y-1">
            <Label>Name</Label>
            <Input {...register("name")} />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-1">
            <Label>Description</Label>
            <Input {...register("description")} />
          </div>

          {/* System prompt */}
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
