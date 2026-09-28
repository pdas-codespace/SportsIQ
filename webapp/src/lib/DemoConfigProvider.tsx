"use client";
/**
 * DemoConfigProvider — React context for server-side demo configuration.
 *
 * The layout (server component) reads SPORTS_IQ_SPORT and DEMO_GAME_ID from
 * process.env and passes the resolved config as a prop.  This eliminates the
 * flash of wrong branding that occurred when the client fetched /api/sport
 * after mount and rendered the default (football) labels in the meantime.
 */
import { createContext, useContext, type ReactNode } from "react";
import type { SportLabels } from "@/lib/sport-labels";

export interface DemoConfig {
  sport: SportLabels;
  gameId: string;
}

const DemoConfigContext = createContext<DemoConfig | null>(null);

export function DemoConfigProvider({
  config,
  children,
}: {
  config: DemoConfig;
  children: ReactNode;
}) {
  return (
    <DemoConfigContext.Provider value={config}>
      {children}
    </DemoConfigContext.Provider>
  );
}

export function useDemoConfig(): DemoConfig | null {
  return useContext(DemoConfigContext);
}
