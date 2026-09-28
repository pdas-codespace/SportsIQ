/**
 * Sport-specific UI labels and configuration for the Sports-IQ demo webapp.
 *
 * The active sport is controlled via the SPORTS_IQ_SPORT environment variable,
 * read server-side by the /api/sport route and served to the client as JSON.
 * This allows per-deployment branding without a webapp image rebuild.
 */

export interface BreakOption {
  value: string;
  label: string;
  icon: string;
}

export interface DemoGame {
  homeTeam: string;
  homeTeamName: string;
  awayTeam: string;
  awayTeamName: string;
  homeScore: number;
  awayScore: number;
  period: string;
  clock: string;
}

export interface SportLabels {
  sport: string;
  emoji: string;
  leagueName: string;
  displayName: string;
  headerSubtitle: string;
  demoLabel: string;
  venueLabel: string;
  periodLabel: string;
  criticalMomentLabel: string;
  stadiumEmoji: string;
  breakTypes: BreakOption[];
  demoGame: DemoGame;
}

const FOOTBALL: SportLabels = {
  sport: "football",
  emoji: "🏈",
  leagueName: "Professional Football",
  displayName: "Football Fan Engagement",
  headerSubtitle: "Football Fan Engagement · Microsoft Fabric + Microsoft Foundry",
  demoLabel: "Football Demo",
  venueLabel: "Stadium",
  periodLabel: "Quarter",
  criticalMomentLabel: "Red Zone",
  stadiumEmoji: "🏟️",
  breakTypes: [
    { value: "commercial",         label: "Commercial",    icon: "📺" },
    { value: "tv_timeout",         label: "TV Timeout",    icon: "⏱️" },
    { value: "halftime",           label: "Halftime",      icon: "🏈" },
    { value: "two_minute_warning", label: "2-Min Warning", icon: "⚠️" },
  ],
  demoGame: {
    homeTeam: "HCC",
    homeTeamName: "Harbor City Comets",
    awayTeam: "MST",
    awayTeamName: "Metro Stars",
    homeScore: 14,
    awayScore: 10,
    period: "Q2",
    clock: "2:03",
  },
};

const BASKETBALL: SportLabels = {
  sport: "basketball",
  emoji: "🏀",
  leagueName: "Professional Basketball",
  displayName: "Basketball Fan Engagement",
  headerSubtitle: "Basketball Fan Engagement · Microsoft Fabric + Microsoft Foundry",
  demoLabel: "Basketball Demo",
  venueLabel: "Arena",
  periodLabel: "Quarter",
  criticalMomentLabel: "Clutch Time",
  stadiumEmoji: "🏟️",
  breakTypes: [
    { value: "timeout",         label: "Timeout",    icon: "⏱️" },
    { value: "tv_timeout",      label: "TV Timeout", icon: "📺" },
    { value: "halftime",        label: "Halftime",   icon: "🏀" },
    { value: "end_of_quarter",  label: "End of Q",   icon: "🔔" },
  ],
  demoGame: {
    homeTeam: "HCC",
    homeTeamName: "Harbor City Comets",
    awayTeam: "MST",
    awayTeamName: "Metro Stars",
    homeScore: 54,
    awayScore: 48,
    period: "Q2",
    clock: "3:42",
  },
};

const SOCCER: SportLabels = {
  sport: "soccer",
  emoji: "⚽",
  leagueName: "Professional Soccer",
  displayName: "Soccer Fan Engagement",
  headerSubtitle: "Soccer Fan Engagement · Microsoft Fabric + Microsoft Foundry",
  demoLabel: "Soccer Demo",
  venueLabel: "Stadium",
  periodLabel: "Half",
  criticalMomentLabel: "Penalty Area",
  stadiumEmoji: "⚽",
  breakTypes: [
    { value: "halftime",          label: "Halftime",   icon: "⚽" },
    { value: "var_review",        label: "VAR Review", icon: "🔍" },
    { value: "water_break",       label: "Water Break", icon: "💧" },
    { value: "substitution",      label: "Sub",        icon: "🔄" },
  ],
  demoGame: {
    homeTeam: "HCC",
    homeTeamName: "Harbor City Comets",
    awayTeam: "MST",
    awayTeamName: "Metro Stars",
    homeScore: 2,
    awayScore: 1,
    period: "H2",
    clock: "67:12",
  },
};

const HOCKEY: SportLabels = {
  sport: "hockey",
  emoji: "🏒",
  leagueName: "Professional Hockey",
  displayName: "Hockey Fan Engagement",
  headerSubtitle: "Hockey Fan Engagement · Microsoft Fabric + Microsoft Foundry",
  demoLabel: "Hockey Demo",
  venueLabel: "Arena",
  periodLabel: "Period",
  criticalMomentLabel: "Power Play",
  stadiumEmoji: "🧊",
  breakTypes: [
    { value: "tv_timeout",   label: "TV Timeout",   icon: "📺" },
    { value: "intermission", label: "Intermission", icon: "🏒" },
    { value: "penalty_break", label: "Penalty",     icon: "⚡" },
    { value: "commercial",   label: "Commercial",   icon: "📻" },
  ],
  demoGame: {
    homeTeam: "HCC",
    homeTeamName: "Harbor City Comets",
    awayTeam: "MST",
    awayTeamName: "Metro Stars",
    homeScore: 3,
    awayScore: 2,
    period: "P2",
    clock: "8:45",
  },
};

export const SPORT_LABELS: Record<string, SportLabels> = {
  football:   FOOTBALL,
  basketball: BASKETBALL,
  soccer:     SOCCER,
  hockey:     HOCKEY,
};

export const DEFAULT_SPORT_LABELS: SportLabels = BASKETBALL;
