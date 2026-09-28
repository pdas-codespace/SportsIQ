"use client";
import { useState, useCallback } from "react";
import { agentsApiUrl } from "./agui";
import type { ChatMessage } from "./types";

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
  reset: () => void;
}

export function useChat(): ChatState {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previousResponseId, setPreviousResponseId] = useState<string | null>(null);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${agentsApiUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text.trim(),
          previous_response_id: previousResponseId,
        }),
      });

      if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText);
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const data: { answer: string; response_id: string } = await res.json();
      setPreviousResponseId(data.response_id);
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.answer,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat error — check agent connection");
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, previousResponseId]);

  const reset = useCallback(() => {
    setMessages([]);
    setPreviousResponseId(null);
    setError(null);
  }, []);

  return { messages, isLoading, error, sendMessage, reset };
}
