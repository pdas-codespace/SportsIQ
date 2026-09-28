import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { SPORT_LABELS, DEFAULT_SPORT_LABELS } from "@/lib/sport-labels";
import { DemoConfigProvider } from "@/lib/DemoConfigProvider";

export const metadata: Metadata = {
  title: "Sports-IQ | Fan Engagement Demo",
  description: "Real-time AI-powered fan offer generation with human-in-the-loop approval",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Force dynamic rendering so env vars are read at request time, not build time
  await headers();

  const sportKey = (process.env.SPORTS_IQ_SPORT ?? "football").toLowerCase().trim();
  const sport = SPORT_LABELS[sportKey] ?? DEFAULT_SPORT_LABELS;
  const gameId = process.env.DEMO_GAME_ID ?? "demo_game";

  return (
    <html lang="en">
      <body className="bg-brand-dark text-white antialiased min-h-screen font-sans">
        <DemoConfigProvider config={{ sport, gameId }}>
          {children}
        </DemoConfigProvider>
      </body>
    </html>
  );
}
