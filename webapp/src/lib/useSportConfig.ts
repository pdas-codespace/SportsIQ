"use client";
/**
 * useSportConfig — return sport labels from server-side DemoConfigProvider.
 *
 * The config is injected by the root layout (server component) so it is
 * available on the very first render — no fetch, no flash of wrong branding.
 * Falls back to DEFAULT_SPORT_LABELS only when rendered outside the provider
 * (should never happen in practice).
 */
import type { SportLabels } from "@/lib/sport-labels";
import { DEFAULT_SPORT_LABELS } from "@/lib/sport-labels";
import { useDemoConfig } from "@/lib/DemoConfigProvider";

export function useSportConfig(): SportLabels {
  const ctx = useDemoConfig();
  return ctx?.sport ?? DEFAULT_SPORT_LABELS;
}
