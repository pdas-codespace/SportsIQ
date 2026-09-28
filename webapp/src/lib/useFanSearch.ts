"use client";
import { useCallback, useState } from "react";
import type { FanProfile } from "@/lib/types";
import { agentsApiUrl } from "@/lib/agui";

const API = agentsApiUrl;

export type FanSearchMode = "tier" | "section";

export interface UseFanSearchResult {
  fans: FanProfile[];
  loading: boolean;
  error: string | null;
  search: (mode: FanSearchMode, value: string, sections?: string[]) => Promise<void>;
  reset: () => void;
}

export function useFanSearch(): UseFanSearchResult {
  const [fans, setFans] = useState<FanProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (mode: FanSearchMode, value: string, sections?: string[]) => {
    setLoading(true);
    setError(null);
    setFans([]);
    try {
      const params = new URLSearchParams({ mode, value });
      if (mode === "section" && sections?.length) {
        params.set("sections", sections.join(","));
      }
      const res = await fetch(`${API}/api/fans?${params}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setFans(data.fans ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setFans([]);
    setError(null);
  }, []);

  return { fans, loading, error, search, reset };
}
