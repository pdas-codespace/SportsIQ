"use client";
import { useSportConfig } from "@/lib/useSportConfig";

interface TimelineEntry {
  label: string;
  status: "done" | "active" | "pending";
  timestamp?: string;
}

interface Props {
  entries: TimelineEntry[];
}

const STATIC_PLAY_ICONS: Record<string, string> = {
  "monitor":  "📡",
  "signal":   "📡",
  "offer":    "⚡",
  "generat":  "⚡",
  "approv":   "🚦",
  "human":    "🧑‍⚖️",
  "email":    "📬",
  "sent":     "📬",
  "complete": "🏆",
  "connect":  "🔗",
};

export function StatusTimeline({ entries }: Props) {
  const { emoji, criticalMomentLabel } = useSportConfig();
  const doneCount = entries.filter(e => e.status === "done").length;
  const progress = entries.length > 0 ? (doneCount / entries.length) * 100 : 0;

  function playIcon(label: string) {
    const l = label.toLowerCase();
    if (l.includes("start")) return emoji;
    for (const [key, icon] of Object.entries(STATIC_PLAY_ICONS)) {
      if (l.includes(key)) return icon;
    }
    return "▸";
  }

  return (
    <div className="rounded-2xl border border-white/10 overflow-hidden"
      style={{background: "linear-gradient(160deg, #1A3350 0%, #152C45 100%)"}}>
      {/* Header bar */}
      <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between"
        style={{background: "linear-gradient(90deg, rgba(11,61,31,0.2) 0%, transparent 80%)"}}>
        <span className="font-display text-[11px] font-semibold tracking-widest text-brand-chalk/50 uppercase">
          {emoji} Play-by-Play
        </span>
        <span className="text-[10px] text-brand-chalk/30 font-mono">
          {doneCount}/{entries.length} plays
        </span>
      </div>

      {/* Progress bar */}
      {entries.length > 0 && (
        <div className="px-5 pt-3 pb-1">
          <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
            <div className="h-full rounded-full bg-gradient-to-r from-brand-field to-brand-grass transition-all duration-700"
              style={{width: `${progress}%`}} />
          </div>
          <div className="flex justify-between mt-0.5">
            <span className="text-[9px] text-brand-chalk/20">Start</span>
            <span className="text-[9px] text-brand-chalk/20">{criticalMomentLabel}</span>
          </div>
        </div>
      )}

      <div className="px-5 pb-5 pt-2 space-y-2.5">
        {entries.length === 0 && (
          <div className="text-brand-chalk/20 text-sm py-3">No plays yet…</div>
        )}
        {entries.map((e, i) => (
          <div key={i} className={`flex items-start gap-3 rounded-lg px-3 py-2.5 transition-all border
            ${e.status === "done"
              ? "bg-brand-grass/5 border-brand-grass/15"
              : e.status === "active"
              ? "bg-brand-gold/8 border-brand-gold/30 shadow-sm shadow-brand-gold/10"
              : "bg-transparent border-white/5 opacity-40"
            }`}>
            <div className={`mt-0.5 text-sm flex-shrink-0 ${
              e.status === "active" ? "animate-pulse" : ""
            }`}>
              {e.status === "done" ? "✅" : e.status === "active" ? playIcon(e.label) : "○"}
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-display ${
                e.status === "done" ? "text-brand-chalk/60 line-through decoration-brand-chalk/20"
                : e.status === "active" ? "text-brand-gold font-semibold"
                : "text-brand-chalk/25"
              }`}>
                {e.label}
              </div>
              {e.timestamp && (
                <div className="text-[10px] text-brand-chalk/25 mt-0.5 font-mono">{e.timestamp}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
