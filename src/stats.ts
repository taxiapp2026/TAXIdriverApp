import { DEFAULT_RIDE_MINUTES, WEEKDAY_LABELS, durationMinutes, mean, toShiftMinutes, weekdayOf } from "./time";
import { APP_IDS, type AppAverages, type AppId, type AppSlot, type DayForecast, type ForecastApp, type ForecastSource, type Shift } from "./types";

export function emptySlot(app: AppId): AppSlot {
  return {
    app,
    startTime: null,
    leaveTime: null,
    rides: 0,
    stuck: false,
    skipped: false,
    notes: "",
  };
}

export function emptyShift(date: string, now = new Date()): Shift {
  const iso = now.toISOString();
  return {
    id: `shift-${date}`,
    date,
    slots: APP_IDS.map(emptySlot),
    createdAt: iso,
    updatedAt: iso,
  };
}

export function normalizeShift(shift: Shift): Shift {
  const byApp = new Map(shift.slots.map((slot) => [slot.app, slot]));
  return {
    ...shift,
    slots: APP_IDS.map((app) => byApp.get(app) ?? emptySlot(app)),
  };
}

export function previousLeave(shift: Shift, app: AppId): string | null {
  const index = APP_IDS.indexOf(app);
  for (let i = index - 1; i >= 0; i -= 1) {
    const slot = shift.slots.find((item) => item.app === APP_IDS[i]);
    if (slot?.leaveTime) return slot.leaveTime;
  }
  return null;
}

export function inferredStart(shift: Shift, app: AppId): string | null {
  const slot = shift.slots.find((item) => item.app === app);
  return slot?.startTime ?? previousLeave(shift, app);
}

export function minutesPerRide(slot: AppSlot, previousLeaveTime: string | null): number | null {
  if (slot.rides <= 0) return null;
  const start = slot.startTime ?? previousLeaveTime;
  const duration = durationMinutes(start, slot.leaveTime);
  if (duration == null) return null;
  return duration / slot.rides;
}

function slotHasWork(slot: AppSlot): boolean {
  if (slot.skipped) return false;
  return Boolean(slot.startTime || slot.leaveTime || slot.rides > 0);
}

export function computeAppAverages(shifts: Shift[], app: AppId, weekday?: number): AppAverages {
  const relevant = weekday == null ? shifts : shifts.filter((shift) => weekdayOf(shift.date) === weekday);
  const leave: number[] = [];
  const start: number[] = [];
  const rides: number[] = [];
  const perRide: number[] = [];
  const leaveStuck: number[] = [];
  const leaveFree: number[] = [];
  let used = 0;
  let stuckCount = 0;

  for (const shift of relevant) {
    const slot = normalizeShift(shift).slots.find((item) => item.app === app);
    if (!slot || !slotHasWork(slot)) continue;
    used += 1;
    const prev = previousLeave(shift, app);
    const leaveMin = slot.leaveTime ? toShiftMinutes(slot.leaveTime) : null;
    const startMin = inferredStart(shift, app) ? toShiftMinutes(inferredStart(shift, app)!) : null;

    if (leaveMin != null) {
      leave.push(leaveMin);
      if (slot.stuck) leaveStuck.push(leaveMin);
      else leaveFree.push(leaveMin);
    }
    if (startMin != null) start.push(startMin);
    if (slot.rides > 0) rides.push(slot.rides);
    const rideMinutes = minutesPerRide(slot, prev);
    if (rideMinutes != null) perRide.push(rideMinutes);
    if (slot.stuck) stuckCount += 1;
  }

  const avgStuck = mean(leaveStuck);
  const avgFree = mean(leaveFree);

  return {
    app,
    samples: used,
    avgStartMinutes: mean(start),
    avgLeaveMinutes: mean(leave),
    avgRides: mean(rides),
    avgMinutesPerRide: mean(perRide),
    stuckRate: used ? stuckCount / used : 0,
    avgLeaveWhenStuck: avgStuck,
    avgLeaveWhenNotStuck: avgFree,
    extraMinutesWhenStuck:
      avgStuck != null && avgFree != null ? avgStuck - avgFree : null,
    minLeaveMinutes: leave.length ? Math.min(...leave) : null,
    maxLeaveMinutes: leave.length ? Math.max(...leave) : null,
  };
}

export function mixNumber(primary: number | null, fallback: number | null, weight: number): number | null {
  if (primary == null) return fallback;
  if (fallback == null) return primary;
  return primary * weight + fallback * (1 - weight);
}

export function blendAverages(primary: AppAverages, fallback: AppAverages): AppAverages {
  if (primary.samples >= 3) return primary;
  if (primary.samples === 0) return fallback;
  if (fallback.samples === 0) return primary;
  const weight = primary.samples / (primary.samples + 1);
  return {
    ...primary,
    avgStartMinutes: mixNumber(primary.avgStartMinutes, fallback.avgStartMinutes, weight),
    avgLeaveMinutes: mixNumber(primary.avgLeaveMinutes, fallback.avgLeaveMinutes, weight),
    avgRides: mixNumber(primary.avgRides, fallback.avgRides, weight),
    avgMinutesPerRide: mixNumber(primary.avgMinutesPerRide, fallback.avgMinutesPerRide, weight),
  };
}

export function latestAcceptTime(averages: AppAverages): number | null {
  if (averages.avgLeaveMinutes == null) return null;
  const rideMinutes = averages.avgMinutesPerRide ?? DEFAULT_RIDE_MINUTES;
  return Math.round(averages.avgLeaveMinutes - rideMinutes);
}

export function forecastForWeekday(shifts: Shift[], weekday: number): DayForecast {
  return {
    weekday,
    weekdayLabel: WEEKDAY_LABELS[weekday],
    apps: APP_IDS.map((app) => {
      const { averages, source } = averagesForForecast(shifts, app, weekday);
      return {
        ...averages,
        latestAcceptMinutes: latestAcceptTime(averages),
        source,
      } satisfies ForecastApp;
    }),
  };
}

export function realShifts(shifts: Shift[]): Shift[] {
  return shifts.filter((shift) => !shift.isDemo);
}

export function demoShifts(shifts: Shift[]): Shift[] {
  return shifts.filter((shift) => shift.isDemo);
}

export function shiftsForStats(shifts: Shift[]): Shift[] {
  const real = realShifts(shifts);
  return real.length ? real : shifts;
}

export function averagesForForecast(
  shifts: Shift[],
  app: AppId,
  weekday: number,
): { averages: AppAverages; source: ForecastSource } {
  const real = realShifts(shifts);
  const demo = demoShifts(shifts);
  const dayReal = computeAppAverages(real, app, weekday);
  const allReal = computeAppAverages(real, app);

  if (dayReal.samples >= 3) return { averages: dayReal, source: "weekday" };
  if (dayReal.samples > 0) {
    const fallback = allReal.samples > 0 ? allReal : computeAppAverages(demo, app);
    return { averages: blendAverages(dayReal, fallback), source: "blended" };
  }
  if (allReal.samples > 0) return { averages: allReal, source: "overall" };

  const dayDemo = computeAppAverages(demo, app, weekday);
  const allDemo = computeAppAverages(demo, app);
  const blended = blendAverages(dayDemo, allDemo);
  if (blended.samples > 0) return { averages: blended, source: "demo" };
  return { averages: blended, source: "none" };
}
