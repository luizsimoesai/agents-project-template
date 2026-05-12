/**
 * User-facing metadata for each graph registered in backend/aegra.json.
 *
 * Convention: whenever you add or remove a graph in aegra.json, update this
 * file accordingly so the frontend reflects the change in the assistant
 * creation flow.
 *
 * Fields:
 *   graph_id    — must match the key in aegra.json → "graphs"
 *   label       — short name shown to the end user
 *   description — one sentence explaining what this agent does
 */
export interface GraphType {
  graph_id: string
  label: string
  description: string
}

export const GRAPH_TYPES: GraphType[] = [
  {
    graph_id: "agent",
    label: "Assistente Rápido",
    description: "Responde perguntas e executa tarefas usando ferramentas. Ideal para uso geral.",
  },
  {
    graph_id: "deep_agent",
    label: "Assistente de Pesquisa",
    description: "Planeia tarefas complexas em etapas, pesquisa informação e produz relatórios detalhados.",
  },
]

export function getGraphType(graphId: string): GraphType | undefined {
  return GRAPH_TYPES.find((g) => g.graph_id === graphId)
}
