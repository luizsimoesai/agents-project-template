import {
  Sparkles,
  Brain,
  Zap,
  Workflow,
  Cpu,
  Network,
  Search,
  Code,
  Database,
  Globe,
  Microscope,
  Shield,
  type LucideIcon,
} from "lucide-react"

export interface AssistantIcon {
  key: string
  label: string
  icon: LucideIcon
}

export const ASSISTANT_ICONS: AssistantIcon[] = [
  { key: "sparkles",   label: "Sparkles",   icon: Sparkles   },
  { key: "brain",      label: "Brain",      icon: Brain      },
  { key: "zap",        label: "Zap",        icon: Zap        },
  { key: "workflow",   label: "Workflow",   icon: Workflow   },
  { key: "cpu",        label: "CPU",        icon: Cpu        },
  { key: "network",    label: "Network",    icon: Network    },
  { key: "search",     label: "Search",     icon: Search     },
  { key: "code",       label: "Code",       icon: Code       },
  { key: "database",   label: "Database",   icon: Database   },
  { key: "globe",      label: "Globe",      icon: Globe      },
  { key: "microscope", label: "Microscope", icon: Microscope },
  { key: "shield",     label: "Shield",     icon: Shield     },
]

export const DEFAULT_ICON_KEY = "sparkles"

export function getAssistantIcon(key?: string): LucideIcon {
  return ASSISTANT_ICONS.find((i) => i.key === key)?.icon ?? Sparkles
}
