interface Message {
  text: string;
}
interface ToolCall {
  name: string;
  status: "running" | "done";
}

interface Props {
  messages: Message[] | string[];
  toolCalls: ToolCall[];
  isActive: boolean;
}

const AGENT_ICONS: Record<string, string> = {
  engagement_monitor: "📡",
  offer_generator:    "⚡",
  offer_approver:     "📨",
  get_fan_context:    "🔍",
  query_game_state:   "🏟️",
  send_fan_notification: "📬",
};

function agentIcon(name: string) {
  for (const [key, icon] of Object.entries(AGENT_ICONS)) {
    if (name.toLowerCase().includes(key)) return icon;
  }
  return "🤖";
}

export function OfferPipeline({ messages, toolCalls, isActive }: Props) {
  const items = messages.map((m) => ({ type: "msg" as const, text: typeof m === "string" ? m : m.text }));

  return (
    <div className="rounded-2xl border border-white/10 overflow-hidden"
      style={{background: "linear-gradient(160deg, #1A3350 0%, #152C45 100%)"}}>
      {/* Top bar */}
      <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between"
        style={{background: "linear-gradient(90deg, rgba(11,61,31,0.3) 0%, transparent 80%)"}}>
        <div className="flex items-center gap-2">
          <span className="text-sm">🤖</span>
          <span className="font-display text-[11px] font-semibold tracking-widest text-brand-chalk/50 uppercase">
            Agent Pipeline
          </span>
        </div>
        {isActive && (
          <div className="flex items-center gap-1.5 bg-brand-orange/10 border border-brand-orange/30 rounded-full px-2.5 py-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-orange animate-pulse" />
            <span className="text-brand-orange text-[10px] font-display font-semibold uppercase tracking-widest">Running</span>
          </div>
        )}
      </div>

      <div className="p-5 min-h-[160px]">
        {items.length === 0 && toolCalls.length === 0 ? (
          <div className="flex items-center gap-2 text-brand-chalk/20 text-sm">
            <span className="text-xl">🎯</span> Waiting for trigger…
          </div>
        ) : (
          <div className="space-y-2.5">
            {/* Tool calls as "plays" */}
            {toolCalls.map((tc, i) => (
              <div key={i} className={`flex items-center gap-3 rounded-lg px-3 py-2 border text-sm
                ${tc.status === "running"
                  ? "bg-brand-orange/5 border-brand-orange/20"
                  : "bg-brand-grass/5 border-brand-grass/20"}`}>
                <span className="text-base">{agentIcon(tc.name)}</span>
                <span className="font-mono text-[11px] text-white/60 flex-1">{tc.name}</span>
                <span className={tc.status === "running" ? "text-brand-orange text-xs animate-pulse" : "text-brand-grass text-xs"}>
                  {tc.status === "running" ? "▶ running" : "✓ done"}
                </span>
              </div>
            ))}

            {/* Messages as narrative */}
            {items.map((item, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-brand-chalk/70 leading-relaxed pl-1 border-l-2 border-brand-field/60 py-0.5 ml-1">
                <span className="text-brand-chalk/30 text-xs mt-0.5 font-mono">{String(i + 1).padStart(2, "0")}</span>
                <span>{item.text}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
