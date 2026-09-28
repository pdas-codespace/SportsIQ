"use client";
import { useEffect, useMemo, useState } from "react";
import { Scoreboard } from "@/components/Scoreboard";
import { FanSelector } from "@/components/FanSelector";
import { TriggeredFanList } from "@/components/TriggeredFanList";
import { OfferPipeline } from "@/components/OfferPipeline";
import { ApprovalCard } from "@/components/ApprovalCard";
import { StatusTimeline } from "@/components/StatusTimeline";
import { DemoSettings, getStoredDemoEmail } from "@/components/DemoSettings";
import { ChatPanel } from "@/components/ChatPanel";
import POSRedemptionPanel from "@/components/POSRedemptionPanel";
import { useWorkflow } from "@/lib/useWorkflow";
import { useSportConfig } from "@/lib/useSportConfig";
import { useDemoConfig } from "@/lib/DemoConfigProvider";
import { simulateGameEvent } from "@/lib/agui";
import type { BreakType, FanProfile, TriggeredFan } from "@/lib/types";

export default function DemoPage() {
  const sport = useSportConfig();
  const demoConfig = useDemoConfig();
  const GAME_ID = demoConfig?.gameId ?? "demo_game";
  const [selectedFan, setSelectedFan] = useState<FanProfile | null>(null);
  const [scanState, setScanState] = useState<"idle" | "scanning" | "ready">("idle");
  const [triggeredFans, setTriggeredFans] = useState<TriggeredFan[]>([]);
  const [breakLabel, setBreakLabel] = useState<string | null>(null);
  const [showBrowse, setShowBrowse] = useState(false);
  const [demoEmail, setDemoEmail] = useState<string>("");
  const [chatSeed, setChatSeed] = useState<string | undefined>();

  // Hydrate from localStorage after mount (avoids SSR mismatch)
  useEffect(() => { setDemoEmail(getStoredDemoEmail()); }, []);

  const { status, messages, toolCalls, offers, decisions, pendingApprovals, trigger, approve } =
    useWorkflow(GAME_ID);

  const approvedOffer = useMemo(
    () => offers.find((o) => decisions[o.id]?.approved),
    [offers, decisions]
  );

  const isRunning = ["connecting", "started"].includes(status ?? "");
  const runSportContext = useMemo(() => ({
    sport: sport.sport,
    league_name: sport.leagueName,
    home_team: sport.demoGame.homeTeam,
    home_team_name: sport.demoGame.homeTeamName,
    away_team: sport.demoGame.awayTeam,
    away_team_name: sport.demoGame.awayTeamName,
    venue_label: sport.venueLabel,
    period_label: sport.periodLabel,
  }), [sport]);

  async function handleSimulate(breakType: BreakType) {
    if (isRunning || scanState === "scanning") return;
    setScanState("scanning");
    setSelectedFan(null);
    setTriggeredFans([]);
    try {
      const result = await simulateGameEvent(breakType, GAME_ID);
      setBreakLabel(result.break_label);
      setTriggeredFans(result.triggered_fans);
      setScanState("ready");
    } catch (err) {
      console.error("Game event scan failed", err);
      setScanState("idle");
    }
  }

  function handleSelectTriggeredFan(fan: TriggeredFan) {
    setSelectedFan(fan);
    trigger(
      fan.fanId,
      fan.fanName,
      fan.loyaltyTier,
      demoEmail || undefined,
      fan.preferredSectionId,
      runSportContext
    );
  }

  const timelineEntries = useMemo(() => {
    const s = status;
    return [
      {
        label: breakLabel
          ? `${breakLabel} detected`
          : "Simulate a game break",
        status: scanState !== "idle" ? "done" : "pending",
      },
      {
        label: triggeredFans.length > 0
          ? `${triggeredFans.length} disengaged fan${triggeredFans.length > 1 ? "s" : ""} identified`
          : "Scanning for disengaged fans",
        status: scanState === "ready" ? "done" : scanState === "scanning" ? "active" : "pending",
      },
      {
        label: selectedFan
          ? `Fan targeted: ${selectedFan.fanName || selectedFan.fanId}`
          : "Select a fan to target",
        status: selectedFan ? "done" : "pending",
      },
      {
        label: "Engagement Monitor — fatigue gate check",
        status: s === "connecting" || s === "started" ? "active" : s === "idle" ? "pending" : "done",
      },
      {
        label: "Offer Generator — 2 personalised offers",
        status:
          s === "awaiting_approval" || s === "completed" ? "done"
          : s === "started" ? "active"
          : "pending",
      },
      {
        label: "Human Review — Approve / Reject",
        status: s === "awaiting_approval" ? "active" : s === "completed" ? "done" : "pending",
      },
      {
        label: "ACS email sent (approved offer)",
        status: s === "completed" && Object.values(decisions).some((d) => d.approved) ? "done" : "pending",
      },
    ] as { label: string; status: "done" | "active" | "pending" }[];
  }, [status, decisions, selectedFan, scanState, triggeredFans, breakLabel]);

  return (
    <main className="min-h-screen bg-brand-dark">
      {/* ── Broadcast header bar ───────────────────────────────────────────── */}
      <header className="relative overflow-hidden border-b border-brand-field/60"
        style={{background: "linear-gradient(135deg, #0F1F35 0%, #0D4A25 50%, #0F1F35 100%)"}}>
        <div className="absolute inset-0 opacity-10"
          style={{backgroundImage: "repeating-linear-gradient(-45deg, rgba(245,166,35,0.5) 0px, transparent 1px, transparent 8px, rgba(245,166,35,0.5) 9px)"}} />
        <div className="relative px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-3xl drop-shadow-lg">{sport.emoji}</span>
              <div>
                <div className="font-display font-bold text-brand-gold text-2xl leading-none tracking-wide uppercase">
                  Sports-IQ
                </div>
                <div className="text-[10px] text-brand-chalk/50 uppercase tracking-widest">
                    {sport.headerSubtitle}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5 bg-brand-grass/20 border border-brand-grass/50 rounded-full px-3 py-1">
              <span className="w-2 h-2 rounded-full bg-brand-grass led-live" />
              <span className="text-brand-grass text-xs font-bold tracking-widest uppercase">Live</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
            <div className="text-xs text-brand-chalk/30 uppercase tracking-widest">System Status</div>
            <div className={`text-sm font-display font-semibold uppercase tracking-wide ${
              status === "idle" ? "text-brand-chalk/40" :
              status === "completed" ? "text-brand-grass" :
              status === "awaiting_approval" ? "text-brand-gold" :
              "text-brand-orange"
            }`}>
              {status === "idle"
                ? (scanState === "ready" ? "Fan Ready" : scanState === "scanning" ? "⚡ Scanning" : "Awaiting Break")
                : status === "connecting" ? "⚡ Connecting"
                : status === "started" ? "🤖 Agents Running"
                : status === "awaiting_approval" ? "🚦 Human Review"
                : status === "completed" ? "✅ Complete"
                : status}
            </div>
            </div>
            <DemoSettings email={demoEmail} onChange={setDemoEmail} />
            <button
              onClick={async () => {
                await fetch("/api/auth/logout", { method: "POST" });
                window.location.href = "/login";
              }}
              className="text-white/30 hover:text-white/60 text-xs uppercase tracking-widest border border-white/10
                         hover:border-white/30 rounded px-2 py-1 transition"
              title="Sign out"
            >
              Sign out
            </button>
          </div>
        </div>
        <div className="h-0.5 bg-gradient-to-r from-transparent via-brand-gold to-transparent" />
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Left column — scoreboard + triggered fans + timeline */}
        <div className="space-y-5">
          <Scoreboard
            homeTeam={sport.demoGame.homeTeam}
            homeTeamName={sport.demoGame.homeTeamName}
            awayTeam={sport.demoGame.awayTeam}
            awayTeamName={sport.demoGame.awayTeamName}
            homeScore={sport.demoGame.homeScore}
            awayScore={sport.demoGame.awayScore}
            quarter={sport.demoGame.period}
            clock={sport.demoGame.clock}
            situation={breakLabel ?? "In Play"}
            demoLabel={sport.demoLabel}
            breakTypes={sport.breakTypes}
            onSimulate={handleSimulate}
            isRunning={isRunning}
            isScanning={scanState === "scanning"}
          />

          <TriggeredFanList
            scanState={scanState}
            breakLabel={breakLabel}
            triggeredFans={triggeredFans}
            selectedFanId={selectedFan?.fanId ?? null}
            onSelectFan={handleSelectTriggeredFan}
          />

          {/* Browse All Fans — collapsible secondary panel */}
          <div>
            <button
              onClick={() => setShowBrowse((v) => !v)}
              className="w-full text-left flex items-center gap-2 text-[10px] text-brand-chalk/30 font-display uppercase tracking-widest hover:text-brand-chalk/60 transition-colors py-1"
            >
              <span className="flex-1 h-px bg-white/5" />
              {showBrowse ? "▲" : "▼"} Browse all fans
              <span className="flex-1 h-px bg-white/5" />
            </button>
            {showBrowse && (
              <FanSelector
                selectedFan={selectedFan}
                onSelect={(fan) => {
                  setSelectedFan(fan);
                  // Allow manually selecting a fan even outside the triggered list
                }}
              />
            )}
          </div>

          <StatusTimeline entries={timelineEntries} />
        </div>

        {/* Middle column — Agent Pipeline */}
        <div>
          <OfferPipeline
            messages={messages}
            toolCalls={toolCalls as { name: string; status: "running" | "done" }[]}
            isActive={isRunning}
          />

          {offers.length > 0 && status !== "completed" && (
            <div className="mt-5">
              <div className="font-display text-[10px] font-semibold tracking-widest text-brand-chalk/35 uppercase mb-3 flex items-center gap-2">
                <span className="w-4 h-px bg-brand-gold/40" />
                ⚡ Generated Offers
                <span className="w-4 h-px bg-brand-gold/40" />
              </div>
              <div className="space-y-3">
                {offers.map((offer) => (
                  <div key={offer.id} className="rounded-xl border border-brand-gold/20 px-4 py-3"
                    style={{background: "linear-gradient(160deg, #1A3350 0%, #0F1F35 100%)"}}>
                    <div className="font-display font-semibold text-white">{offer.title}</div>
                    <div className="text-sm text-brand-chalk/45 mt-1">{offer.justification}</div>
                    {offer.incident_alert && (
                      <div className="text-xs text-brand-red mt-2 flex items-center gap-1.5">
                        <span>🚩</span>{offer.incident_alert}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right column — Human Review */}
        <div>
          <div className="font-display text-[10px] font-semibold tracking-widest text-brand-chalk/40 uppercase mb-3 flex items-center gap-2">
            <span className="w-4 h-px bg-brand-gold/40" />
            🧑‍⚖️ Human Review
            {pendingApprovals.length > 0 && (
              <span className="ml-1 bg-brand-gold text-brand-dark px-2 py-0.5 rounded-full text-[10px] font-bold animate-pulse">
                {pendingApprovals.length} pending
              </span>
            )}
            <span className="flex-1 h-px bg-brand-gold/20" />
          </div>

          {pendingApprovals.length > 0 && (
            <div className="space-y-4">
              {pendingApprovals.map(({ offerId, offer }) => (
                <ApprovalCard
                  key={offerId}
                  offer={offer}
                  decision={decisions[offerId]}
                  onDecide={(approved, reason) => approve(offerId, approved, reason)}
                />
              ))}
            </div>
          )}

          {status === "completed" && offers.length > 0 && (
            <div className="space-y-4">
              {offers.map((offer) => (
                <ApprovalCard
                  key={offer.id}
                  offer={offer}
                  decision={decisions[offer.id]}
                  onDecide={() => {}}
                />
              ))}
              <div className="mt-4 rounded-2xl border border-brand-grass/40 overflow-hidden">
                <div className="h-1 bg-gradient-to-r from-brand-field via-brand-grass to-brand-field" />
                <div className="px-5 py-4 text-center"
                  style={{background: "linear-gradient(160deg, rgba(13,74,37,0.15), #0F1F35)"}}>
                  <div className="font-display font-bold text-brand-grass text-lg tracking-wide">
                    🏆 Demo Complete
                  </div>
                  <div className="text-sm text-brand-chalk/45 mt-1">
                    Approved offer emailed · Rejection logged to Lakehouse · Teams updated
                  </div>
                </div>
              </div>

              {/* POS Redemption — only show when an offer was approved */}
              {approvedOffer && selectedFan && (
                <POSRedemptionPanel
                  fanId={selectedFan.fanId}
                  fanName={selectedFan.fanName}
                  gameId={GAME_ID}
                  offer={approvedOffer}
                  onSuggestedQuestion={(q) => setChatSeed(q)}
                />
              )}
            </div>
          )}

          {status === "idle" && (
            <div className="rounded-2xl border border-dashed border-brand-gold/15 p-10 text-center">
              <div className="text-4xl mb-3">{sport.stadiumEmoji}</div>
              <div className="font-display text-brand-chalk/25 text-sm tracking-wide">
                {selectedFan
                  ? <>Fan targeted — pipeline will start automatically</>
                  : scanState === "ready"
                  ? <>Select a fan from the triggered list</>
                  : <>Simulate a break to identify disengaged fans</>}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Floating Data Agent Chat widget — fixed top-right, always accessible */}
      <ChatPanel seedQuestion={chatSeed} onSeedConsumed={() => setChatSeed(undefined)} />
    </main>
  );
}
