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
    graph_id: "basic_agent",
    label: "Quick Assistant",
    description: "Answers questions and executes tasks using tools. Ideal for general use.",
  },
  {
    graph_id: "deep_agent",
    label: "Research Assistant",
    description: "Plans complex tasks step by step, researches information, and produces detailed reports.",
  },
]

export function getGraphType(graphId: string): GraphType | undefined {
  return GRAPH_TYPES.find((g) => g.graph_id === graphId)
}
