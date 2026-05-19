import type { Metadata } from "next"

type Params = Promise<{ id: string; threadId: string }>

export async function generateMetadata({
  params,
}: {
  params: Params
}): Promise<Metadata> {
  const { threadId } = await params
  return {
    title: `Conversation ${threadId.slice(0, 8)}`,
  }
}

export default function ThreadLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
