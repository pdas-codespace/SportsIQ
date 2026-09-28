import { clsx } from "clsx";
import { useState } from "react";
import type { BreakOption } from "@/lib/sport-labels";

interface Props {
  homeTeam: string;
  homeTeamName?: string;
  awayTeam: string;
  awayTeamName?: string;
  homeScore: number;
  awayScore: number;
  quarter: string;
  clock: string;
  situation: string;
  demoLabel: string;
  breakTypes: BreakOption[];
  onSimulate: (breakType: string) => void;
  isRunning: boolean;
  isScanning?: boolean;
}

export function Scoreboard({
  homeTeam, homeTeamName, awayTeam, awayTeamName, homeScore, awayScore,
  quarter, clock, situation, demoLabel, breakTypes,
  onSimulate, isRunning, isScanning = false,
}: Props) {
  const [selectedBreak, setSelectedBreak] = useState<string>(() => breakTypes[0]?.value ?? "commercial");
  const busy = isRunning || isScanning;

  return (
    <div className="rounded-2xl overflow-hidden border border-brand-gold/40 shadow-2xl"
      style={{background: "linear-gradient(160deg, #1A3350 0%, #0F1F35 100%)"}}>

      {/* Broadcast ticker bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-brand-field/50"
        style={{background: "linear-gradient(90deg, #0D4A25 0%, #0a3319 100%)"}}>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-brand-grass led-live" />
          <span className="font-display text-brand-grass text-xs font-semibold tracking-widest uppercase">
            Live · {demoLabel}
          </span>
        </div>
        <div className="flex items-center gap-3 font-display text-xs font-semibold tracking-wider">
          <span className="text-brand-gold">{quarter}</span>
          <span className="text-white/30">·</span>
          <span className="text-white/80">{clock}</span>
          <span className="text-white/30">·</span>
          <span className="bg-brand-gold/10 border border-brand-gold/40 text-brand-gold px-2 py-0.5 rounded text-xs uppercase">
            {situation}
          </span>
        </div>
      </div>

      {/* Score panel */}
      <div className="px-6 py-5">
        <div className="flex items-stretch justify-between gap-2">

          {/* Home team */}
          <div className="flex-1 text-center">
            <div className="font-display text-3xl font-bold tracking-widest text-white uppercase">{homeTeam}</div>
            <div className="text-[10px] text-brand-chalk/30 uppercase tracking-widest mb-1">{homeTeamName || homeTeam} · Home</div>
            <div
              className="font-display text-7xl font-bold text-brand-gold score-glow tabular-nums"
              style={{textShadow: "0 0 30px rgba(245,166,35,0.5)"}}>
              {homeScore}
            </div>
          </div>

          {/* Center divider */}
          <div className="flex flex-col items-center justify-center px-2 gap-1">
            <div className="w-px flex-1 bg-white/10" />
            <div className="font-display text-white/20 font-bold text-lg">VS</div>
            <div className="w-px flex-1 bg-white/10" />
          </div>

          {/* Away team */}
          <div className="flex-1 text-center">
            <div className="font-display text-3xl font-bold tracking-widest text-white/70 uppercase">{awayTeam}</div>
            <div className="text-[10px] text-brand-chalk/30 uppercase tracking-widest mb-1">{awayTeamName || awayTeam} · Away</div>
            <div className="font-display text-7xl font-bold text-white/50 tabular-nums">
              {awayScore}
            </div>
          </div>
        </div>

        {/* Down & distance strip */}
        <div className="mt-4 flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full overflow-hidden bg-white/5">
            <div className="h-full bg-gradient-to-r from-brand-field via-brand-grass to-brand-gold rounded-full"
              style={{width: `${(homeScore / (homeScore + awayScore + 0.01)) * 100}%`}} />
          </div>
        </div>
      </div>

      {/* Break type selector */}
      <div className="px-4 pb-2">
        <div className="text-[10px] text-brand-chalk/40 uppercase tracking-widest mb-2 font-display font-semibold">
          Break Type
        </div>
        <div className="grid grid-cols-4 gap-1.5">
          {breakTypes.map((bt) => (
            <button
              key={bt.value}
              onClick={() => setSelectedBreak(bt.value)}
              disabled={busy}
              className={clsx(
                "py-1.5 px-1 rounded-lg text-[10px] font-display font-semibold tracking-wide uppercase transition-all duration-150 text-center leading-tight",
                selectedBreak === bt.value
                  ? "bg-brand-gold/20 border border-brand-gold/60 text-brand-gold"
                  : "bg-white/5 border border-white/10 text-white/40 hover:text-white/70 hover:border-white/20",
                busy && "opacity-40 cursor-not-allowed"
              )}
            >
              <div>{bt.icon}</div>
              <div>{bt.label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Simulate button */}
      <div className="px-4 pb-4 pt-2">
        <button
          onClick={() => onSimulate(selectedBreak)}
          disabled={busy}
          className={clsx(
            "w-full py-3.5 rounded-xl font-display font-semibold text-sm tracking-widest uppercase transition-all duration-200",
            busy
              ? "bg-white/5 text-white/25 cursor-not-allowed border border-white/10"
              : "bg-gradient-to-r from-brand-grass to-brand-field text-white border border-brand-grass/60 hover:from-green-500 hover:to-brand-grass hover:shadow-lg hover:shadow-brand-grass/25 active:scale-[0.98]"
          )}
        >
          {isScanning
            ? "🔍  Scanning Fans…"
            : isRunning
            ? "⏳  Workflow Running…"
            : "🎯  Simulate Break"}
        </button>
      </div>
    </div>
  );
}
