"use client";
import { useState } from "react";
import { clsx } from "clsx";
import type { Offer } from "@/lib/types";

interface Props {
  offer: Offer;
  onDecide: (approved: boolean, reason: string) => void;
  decision?: { approved: boolean; reason: string };
}

const REJECTION_REASONS = [
  "Active stadium incident — F&B offers inappropriate",
  "Offer not relevant to current game moment",
  "Fan has already left the stadium",
  "Other",
];

const CATEGORY_CONFIG: Record<string, { icon: string; label: string; accent: string }> = {
  merchandise: { icon: "🛍️", label: "Merchandise", accent: "from-blue-900/40 to-indigo-950/20 border-blue-500/30" },
  food:        { icon: "🍺", label: "Food & Beverage", accent: "from-amber-900/30 to-yellow-950/20 border-yellow-600/30" },
  beverage:    { icon: "🍺", label: "Food & Beverage", accent: "from-amber-900/30 to-yellow-950/20 border-yellow-600/30" },
};
function catConfig(cat?: string) {
  if (!cat) return { icon: "🎁", label: "Offer", accent: "from-slate-900/40 to-slate-950/20 border-slate-500/30" };
  for (const [k, v] of Object.entries(CATEGORY_CONFIG)) {
    if (cat.toLowerCase().includes(k)) return v;
  }
  return { icon: "🎁", label: cat, accent: "from-slate-900/40 to-slate-950/20 border-slate-500/30" };
}

export function ApprovalCard({ offer, onDecide, decision }: Props) {
  const [showRejectMenu, setShowRejectMenu] = useState(false);
  const decided = !!decision;
  const cat = catConfig(offer.category);

  return (
    <div className={clsx(
      "rounded-2xl border overflow-hidden transition-all duration-300",
      decided
        ? decision!.approved
          ? "border-brand-grass/50 shadow-lg shadow-brand-grass/10"
          : "border-brand-red/40 shadow-lg shadow-brand-red/10"
        : "border-brand-gold/40 shadow-lg shadow-brand-gold/10"
    )}>
      {/* Category accent header */}
      <div className={`bg-gradient-to-r ${cat.accent} border-b border-current/10 px-5 py-3 flex items-center justify-between`}
        style={{borderBottomColor: "rgba(255,255,255,0.06)"}}>
        <div className="flex items-center gap-2">
          <span className="text-lg">{cat.icon}</span>
          <span className="font-display text-[10px] font-semibold tracking-widest text-brand-chalk/50 uppercase">
            {cat.label}
          </span>
        </div>
        {offer.incident_alert && (
          <div className="flex items-center gap-1.5 bg-brand-red/10 border border-brand-red/30 rounded-full px-2.5 py-1">
            <span className="text-brand-red text-xs">🚩</span>
            <span className="text-brand-red text-[10px] font-display font-bold uppercase tracking-widest">Flag on Play</span>
          </div>
        )}
      </div>

      <div className="p-5" style={{background: "linear-gradient(160deg, #1A3350 0%, #0F1F35 100%)"}}>
        {/* Title + Value */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="font-display font-bold text-white text-xl leading-tight tracking-wide">{offer.title}</div>
          <div className="text-right flex-shrink-0">
            <div className="font-display font-bold text-brand-gold text-2xl leading-none score-glow">{offer.value}</div>
            <div className="text-[10px] text-brand-chalk/30 uppercase tracking-wider">discount</div>
          </div>
        </div>

        <p className="text-sm text-brand-chalk/60 leading-relaxed">{offer.description}</p>

        {/* Incident alert */}
        {offer.incident_alert && (
          <div className="mt-3 flex items-start gap-2.5 bg-brand-red/5 border border-brand-red/25 rounded-xl px-3 py-2.5">
            <span className="text-brand-red mt-0.5 flex-shrink-0">⚠️</span>
            <p className="text-red-300 text-xs leading-relaxed">{offer.incident_alert}</p>
          </div>
        )}

        {/* Justification */}
        <div className="mt-3 text-[11px] text-brand-chalk/35 italic leading-relaxed border-l-2 border-brand-gold/20 pl-2.5">
          {offer.justification}
        </div>

        {/* Offer code */}
        <div className="mt-3 bg-brand-field/20 border border-brand-field/40 rounded-xl px-4 py-2.5 flex items-center justify-between">
          <span className="text-[10px] text-brand-chalk/40 uppercase tracking-widest font-display">Promo Code</span>
          <span className="font-mono font-bold text-brand-gold tracking-widest text-sm">{offer.offer_code}</span>
        </div>

        {/* Decision area */}
        {!decided ? (
          <div className="mt-4 space-y-2">
            <button
              onClick={() => onDecide(true, "")}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-brand-grass to-green-600 hover:from-green-500 hover:to-brand-grass text-white font-display font-bold text-sm tracking-widest uppercase transition-all hover:shadow-lg hover:shadow-brand-grass/25 active:scale-[0.98]"
            >
              ✅ Approve — Send to Fan
            </button>

            {!showRejectMenu ? (
              <button
                onClick={() => setShowRejectMenu(true)}
                className="w-full py-2.5 rounded-xl bg-white/3 hover:bg-brand-red/10 text-brand-chalk/40 hover:text-brand-red font-display font-semibold text-sm tracking-widest uppercase transition-all border border-white/8 hover:border-brand-red/40"
              >
                🚩 Reject
              </button>
            ) : (
              <div className="bg-brand-red/5 rounded-xl p-3.5 border border-brand-red/25">
                <p className="text-[10px] text-brand-chalk/40 uppercase tracking-widest font-display mb-2">Select rejection reason:</p>
                {REJECTION_REASONS.map((r) => (
                  <button
                    key={r}
                    onClick={() => onDecide(false, r)}
                    className="w-full text-left text-sm text-brand-chalk/60 hover:text-brand-red py-2 px-2 rounded-lg hover:bg-brand-red/10 transition-colors font-display"
                  >
                    › {r}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className={clsx(
            "mt-4 rounded-xl px-4 py-3.5 text-sm font-display font-bold text-center tracking-wide border",
            decision!.approved
              ? "bg-brand-grass/10 text-brand-grass border-brand-grass/30"
              : "bg-brand-red/10 text-red-300 border-brand-red/25"
          )}>
            {decision!.approved
              ? "✅ Approved — Email sent to fan"
              : `🚩 Rejected: ${decision!.reason}`}
          </div>
        )}
      </div>
    </div>
  );
}
