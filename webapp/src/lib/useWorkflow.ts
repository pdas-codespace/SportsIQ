"use client";
import { useCallback, useRef, useState } from "react";
import { AgUiEvent, Offer, WorkflowState } from "@/lib/types";
import { createAgentRunStream, startRun, submitToolResult, type RunSportContext } from "@/lib/agui";

export interface UseWorkflowResult {
  runId: string | null;
  status: WorkflowState["workflow_status"] | "idle" | "connecting";
  messages: string[];
  toolCalls: { name: string; status: string }[];
  offers: Offer[];
  decisions: Record<string, { approved: boolean; reason: string }>;
  pendingApprovals: { offerId: string; offer: Offer }[];
  trigger: (
    fanId: string,
    fanName?: string,
    fanLoyaltyTier?: string,
    fanEmail?: string,
    preferredSectionId?: string,
    sportContext?: RunSportContext
  ) => Promise<void>;
  approve: (offerId: string, approved: boolean, reason?: string) => Promise<void>;
}

export function useWorkflow(gameId: string): UseWorkflowResult {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<UseWorkflowResult["status"]>("idle");
  const [messages, setMessages] = useState<string[]>([]);
  const [toolCalls, setToolCalls] = useState<{ name: string; status: string }[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [decisions, setDecisions] = useState<Record<string, { approved: boolean; reason: string }>>({});
  const [pendingApprovals, setPendingApprovals] = useState<{ offerId: string; offer: Offer }[]>([]);
  const msgBuffer = useRef<Record<string, string>>({});

  const esRef = useRef<EventSource | null>(null);

  const handleEvent = useCallback((event: AgUiEvent, es: EventSource) => {
    switch (event.type) {
      case "RUN_STARTED":
        setStatus("started");
        break;

      case "TEXT_MESSAGE_CONTENT":
        if (event.message_id && event.delta) {
          msgBuffer.current[event.message_id] = (msgBuffer.current[event.message_id] || "") + event.delta;
        }
        break;

      case "TEXT_MESSAGE_END":
        if (event.message_id) {
          const text = msgBuffer.current[event.message_id];
          if (text) {
            setMessages((prev) => [...prev, text]);
            delete msgBuffer.current[event.message_id!];
          }
        }
        break;

      case "TOOL_CALL_START":
        if (event.tool_call_type === "client" && event.tool_name === "request_approval") {
          // HITL: add to pending approvals
          const args = event.args as { offer_id: string; offer: Offer };
          setPendingApprovals((prev) => {
            if (prev.some((p) => p.offerId === args.offer_id)) return prev;
            return [...prev, { offerId: args.offer_id, offer: args.offer }];
          });
          setStatus("awaiting_approval");
        } else {
          setToolCalls((prev) => [...prev, { name: event.tool_name || "tool", status: "running" }]);
        }
        break;

      case "TOOL_CALL_END":
        setToolCalls((prev) =>
          prev.map((t, i) => (i === prev.length - 1 ? { ...t, status: "done" } : t))
        );
        break;

      case "STATE_SNAPSHOT":
        if (event.snapshot) {
          if (event.snapshot.offers) setOffers(event.snapshot.offers);
          if (event.snapshot.decisions) {
            setDecisions(
              Object.fromEntries(
                Object.entries(event.snapshot.decisions).map(([k, v]) => [
                  k,
                  { approved: (v as { approved: boolean }).approved, reason: (v as { reason: string }).reason },
                ])
              )
            );
          }
          if (event.snapshot.workflow_status) setStatus(event.snapshot.workflow_status);
        }
        break;

      case "RUN_FINISHED":
        setStatus("completed");
        es.close();  // prevent EventSource auto-reconnect from re-triggering the workflow
        break;

      case "RUN_ERROR":
        setStatus("idle");
        es.close();  // prevent reconnect loop
        setMessages((prev) => [...prev, `❌ Error: ${event.error || "unknown error"}`]);
        break;
    }
  }, []);

  const trigger = useCallback(async (
    fanId: string,
    fanName?: string,
    fanLoyaltyTier?: string,
    fanEmail?: string,
    preferredSectionId?: string,
    sportContext?: RunSportContext
  ) => {
    setStatus("connecting");
    setMessages([]);
    setToolCalls([]);
    setOffers([]);
    setDecisions({});
    setPendingApprovals([]);
    msgBuffer.current = {};

    // Close any existing stream before opening a new one
    esRef.current?.close();

    const id = await startRun(
      fanId,
      gameId,
      fanName,
      fanLoyaltyTier,
      fanEmail,
      preferredSectionId,
      sportContext
    );
    setRunId(id);

    const es = createAgentRunStream(id);
    esRef.current = es;
    es.onmessage = (e) => {
      try {
        handleEvent(JSON.parse(e.data) as AgUiEvent, es);
      } catch {
        // ignore parse errors on keep-alive pings
      }
    };
    es.onerror = () => {
      es.close();
    };
  }, [gameId, handleEvent]);

  const approve = useCallback(
    async (offerId: string, approved: boolean, reason = "") => {
      if (!runId) return;
      await submitToolResult(runId, offerId, approved, reason);
      setDecisions((prev) => ({ ...prev, [offerId]: { approved, reason } }));
      setPendingApprovals((prev) => prev.filter((p) => p.offerId !== offerId));
    },
    [runId]
  );

  return { runId, status, messages, toolCalls, offers, decisions, pendingApprovals, trigger, approve };
}
