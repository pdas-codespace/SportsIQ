import { useState, useCallback } from "react";
import { agentsApiUrl } from "./agui";
import type {
  RedemptionStep,
  RedemptionStepName,
  RedemptionResult,
  Offer,
} from "./types";

const INITIAL_STEPS: RedemptionStep[] = [
  { name: "scanning",    label: "Scan QR / POS Receipt", status: "idle", message: "" },
  { name: "eventhouse",  label: "Write to Eventhouse",   status: "idle", message: "" },
  { name: "lakehouse",   label: "Write Feedback Event",  status: "idle", message: "" },
  { name: "complete",    label: "Closed-Loop Complete",  status: "idle", message: "" },
];

interface UsePOSRedemptionOptions {
  fanId: string;
  fanName: string;
  gameId: string;
  offer: Offer;
  unitPrice?: number;
}

export function usePOSRedemption({
  fanId,
  fanName,
  gameId,
  offer,
  unitPrice = 89.0,
}: UsePOSRedemptionOptions) {
  const [steps, setSteps] = useState<RedemptionStep[]>(INITIAL_STEPS);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<RedemptionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateStep = useCallback(
    (name: RedemptionStepName, patch: Partial<RedemptionStep>) => {
      setSteps((prev) =>
        prev.map((s) => (s.name === name ? { ...s, ...patch } : s))
      );
    },
    []
  );

  const reset = useCallback(() => {
    setSteps(INITIAL_STEPS);
    setIsRunning(false);
    setResult(null);
    setError(null);
  }, []);

  const redeem = useCallback(async () => {
    reset();
    setIsRunning(true);

    const body = {
      fan_id: fanId,
      fan_name: fanName,
      game_id: gameId,
      promo_id: offer.id,
      offer_title: offer.title,
      offer_category: offer.category,
      offer_type: offer.offer_type,
      offer_value: parseFloat(offer.value.replace(/[^0-9.]/g, "")),
      unit_price: unitPrice,
    };

    try {
      const res = await fetch(`${agentsApiUrl}/api/demo/redeem-offer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          const event = JSON.parse(raw);
          const { step, status, message, latency_ms, ...rest } = event;

          updateStep(step as RedemptionStepName, { status, message, latency_ms });

          if (step === "complete" && status === "done") {
            setResult({
              transaction_id: rest.transaction_id,
              revenue_impact: rest.revenue_impact,
              suggested_question: rest.suggested_question,
            });
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRunning(false);
    }
  }, [fanId, fanName, gameId, offer, unitPrice, reset, updateStep]);

  return { steps, isRunning, result, error, redeem, reset };
}
