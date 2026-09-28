"use client";
import { useState, useEffect } from "react";
import { clsx } from "clsx";
import type { FanProfile, FanDetail } from "@/lib/types";
import { useFanSearch } from "@/lib/useFanSearch";

const TIERS = ["Platinum", "Gold", "Silver", "Bronze"] as const;

const SECTION_GROUPS = [
  {
    id: "field-vip",
    label: "Field Level / VIP",
    icon: "⭐",
    hint: "Sideline seats · premium concessions nearby",
    sections: ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"],
  },
  {
    id: "end-zone-merch",
    label: "Merch Hub",
    icon: "🛍️",
    hint: "Near main merchandise stands",
    sections: ["EZ1", "EZ2", "EZ3", "EZ4", "EZ5", "EZ6", "EZ7", "EZ8"],
  },
  {
    id: "club-level",
    label: "Club Level",
    icon: "🏅",
    hint: "Club access · upscale F&B · shorter queues",
    sections: ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"],
  },
  {
    id: "upper-deck",
    label: "Upper Deck",
    icon: "🥤",
    hint: "Value zone · less crowded concessions",
    sections: ["U1", "U2", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "U10"],
  },
] as const;

const TIER_COLORS: Record<string, string> = {
  Platinum: "border-blue-400/50 text-blue-300 bg-blue-400/10",
  Gold:     "border-brand-gold/50 text-brand-gold bg-brand-gold/10",
  Silver:   "border-slate-400/50 text-slate-300 bg-slate-400/10",
  Bronze:   "border-orange-500/50 text-orange-300 bg-orange-500/10",
};

interface Props {
  selectedFan: FanProfile | null;
  onSelect: (fan: FanProfile | null) => void;
}

export function FanSelector({ selectedFan, onSelect }: Props) {
  const [mode, setMode] = useState<"tier" | "section">("tier");
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [filterText, setFilterText] = useState("");
  const { fans, loading, error, search, reset } = useFanSearch();

  // Fan detail state — fetched when a fan is selected
  const [detail, setDetail] = useState<FanDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const selectedFanId = selectedFan?.fanId;

  useEffect(() => {
    if (!selectedFanId) { setDetail(null); return; }
    setDetailLoading(true);
    fetch(`/api/agents/fans/${encodeURIComponent(selectedFanId)}`)
      .then((r) => r.json())
      .then((d) => setDetail(d))
      .catch(() => setDetail(null))
      .finally(() => setDetailLoading(false));
  }, [selectedFanId]);

  function handleSearch() {
    setFilterText("");
    if (mode === "tier" && selectedTier) {
      search("tier", selectedTier);
    } else if (mode === "section" && selectedGroup) {
      const group = SECTION_GROUPS.find((g) => g.id === selectedGroup)!;
      search("section", selectedGroup, [...group.sections]);
    }
    onSelect(null);
  }

  function handleModeSwitch(m: "tier" | "section") {
    setMode(m);
    setSelectedTier(null);
    setSelectedGroup(null);
    setFilterText("");
    reset();
    onSelect(null);
  }

  const canSearch = mode === "tier" ? !!selectedTier : !!selectedGroup;
  const q = filterText.trim().toLowerCase();
  const visibleFans = q
    ? fans.filter((f) =>
        (f.fanName ?? f.fanId).toLowerCase().includes(q) ||
        f.fanId.toLowerCase().includes(q) ||
        (f.preferredSectionId ?? "").toLowerCase().includes(q)
      )
    : fans;
  const eligibleCount = visibleFans.filter((f) => !f.offerFatigued).length;

  return (
    <div className="rounded-2xl border border-white/10 overflow-hidden"
      style={{ background: "linear-gradient(160deg, #1A3350 0%, #0F1F35 100%)" }}>
      {/* Header */}
      <div className="h-1 bg-gradient-to-r from-brand-field via-brand-gold to-brand-field" />
      <div className="px-5 pt-4 pb-3 border-b border-white/5">
        <div className="font-display text-[10px] font-semibold tracking-widest text-brand-chalk/40 uppercase mb-3">
          🎯 Target Fans
        </div>
        {/* Mode tabs */}
        <div className="flex gap-2">
          {(["tier", "section"] as const).map((m) => (
            <button
              key={m}
              onClick={() => handleModeSwitch(m)}
              className={clsx(
                "flex-1 py-2 rounded-lg text-xs font-display font-semibold uppercase tracking-wider transition-all border",
                mode === m
                  ? "bg-brand-gold/15 border-brand-gold/50 text-brand-gold"
                  : "bg-white/3 border-white/10 text-brand-chalk/40 hover:text-brand-chalk/70"
              )}
            >
              {m === "tier" ? "🏅 By Tier" : "🏟️ By Section"}
            </button>
          ))}
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Tier selector */}
        {mode === "tier" && (
          <div className="grid grid-cols-2 gap-2">
            {TIERS.map((tier) => (
              <button
                key={tier}
                onClick={() => setSelectedTier(tier)}
                className={clsx(
                  "py-2.5 px-3 rounded-xl border text-sm font-display font-semibold tracking-wide transition-all",
                  selectedTier === tier
                    ? TIER_COLORS[tier] + " shadow-md"
                    : "border-white/10 text-brand-chalk/40 hover:border-white/20 hover:text-brand-chalk/70"
                )}
              >
                {tier}
              </button>
            ))}
          </div>
        )}

        {/* Section group selector */}
        {mode === "section" && (
          <div className="space-y-2">
            {SECTION_GROUPS.map((g) => (
              <button
                key={g.id}
                onClick={() => setSelectedGroup(g.id)}
                className={clsx(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border text-left transition-all",
                  selectedGroup === g.id
                    ? "border-brand-gold/50 bg-brand-gold/10"
                    : "border-white/8 hover:border-white/20"
                )}
              >
                <span className="text-xl flex-shrink-0">{g.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className={clsx(
                    "text-sm font-display font-semibold",
                    selectedGroup === g.id ? "text-brand-gold" : "text-brand-chalk/70"
                  )}>{g.label}</div>
                  <div className="text-[10px] text-brand-chalk/35 mt-0.5">{g.hint} · {g.sections.join(", ")}</div>
                </div>
                {selectedGroup === g.id && <span className="text-brand-gold text-xs">✓</span>}
              </button>
            ))}
          </div>
        )}

        {/* Search button */}
        <button
          onClick={handleSearch}
          disabled={!canSearch || loading}
          className={clsx(
            "w-full py-3 rounded-xl font-display font-bold text-xs tracking-widest uppercase transition-all border",
            canSearch && !loading
              ? "bg-gradient-to-r from-brand-grass to-brand-field border-brand-grass/50 text-white hover:shadow-lg hover:shadow-brand-grass/20 active:scale-[0.98]"
              : "bg-white/3 border-white/8 text-brand-chalk/25 cursor-not-allowed"
          )}
        >
          {loading ? "⏳ Querying Data Agent…" : "🔍 Find Fans"}
        </button>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-brand-red/30 bg-brand-red/5 px-3 py-2.5 text-xs text-red-300">
            ⚠️ {error}
          </div>
        )}

        {/* Results */}
        {fans.length > 0 && (
          <div>
            {/* Filter input */}
            <div className="relative mb-2">
              <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-brand-chalk/30 text-xs pointer-events-none">🔎</span>
              <input
                type="text"
                value={filterText}
                onChange={(e) => { setFilterText(e.target.value); onSelect(null); }}
                placeholder="Filter by name, ID or section…"
                className="w-full rounded-lg pl-7 pr-3 py-2 text-xs text-brand-chalk placeholder-brand-chalk/30 focus:outline-none focus:ring-1 focus:ring-brand-gold/40 transition-all"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}
              />
              {filterText && (
                <button
                  onClick={() => { setFilterText(""); onSelect(null); }}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-brand-chalk/30 hover:text-brand-chalk/70 text-xs"
                >✕</button>
              )}
            </div>

            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-display font-semibold tracking-widest text-brand-chalk/35 uppercase">
                {visibleFans.length} of {fans.length} fan{fans.length !== 1 ? "s" : ""}
              </span>
              {eligibleCount > 0 && (
                <span className="text-[10px] text-brand-grass font-display">
                  {eligibleCount} eligible
                </span>
              )}
            </div>

            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {visibleFans.map((fan) => {
                const isSelected = selectedFan?.fanId === fan.fanId;
                const tier = fan.loyaltyTier ?? "";
                return (
                  <button
                    key={fan.fanId}
                    disabled={fan.offerFatigued}
                    onClick={() => onSelect(isSelected ? null : fan)}
                    className={clsx(
                      "w-full text-left rounded-xl border px-3 py-2.5 transition-all",
                      fan.offerFatigued
                        ? "opacity-40 cursor-not-allowed border-white/5 bg-white/2"
                        : isSelected
                          ? "border-brand-gold/60 bg-brand-gold/8 shadow-md shadow-brand-gold/10"
                          : "border-white/10 hover:border-white/25 hover:bg-white/3"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={clsx(
                          "text-[10px] font-display font-bold px-1.5 py-0.5 rounded border flex-shrink-0",
                          TIER_COLORS[tier] ?? "border-white/20 text-white/50 bg-white/5"
                        )}>
                          {tier.slice(0, 4).toUpperCase()}
                        </span>
                        <span className={clsx(
                          "font-display font-semibold text-sm truncate",
                          isSelected ? "text-brand-gold" : fan.offerFatigued ? "text-brand-chalk/40" : "text-white"
                        )}>
                          {fan.fanName || fan.fanId}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {fan.offerFatigued ? (
                          <span className="text-[9px] text-orange-400/70 font-display uppercase tracking-wide border border-orange-500/20 bg-orange-500/5 rounded px-1.5 py-0.5">
                            Fatigued
                          </span>
                        ) : (
                          <span className="text-[10px] text-brand-chalk/30 font-mono">
                            {fan.preferredSectionId}
                          </span>
                        )}
                        {isSelected && <span className="text-brand-gold text-xs">✓</span>}
                      </div>
                    </div>

                    {/* Engagement bar */}
                    {!fan.offerFatigued && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="flex-1 h-1 rounded-full bg-white/8 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${(fan.baseEngagementScore ?? 0) * 100}%`,
                              backgroundColor:
                                fan.baseEngagementScore < 0.4 ? "#DC2626"
                                : fan.baseEngagementScore < 0.65 ? "#F5A623"
                                : "#16A34A",
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-brand-chalk/30 w-8 text-right">
                          {(fan.baseEngagementScore ?? 0).toFixed(2)}
                        </span>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Fan detail panel */}
        {selectedFan && (
          <div className="rounded-xl border border-brand-gold/30 bg-gradient-to-b from-brand-gold/5 to-transparent overflow-hidden">
            {/* Header */}
            <div className="px-4 pt-3 pb-2 border-b border-white/5">
              <div className="text-[9px] font-display text-brand-gold/60 uppercase tracking-widest mb-1">
                Selected Fan
              </div>
              <div className="flex items-center gap-2">
                <span className={clsx(
                  "text-[10px] font-display font-bold px-1.5 py-0.5 rounded border flex-shrink-0",
                  TIER_COLORS[selectedFan.loyaltyTier] ?? "border-white/20 text-white/50 bg-white/5"
                )}>
                  {selectedFan.loyaltyTier.toUpperCase()}
                </span>
                <span className="font-display font-bold text-white text-sm">
                  {selectedFan.fanName}
                </span>
                <span className="text-[10px] font-mono text-brand-chalk/35 ml-auto">
                  {selectedFan.preferredSectionId}
                </span>
              </div>
            </div>

            {detailLoading && (
              <div className="px-4 py-3 text-[11px] text-brand-chalk/40 font-display">
                Loading fan intel…
              </div>
            )}

            {detail && !detailLoading && (
              <div className="px-4 py-3 space-y-3">
                {/* Why this fan — computed insight */}
                <div className="rounded-lg bg-white/3 border border-white/6 px-3 py-2">
                  <div className="text-[9px] font-display font-semibold tracking-widest text-brand-gold/60 uppercase mb-1">
                    Why Target?
                  </div>
                  <p className="text-[11px] text-brand-chalk/70 leading-relaxed">
                    {detail.baseEngagementScore < 0.4
                      ? "Low engagement — ideal moment to re-activate with a targeted offer."
                      : detail.baseEngagementScore < 0.65
                      ? "Moderate engagement — a timely incentive can convert to purchase."
                      : "High engagement — fan is in the zone; use a premium upsell."}
                    {detail.churnRiskScore > 0.6 &&
                      " Elevated churn risk — retention offer recommended."}
                  </p>
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { label: "Avg Spend", value: `$${detail.avgSpendPerGame.toFixed(0)}` },
                    { label: "Concession", value: `$${detail.avgConcessionSpend.toFixed(0)}` },
                    { label: "Merch", value: `$${detail.avgMerchandiseSpend.toFixed(0)}` },
                  ].map(({ label, value }) => (
                    <div key={label} className="rounded-lg bg-white/3 border border-white/6 px-2 py-2 text-center">
                      <div className="text-[9px] text-brand-chalk/35 uppercase tracking-wide font-display">{label}</div>
                      <div className="text-sm font-display font-bold text-white mt-0.5">{value}</div>
                    </div>
                  ))}
                </div>

                {/* Engagement + Churn bars */}
                <div className="space-y-1.5">
                  {[
                    { label: "Engagement", value: detail.baseEngagementScore,
                      color: detail.baseEngagementScore < 0.4 ? "#DC2626" : detail.baseEngagementScore < 0.65 ? "#F5A623" : "#16A34A" },
                    { label: "Churn Risk", value: detail.churnRiskScore,
                      color: detail.churnRiskScore > 0.6 ? "#DC2626" : detail.churnRiskScore > 0.35 ? "#F5A623" : "#16A34A" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="flex items-center gap-2">
                      <span className="text-[9px] font-display text-brand-chalk/40 w-16 flex-shrink-0">{label}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-white/8 overflow-hidden">
                        <div className="h-full rounded-full transition-all" style={{ width: `${value * 100}%`, backgroundColor: color }} />
                      </div>
                      <span className="text-[10px] font-mono text-brand-chalk/40 w-8 text-right">{value.toFixed(2)}</span>
                    </div>
                  ))}
                </div>

                {/* Recent offers */}
                {detail.recentOffers.length > 0 && (
                  <div>
                    <div className="text-[9px] font-display font-semibold tracking-widest text-brand-chalk/35 uppercase mb-1.5">
                      Recent Offers
                    </div>
                    <div className="space-y-1.5">
                      {detail.recentOffers.slice(0, 3).map((o) => (
                        <div key={o.promoId} className="flex items-center gap-2 rounded-lg bg-white/2 border border-white/5 px-2.5 py-1.5">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] font-display font-semibold text-brand-chalk/70 capitalize">
                                {o.offerCategory.replace("_", " ")}
                              </span>
                              <span className="text-[9px] font-mono text-brand-gold/60">
                                ${o.offerValue.toFixed(0)}
                              </span>
                            </div>
                            <div className="text-[9px] text-brand-chalk/30 capitalize">
                              {o.triggerContext.replace("_", " ")} · {o.channel}
                            </div>
                          </div>
                          <span className={clsx(
                            "text-[9px] font-display uppercase tracking-wide px-1.5 py-0.5 rounded border flex-shrink-0",
                            o.outcome === "accepted"
                              ? "border-brand-grass/40 text-brand-grass bg-brand-grass/5"
                              : o.outcome === "redeemed"
                              ? "border-blue-400/40 text-blue-300 bg-blue-400/5"
                              : "border-white/10 text-brand-chalk/30 bg-white/2"
                          )}>
                            {o.outcome}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
