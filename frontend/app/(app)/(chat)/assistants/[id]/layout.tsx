import type { Metadata } from "next"

type Params = Promise<{ id: string }>

export async function generateMetadata({
  params,
}: {
  params: Params
}): Promise<Metadata> {
  const { id } = await params
  // The assistant name is per-user and lives behind auth, so we can't enrich
  // server-side without forwarding credentials. A short id is enough to make
  // tabs/share previews distinguishable.
  return {
    title: `Assistant ${id.slice(0, 8)}`,
  }
}

export default function AssistantLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
