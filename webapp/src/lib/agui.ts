/**
 * AG-UI request helpers routed through the same-origin backend proxy.
 */
"use client";

export const agentsApiUrl = "/api/agents";

export interface RunSportContext {
  sport: string;
  league_name: string;
  home_team: string;
  home_team_name: string;
  away_team: string;
  away_team_name: string;
  venue_label: string;
  period_label: string;
}

export function createAgentRunStream(runId: string) {
  const url = `${agentsApiUrl}/api/run/${runId}/stream`;
  return new EventSource(url);
}

export async function startRun(
  fanId: string,
  gameId: string,
  fanName?: string,
  fanLoyaltyTier?: string,
  fanEmail?: string,
  preferredSectionId?: string,
  sportContext?: RunSportContext
): Promise<string> {
  const res = await fetch(`${agentsApiUrl}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      fan_id: fanId,
      game_id: gameId,
      ...(fanName && { fan_name: fanName }),
      ...(fanLoyaltyTier && { fan_loyalty_tier: fanLoyaltyTier }),
      ...(fanEmail && { fan_email: fanEmail }),
      ...(preferredSectionId && { preferred_section_id: preferredSectionId }),
      ...(sportContext && { sport_context: sportContext }),
    }),
  });
  if (!res.ok) throw new Error(`Failed to start run: ${res.statusText}`);
  const data = await res.json();
  return data.run_id as string;
}

export async function submitToolResult(
  runId: string,
  offerId: string,
  approved: boolean,
  reason: string = ""
): Promise<void> {
  const res = await fetch(`${agentsApiUrl}/api/run/${runId}/tool-result`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ offer_id: offerId, approved, reason }),
  });
  if (!res.ok) throw new Error(`Failed to submit tool result: ${res.statusText}`);
}

export async function simulateGameEvent(
  breakType: string,
  gameId: string
): Promise<import("./types").GameEventResponse> {
  const res = await fetch(`${agentsApiUrl}/api/game-event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ break_type: breakType, game_id: gameId }),
  });
  if (!res.ok) throw new Error(`Failed to simulate game event: ${res.statusText}`);
  return res.json();
}
