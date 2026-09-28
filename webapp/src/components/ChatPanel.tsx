"use client";
import { useRef, useEffect, useState, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "@/lib/useChat";
import { useSportConfig } from "@/lib/useSportConfig";
import type { ChatMessage } from "@/lib/types";

const SUGGESTED_QUESTIONS = [
  "I am in charge of Concessions and Venue. Help me prepare for the match today.",
  "Top performing offer categories last month?",
  "Engagement score trends for Gold tier fans",
  "Most active concession zones this quarter?",
  "How much total annual revenue is at risk from fans with churn risk scores above 0.7?"
];

/** Renders markdown with GFM tables, lists, bold – styled to match the dark theme */
function AgentMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => (
          <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-brand-chalk">{children}</strong>
        ),
        ul: ({ children }) => (
          <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="text-brand-chalk/80">{children}</li>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto mb-2 -mx-1">
            <table className="w-full text-xs border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="border-b border-brand-gold/30">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-2 py-1 text-left font-semibold text-brand-gold/80 whitespace-nowrap">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-2 py-1 border-b border-white/5 text-brand-chalk/75">
            {children}
          </td>
        ),
        code: ({ children }) => (
          <code className="bg-white/10 rounded px-1 py-0.5 text-[11px] font-mono text-brand-gold/80">
            {children}
          </code>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function MessageBubble({ msg, agentEmoji }: { msg: ChatMessage; agentEmoji: string }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      {!isUser && (
        <div className="w-6 h-6 rounded-full bg-brand-field/60 border border-brand-gold/30 flex items-center justify-center text-xs mr-2 flex-shrink-0 mt-0.5">
          {agentEmoji}
        </div>
      )}
      <div
        className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-sm ${
          isUser
            ? "bg-brand-gold/15 border border-brand-gold/25 text-brand-chalk rounded-br-sm"
            : "border border-brand-field/60 text-brand-chalk/85 rounded-bl-sm"
        }`}
        style={isUser ? undefined : { background: "linear-gradient(160deg, #1A3350 0%, #0F1F35 100%)" }}
      >
        {isUser ? (
          <span className="leading-relaxed">{msg.content}</span>
        ) : (
          <AgentMessage content={msg.content} />
        )}
        <div className="text-[10px] text-brand-chalk/20 mt-1 text-right">
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  );
}

function ThinkingBubble({ agentEmoji }: { agentEmoji: string }) {
  return (
    <div className="flex justify-start mb-3">
      <div className="w-6 h-6 rounded-full bg-brand-field/60 border border-brand-gold/30 flex items-center justify-center text-xs mr-2 flex-shrink-0 mt-0.5">
        {agentEmoji}
      </div>
      <div
        className="rounded-2xl rounded-bl-sm px-4 py-3 border border-brand-field/60"
        style={{ background: "linear-gradient(160deg, #1A3350 0%, #0F1F35 100%)" }}
      >
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-brand-gold/60 animate-bounce [animation-delay:0ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-brand-gold/60 animate-bounce [animation-delay:150ms]" />
          <span className="w-1.5 h-1.5 rounded-full bg-brand-gold/60 animate-bounce [animation-delay:300ms]" />
          <span className="text-xs text-brand-chalk/40 ml-1">Querying Fabric…</span>
        </div>
      </div>
    </div>
  );
}

/** Self-contained floating chat widget — fixed to top-right below the header. */
export function ChatPanel({
  seedQuestion,
  onSeedConsumed,
}: {
  seedQuestion?: string;
  onSeedConsumed?: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const { messages, isLoading, error, sendMessage, reset } = useChat();
  const { emoji: agentEmoji } = useSportConfig();
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isOpen) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, isOpen]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 50);
  }, [isOpen]);

  // When a seed question arrives from the POS panel, open chat and send it
  useEffect(() => {
    if (seedQuestion) {
      setIsOpen(true);
      setTimeout(() => {
        sendMessage(seedQuestion);
        onSeedConsumed?.();
      }, 200);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedQuestion]);

  function handleSend() {
    if (!draft.trim()) return;
    sendMessage(draft);
    setDraft("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    if (e.key === "Escape") setIsOpen(false);
  }

  const isEmpty = messages.length === 0 && !isLoading;

  return (
    <>
      {/* Closed state — floating pill button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed z-50 flex items-center gap-2 px-4 py-2 rounded-full border border-brand-gold/30 hover:border-brand-gold/60 text-sm font-display font-semibold text-brand-chalk/80 hover:text-brand-chalk transition-all shadow-lg"
          style={{
            top: "80px",
            right: "20px",
            background: "linear-gradient(135deg, #0D2C54 0%, #0F1F35 100%)",
          }}
        >
          <span>🤖</span>
          <span>Ask Sports-IQ</span>
        </button>
      )}

      {/* Open state — overlay panel */}
      {isOpen && (
        <div
          className="fixed z-50 flex flex-col rounded-2xl border border-brand-gold/25 shadow-2xl overflow-hidden"
          style={{
            top: "80px",
            right: "20px",
            width: "420px",
            maxHeight: "calc(100vh - 100px)",
            background: "linear-gradient(160deg, #0D2C54 0%, #0F1F35 100%)",
          }}
        >
          {/* Panel header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-brand-gold/15 flex-shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-base">🤖</span>
              <div>
                <div className="font-display text-sm font-semibold text-brand-chalk leading-none">
                  Fabric IQ Chat
                </div>
                <div className="text-[10px] text-brand-chalk/30 mt-0.5">
                  Foundry · MicrosoftFabricIQTool
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button
                  onClick={reset}
                  className="text-[11px] text-brand-chalk/30 hover:text-brand-chalk/60 transition-colors px-2 py-1 rounded-lg hover:bg-white/5"
                >
                  Clear
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-brand-chalk/40 hover:text-brand-chalk/80 hover:bg-white/10 transition-all text-base leading-none"
                title="Close (Esc)"
              >
                ×
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 min-h-[200px]">
            {isEmpty && (
              <div className="flex flex-col items-center gap-4 py-4">
                <div className="text-center">
                  <div className="text-2xl mb-1.5">📊</div>
                  <div className="text-sm text-brand-chalk/40">Ask about your data estate</div>
                  <div className="text-[11px] text-brand-chalk/25 mt-0.5">
                    Fans · Offers · Engagement · Game context
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-1.5 w-full">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => { setDraft(q); inputRef.current?.focus(); }}
                      className="text-left text-xs text-brand-chalk/50 hover:text-brand-chalk/80 border border-brand-gold/10 hover:border-brand-gold/30 rounded-xl px-3 py-2 transition-all hover:bg-brand-gold/5"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} agentEmoji={agentEmoji} />
            ))}

            {isLoading && <ThinkingBubble agentEmoji={agentEmoji} />}

            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3.5 py-2.5 text-xs text-red-300 mb-3">
                <span className="font-semibold">Error: </span>{error}
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="px-3 pb-3 pt-2 border-t border-brand-gold/10 flex-shrink-0">
            <div className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                rows={1}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about fans, offers, engagement…"
                disabled={isLoading}
                className="flex-1 resize-none bg-white/5 border border-brand-gold/15 rounded-xl px-3 py-2 text-sm text-brand-chalk placeholder:text-brand-chalk/25 focus:outline-none focus:border-brand-gold/40 transition-colors disabled:opacity-50 leading-relaxed"
                style={{ minHeight: "38px", maxHeight: "100px" }}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = `${Math.min(el.scrollHeight, 100)}px`;
                }}
              />
              <button
                onClick={handleSend}
                disabled={!draft.trim() || isLoading}
                className="flex-shrink-0 w-9 h-9 rounded-xl bg-brand-gold/80 hover:bg-brand-gold disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-all text-brand-dark font-bold"
              >
                ↑
              </button>
            </div>
            <div className="text-[10px] text-brand-chalk/20 mt-1.5 text-center">
              Enter · Esc to close · ~10–30 s per response
            </div>
          </div>
        </div>
      )}
    </>
  );
}

