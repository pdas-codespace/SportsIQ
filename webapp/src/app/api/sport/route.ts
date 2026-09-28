/**
 * GET /api/sport
 *
 * Returns the SportLabels JSON for the currently configured sport.
 * Reads SPORTS_IQ_SPORT from the server environment — this is NOT a
 * NEXT_PUBLIC_ variable, so it can be changed per ACA deployment without
 * rebuilding the webapp image. The client fetches this once on mount via
 * the useSportConfig() hook.
 */
import { NextResponse } from "next/server";
import { SPORT_LABELS, DEFAULT_SPORT_LABELS } from "@/lib/sport-labels";

// Force dynamic so Next.js re-evaluates process.env on every request
// instead of caching the response at build time.
export const dynamic = "force-dynamic";

export function GET() {
  const sport = (process.env.SPORTS_IQ_SPORT ?? "basketball").toLowerCase().trim();
  const labels = SPORT_LABELS[sport] ?? DEFAULT_SPORT_LABELS;
  return NextResponse.json(labels);
}
