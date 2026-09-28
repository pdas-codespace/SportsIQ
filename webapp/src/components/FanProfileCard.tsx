interface Props {
  fanName: string;
  loyaltyTier: string;
  section: string;
  engagementScore: number;
  lastOfferDaysAgo: number;
}

export function FanProfileCard({ fanName, loyaltyTier, section, engagementScore, lastOfferDaysAgo }: Props) {
  const scoreColor =
    engagementScore < 0.5 ? "text-brand-red" : engagementScore < 0.7 ? "text-brand-gold" : "text-brand-grass";
  const scoreBg =
    engagementScore < 0.5 ? "from-red-900/40 to-red-950/20 border-red-500/30"
    : engagementScore < 0.7 ? "from-yellow-900/40 to-yellow-950/20 border-yellow-500/30"
    : "from-green-900/40 to-green-950/20 border-green-600/30";
  const tierColor =
    loyaltyTier === "Platinum" ? "bg-blue-400/10 text-blue-300 border-blue-400/30" :
    loyaltyTier === "Gold"     ? "bg-brand-gold/10 text-brand-gold border-brand-gold/30" :
    loyaltyTier === "Silver"   ? "bg-white/10 text-white/70 border-white/20" :
                                 "bg-brand-field/40 text-brand-grass border-brand-grass/30";

  return (
    <div className="rounded-2xl border border-white/10 overflow-hidden"
      style={{background: "linear-gradient(160deg, #1A3350 0%, #152C45 100%)"}}>
      {/* Accent stripe */}
      <div className="h-1 bg-gradient-to-r from-brand-field via-brand-gold to-brand-field" />

      <div className="p-5">
        <div className="text-[10px] font-display font-semibold tracking-widest text-brand-chalk/30 uppercase mb-3">
          🏟️ Fan on Record
        </div>

        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-14 h-14 rounded-full border-2 border-brand-gold bg-brand-gold/10 flex items-center justify-center text-2xl shadow-lg shadow-brand-gold/10">
              🙋
            </div>
            <div className={`absolute -bottom-1 -right-1 text-[10px] font-display font-bold px-1.5 py-0.5 rounded-full border ${tierColor}`}>
              {loyaltyTier.slice(0, 4).toUpperCase()}
            </div>
          </div>
          <div>
            <div className="font-display font-bold text-white text-xl tracking-wide">{fanName}</div>
            <div className="text-brand-chalk/40 text-xs mt-0.5 uppercase tracking-wider">
              Section {section} · {loyaltyTier} Tier
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className={`rounded-xl border bg-gradient-to-b ${scoreBg} p-3`}>
            <div className="text-[10px] text-brand-chalk/40 uppercase tracking-widest mb-1 font-display">Engagement</div>
            <div className={`font-display text-3xl font-bold ${scoreColor}`}>{engagementScore.toFixed(2)}</div>
            <div className="mt-2 h-1.5 rounded-full bg-black/30 overflow-hidden">
              <div className="h-full rounded-full bg-current transition-all duration-500"
                style={{width: `${engagementScore * 100}%`, color: "inherit", backgroundColor:
                  engagementScore < 0.5 ? "#DC2626" : engagementScore < 0.7 ? "#F5A623" : "#16A34A"}} />
            </div>
            <div className={`text-[10px] mt-1 ${scoreColor}`}>
              {engagementScore < 0.5 ? "⬇ Below threshold" : engagementScore < 0.7 ? "⚡ Moderate" : "🔥 High"}
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/3 p-3">
            <div className="text-[10px] text-brand-chalk/40 uppercase tracking-widest mb-1 font-display">Last Offer</div>
            <div className="font-display text-3xl font-bold text-white">{lastOfferDaysAgo}<span className="text-base font-normal text-white/40 ml-0.5">d</span></div>
            <div className="text-[10px] text-brand-grass mt-2 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-grass inline-block" />
              Fatigue gate clear
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
