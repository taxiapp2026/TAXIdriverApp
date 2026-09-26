export const APP_IDS = ["bolt", "uber", "freenow"] as const;
export type AppId = (typeof APP_IDS)[number];

export interface AppMeta {
  id: AppId;
  name: string;
  color: string;
}

export const APPS: AppMeta[] = [
  { id: "bolt", name: "Bolt", color: "#34d186" },
  { id: "uber", name: "Uber", color: "#4c8dff" },
  { id: "freenow", name: "FreeNow", color: "#ff6a3d" },
];

export const APP_BY_ID: Record<AppId, AppMeta> = Object.fromEntries(
  APPS.map((app) => [app.id, app]),
) as Record<AppId, AppMeta>;

export interface AppSlot {
  app: AppId;
  startTime: string | null;
  leaveTime: string | null;
  rides: number;
  stuck: boolean;
  skipped: boolean;
  notes: string;
}

export interface Shift {
  id: string;
  date: string;
  slots: AppSlot[];
  isDemo?: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AppAverages {
  app: AppId;
  samples: number;
  avgStartMinutes: number | null;
  avgLeaveMinutes: number | null;
  avgRides: number | null;
  avgMinutesPerRide: number | null;
  stuckRate: number;
  avgLeaveWhenStuck: number | null;
  avgLeaveWhenNotStuck: number | null;
  extraMinutesWhenStuck: number | null;
  minLeaveMinutes: number | null;
  maxLeaveMinutes: number | null;
}

export type ForecastSource = "weekday" | "blended" | "overall" | "demo" | "none";

export interface ForecastApp extends AppAverages {
  latestAcceptMinutes: number | null;
  source: ForecastSource;
}

export interface DayForecast {
  weekday: number;
  weekdayLabel: string;
  apps: ForecastApp[];
}

export interface RideAdvice {
  app: AppId;
  nowMinutes: number;
  typicalLeaveMinutes: number | null;
  avgRideMinutes: number;
  finishMinutes: number;
  latestAcceptMinutes: number | null;
  shouldTake: boolean;
  reason: string;
  nextApp: AppId | null;
}

export type TabId = "today" | "forecast" | "week" | "history";
