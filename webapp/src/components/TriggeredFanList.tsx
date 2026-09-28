import { clsx } from "clsx";
import { useState, useMemo } from "react";
import type { TriggeredFan } from "@/lib/types";

const TIER_COLORS: Record<string, string> = {
  Platinum: "text-sky-300 border-sky-400/50 bg-sky-400/10",
  Gold:     "text-brand-gold border-brand-gold/50 bg-brand-gold/10",
  Silver:   "text-slate-300 border-slate-400/40 bg-slate-400/10",
  Bronze:   "text-amber-600 border-amber-600/40 bg-amber-600/10",
};

const URGENCY_BAR_COLOR = (score: number) =>
  score < 0.3 ? "bg-red-500" : score < 0.45 ? "bg-orange-400" : "bg-yellow-400";

interface Props {
  scanState: "idle" | "scanning" | "ready";
  breakLabel: string | null;
  triggeredFans: TriggeredFan[];
  selectedFanId: string | null;
  onSelectFan: (fan: TriggeredFan) => void;
}

export function TriggeredFanList({ scanState, breakLabel, triggeredFans, selectedFanId, onSelectFan }: Props) {
  const [tierFilter, setTierFilter] = useState<string | null>(null);
  const [sectionFilter, setSectionFilter] = useState<string | null>(null);

  const tiers = useMemo(() => [...new Set(triggeredFans.map((f) => f.loyaltyTier))], [triggeredFans]);
  const sections = useMemo(() => [...new Set(triggeredFans.map((f) => f.preferredSectionId).filter(Boolean))], [triggeredFans]);

  const filtered = useMemo(
    () =>
      triggeredFans.filter(
        (f) =>
          (!tierFilter || f.loyaltyTier === tierFilter) &&
          (!sectionFilter || f.preferredSectionId === sectionFilter)
      ),
    [triggeredFans, tierFilter, sectionFilter]
  );

  return (
    <div className="rounded-2xl border border-white/10 overflow-hidden"
      style={{ background: "linear-gradient(160deg, #111B2A 0%, #0C1622 100%)" }}>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <span className="text-sm font-display font-semibold text-white/80 uppercase tracking-widest">
            Triggered Fans
          </span>
          {scanState === "ready" && (
            <span className="text-[10px] font-display bg-red-500/15 border border-red-500/30 text-red-400 px-2 py-0.5 rounded-full uppercase tracking-wide">
              {triggeredFans.length} disengaged
            </span>
          )}
        </div>
        {breakLabel && scanState === "ready" && (
          <span className="text-[10px] text-brand-gold/60 font-display uppercase tracking-wide">{breakLabel}</span>
        )}
      </div>

      {/* Idle state */}
      {scanState === "idle" && (
        <div className="flex flex-col items-center justify-center py-12 px-6 text-center gap-3">
          <div className="text-3xl opacity-30">📡</div>
          <div className="text-sm text-white/30 font-display uppercase tracking-widest">
            Simulate a break to identify disengaged fans
          </div>
        </div>
      )}

      {/* Scanning state */}
      {scanState === "scanning" && (
        <div className="flex flex-col items-center justify-center py-12 px-6 gap-4">
          <div className="w-8 h-8 rounded-full border-2 border-brand-grass/40 border-t-brand-grass animate-spin" />
          <div className="text-sm text-brand-grass/70 font-display uppercase tracking-widest animate-pulse">
            Scanning Eventhouse…
          </div>
          {/* Skeleton cards */}
          <div className="w-full space-y-2 mt-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse" />
            ))}
          </div>
        </div>
      )}

      {/* Ready state */}
      {scanState === "ready" && (
        <div>
          {/* Filters */}
          {(tiers.length > 1 || sections.length > 1) && (
            <div className="px-4 py-2 border-b border-white/5 flex flex-wrap gap-1.5">
              {tiers.length > 1 && (
                <>
                  <button
                    onClick={() => setTierFilter(null)}
                    className={clsx(
                      "text-[10px] px-2 py-0.5 rounded-full font-display uppercase tracking-wide border transition-all",
                      !tierFilter
                        ? "bg-brand-gold/20 border-brand-gold/50 text-brand-gold"
                        : "border-white/10 text-white/30 hover:text-white/60"
                    )}
                  >All tiers</button>
                  {tiers.map((t) => (
                    <button key={t}
                      onClick={() => setTierFilter(tierFilter === t ? null : t)}
                      className={clsx(
                        "text-[10px] px-2 py-0.5 rounded-full font-display uppercase tracking-wide border transition-all",
                        tierFilter === t
                          ? TIER_COLORS[t] || "bg-white/10 border-white/30 text-white"
                          : "border-white/10 text-white/30 hover:text-white/60"
                      )}
                    >{t}</button>
                  ))}
                </>
              )}
              {sections.length > 1 && (
                <>
                  <div className="w-px bg-white/10" />
                  {sections.map((s) => (
                    <button key={s}
                      onClick={() => setSectionFilter(sectionFilter === s ? null : s)}
                      className={clsx(
                        "text-[10px] px-2 py-0.5 rounded-full font-display uppercase tracking-wide border transition-all",
                        sectionFilter === s
                          ? "bg-white/15 border-white/40 text-white"
                          : "border-white/10 text-white/30 hover:text-white/60"
                      )}
                    >§{s}</button>
                  ))}
                </>
              )}
            </div>
          )}

          {/* Fan cards */}
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-sm text-white/30 font-display uppercase tracking-widest">
              No fans match the current filter
            </div>
          ) : (
            <div className="divide-y divide-white/5 max-h-[420px] overflow-y-auto">
              {filtered.map((fan) => (
                <button
                  key={fan.fanId}
                  onClick={() => onSelectFan(fan)}
                  className={clsx(
                    "w-full text-left px-4 py-3 transition-all duration-150",
                    selectedFanId === fan.fanId
                      ? "bg-brand-gold/10 border-l-2 border-brand-gold"
                      : "hover:bg-white/5 border-l-2 border-transparent"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-display font-semibold text-sm text-white truncate">
                          {fan.fanName}
                        </span>
                        <span className={clsx(
                          "text-[9px] font-display uppercase tracking-wide border px-1.5 py-0.5 rounded-full shrink-0",
                          TIER_COLORS[fan.loyaltyTier] || "text-white/50 border-white/20"
                        )}>
                          {fan.loyaltyTier}
                        </span>
                        {fan.offerFatigued && (
                          <span className="text-[9px] font-display text-amber-400/70 border border-amber-400/30 px-1.5 py-0.5 rounded-full shrink-0 uppercase">
                            Fatigued
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] text-white/40 font-mono">
                        §{fan.preferredSectionId}
                        {fan.quarter && ` · Q${fan.quarter}`}
                        {fan.gameMinute && ` · ${fan.gameMinute}m`}
                        {fan.churnRiskScore > 0 && ` · Churn ${Math.round(fan.churnRiskScore * 100)}%`}
                      </div>
                    </div>

                    {/* Engagement score */}
                    <div className="shrink-0 text-right">
                      <div className="font-display text-lg font-bold text-red-400 tabular-nums leading-none">
                        {fan.currentEngagementScore.toFixed(2)}
                      </div>
                      <div className="text-[9px] text-white/30 uppercase tracking-wide">
                        ↓{fan.engagementDropAmount.toFixed(2)}
                      </div>
                    </div>
                  </div>

                  {/* Urgency bar */}
                  <div className="mt-2 h-1 rounded-full overflow-hidden bg-white/5">
                    <div
                      className={clsx("h-full rounded-full transition-all", URGENCY_BAR_COLOR(fan.currentEngagementScore))}
                      style={{ width: `${(1 - fan.currentEngagementScore) * 100}%` }}
                    />
                  </div>
                  <div className="mt-1 text-[9px] text-white/25 font-mono truncate">{fan.triggerReason}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
