import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import { ToolCallBadge, type RenderedToolCall } from "./ToolCallBadge"

interface ChatMessageProps {
  role: string
  content: string
  isStreaming?: boolean
  toolCalls?: RenderedToolCall[]
}

export function ChatMessage({ role, content, isStreaming = false, toolCalls }: ChatMessageProps) {
  const isAI = role === "ai" || role === "assistant"

  return (
    <div className={cn("group py-5 px-6", isAI ? "bg-transparent" : "")}>
      <div className="flex items-center gap-2 mb-2.5">
        <div
          className={cn(
            "w-1.5 h-1.5 rounded-full shrink-0",
            isAI ? "bg-[#2a9d8f]" : "bg-muted-foreground/50"
          )}
        />
        <span
          className={cn(
            "font-mono text-[10px] uppercase tracking-[0.18em] font-medium",
            isAI ? "text-[#2a9d8f]" : "text-muted-foreground"
          )}
        >
          {isAI ? "assistant" : "you"}
        </span>
      </div>

      <div className={cn("pl-4.5 text-sm leading-7", isAI ? "text-foreground" : "text-foreground/75 whitespace-pre-wrap")}>
        {/* Tool call badges — shown before the AI text response */}
        {isAI && toolCalls && toolCalls.length > 0 && (
          <div className="flex flex-col gap-1 mb-3">
            {toolCalls.map((tc) => (
              <ToolCallBadge key={tc.id} tc={tc} />
            ))}
          </div>
        )}

        {isAI ? (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                h1: ({ children }) => <h1 className="text-xl font-semibold mt-5 mb-2">{children}</h1>,
                h2: ({ children }) => <h2 className="text-lg font-semibold mt-4 mb-2">{children}</h2>,
                h3: ({ children }) => <h3 className="text-base font-semibold mt-3 mb-1">{children}</h3>,
                ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="leading-7">{children}</li>,
                code: ({ className, children, ...props }) => {
                  const isBlock = className?.includes("language-")
                  return isBlock ? (
                    <code
                      className={cn(
                        "block bg-muted/60 border border-border/60 rounded-lg px-4 py-3 font-mono text-xs overflow-x-auto mb-3",
                        className
                      )}
                      {...props}
                    >
                      {children}
                    </code>
                  ) : (
                    <code
                      className="bg-muted/60 border border-border/50 rounded px-1.5 py-0.5 font-mono text-xs"
                      {...props}
                    >
                      {children}
                    </code>
                  )
                },
                pre: ({ children }) => <pre className="mb-3 last:mb-0">{children}</pre>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-[#2a9d8f]/50 pl-4 text-foreground/70 italic mb-3">
                    {children}
                  </blockquote>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#2a9d8f] underline underline-offset-2 hover:text-[#2a9d8f]/80"
                  >
                    {children}
                  </a>
                ),
                hr: () => <hr className="border-border/40 my-4" />,
                table: ({ children }) => (
                  <div className="overflow-x-auto mb-3">
                    <table className="w-full text-sm border-collapse">{children}</table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="border border-border/60 px-3 py-2 bg-muted/40 font-semibold text-left">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="border border-border/60 px-3 py-2">{children}</td>
                ),
              }}
            >
              {content}
            </ReactMarkdown>
            {isStreaming && (
              <span
                data-testid="streaming-cursor"
                className="inline-block w-0.5 h-3.75 bg-[#2a9d8f] ml-0.5 align-middle"
                style={{ animation: "blink 1s steps(1) infinite" }}
              />
            )}
          </>
        ) : (
          <>
            {content}
            {isStreaming && (
              <span
                data-testid="streaming-cursor"
                className="inline-block w-0.5 h-3.75 bg-[#2a9d8f] ml-0.5 align-middle"
                style={{ animation: "blink 1s steps(1) infinite" }}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}
