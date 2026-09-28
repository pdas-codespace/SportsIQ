"use client";

import React from "react";
import { usePOSRedemption } from "@/lib/usePOSRedemption";
import type { Offer, RedemptionStep } from "@/lib/types";

interface POSRedemptionPanelProps {
  fanId: string;
  fanName: string;
  gameId: string;
  offer: Offer;
  unitPrice?: number;
  onSuggestedQuestion?: (q: string) => void;
}

const STEP_ICONS: Record<string, string> = {
  scanning:   "📱",
  eventhouse: "⚡",
  lakehouse:  "🔄",
  complete:   "🎉",
};

function StepRow({ step }: { step: RedemptionStep }) {
  const icon = STEP_ICONS[step.name] ?? "•";
  const color =
    step.status === "done"    ? "text-green-400" :
    step.status === "error"   ? "text-red-400"   :
    step.status === "running" ? "text-yellow-400 animate-pulse" :
                                "text-gray-500";

  const bullet =
    step.status === "done"    ? "✅" :
    step.status === "error"   ? "❌" :
    step.status === "running" ? "⏳" :
                                "⬜";

  return (
    <div className="flex items-start gap-2 py-1">
      <span className="text-base">{bullet}</span>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium ${color}`}>
          {icon} {step.label}
          {step.latency_ms !== undefined && step.status === "done" && (
            <span className="ml-2 text-xs text-gray-400 font-normal">{step.latency_ms} ms</span>
          )}
        </div>
        {step.message && (
          <div className="text-xs text-gray-400 mt-0.5 break-words">{step.message}</div>
        )}
      </div>
    </div>
  );
}

export default function POSRedemptionPanel({
  fanId,
  fanName,
  gameId,
  offer,
  unitPrice = 89.0,
  onSuggestedQuestion,
}: POSRedemptionPanelProps) {
  const { steps, isRunning, result, error, redeem, reset } = usePOSRedemption({
    fanId,
    fanName,
    gameId,
    offer,
    unitPrice,
  });

  const hasStarted = steps.some((s) => s.status !== "idle");

  // Compute discount label
  const discountLabel =
    offer.offer_type === "percentage_discount"
      ? `${offer.value}% off (was $${unitPrice.toFixed(2)})`
      : `$${offer.value} off`;

  return (
    <div className="rounded-xl border border-orange-500/30 bg-gradient-to-br from-orange-950/30 to-gray-900/60 p-4 mt-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">🏟️</span>
        <div>
          <div className="text-sm font-bold text-orange-300">Stadium POS Redemption Simulation</div>
          <div className="text-xs text-gray-400">
            {fanName} · {offer.title} · {discountLabel}
          </div>
        </div>
      </div>

      {/* Steps */}
      {hasStarted && (
        <div className="mb-3 space-y-0.5 bg-black/30 rounded-lg p-3 border border-white/5">
          {steps.map((step) => (
            <StepRow key={step.name} step={step} />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-3 rounded-lg bg-red-900/30 border border-red-500/30 p-2 text-xs text-red-300">
          ⚠️ {error}
        </div>
      )}

      {/* Result card */}
      {result && (
        <div className="mb-3 rounded-lg bg-green-900/20 border border-green-500/30 p-3 text-sm">
          <div className="font-semibold text-green-300 mb-1">
            💵 ${result.revenue_impact?.toFixed(2)} captured · ID: {result.transaction_id}
          </div>
          {result.suggested_question && (
            <div className="text-xs text-gray-300 mt-1">
              <span className="text-gray-400">Ask the Data Agent: </span>
              <button
                onClick={() => onSuggestedQuestion?.(result.suggested_question!)}
                className="text-orange-300 hover:text-orange-200 underline text-left"
              >
                &ldquo;{result.suggested_question}&rdquo;
              </button>
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={redeem}
          disabled={isRunning}
          className={
            "flex-1 rounded-lg py-2 px-4 text-sm font-semibold transition-all " +
            (isRunning
              ? "bg-orange-700/50 text-orange-300 cursor-not-allowed"
              : "bg-orange-600 hover:bg-orange-500 text-white cursor-pointer")
          }
        >
          {isRunning ? "⏳ Simulating…" : hasStarted ? "🔄 Re-Simulate" : "🏟️ Simulate POS Redemption"}
        </button>
        {hasStarted && !isRunning && (
          <button
            onClick={reset}
            className="rounded-lg py-2 px-3 text-sm text-gray-400 hover:text-white border border-white/10 hover:border-white/20 transition-all"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
