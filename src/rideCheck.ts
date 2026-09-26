import { forecastForWeekday } from "./stats";
import { DEFAULT_RIDE_MINUTES, fromShiftMinutes } from "./time";
import { APP_BY_ID, APP_IDS, type AppId, type DayForecast, type RideAdvice, type Shift } from "./types";

export function adviseRide(input: {
  app: AppId;
  nowMinutes: number;
  forecast: DayForecast;
  bufferMinutes?: number;
}): RideAdvice {
  const buffer = input.bufferMinutes ?? 5;
  const row = input.forecast.apps.find((item) => item.app === input.app);
  const avgRide = row?.avgMinutesPerRide ?? DEFAULT_RIDE_MINUTES;
  const typicalLeave = row?.avgLeaveMinutes ?? null;
  const finish = input.nowMinutes + avgRide;
  const latestAccept = row?.latestAcceptMinutes ?? null;
  const nextApp = APP_IDS[APP_IDS.indexOf(input.app) + 1] ?? null;
  const appName = APP_BY_ID[input.app].name;

  if (typicalLeave == null) {
    return {
      app: input.app,
      nowMinutes: input.nowMinutes,
      typicalLeaveMinutes: null,
      avgRideMinutes: avgRide,
      finishMinutes: finish,
      latestAcceptMinutes: null,
      shouldTake: true,
      reason: `Δεν υπάρχουν ακόμα αρκετές μέρες για το ${appName}. Κατάγραψε μερικές βάρδιες και ο μέσος όρος θα γίνει ακριβής.`,
      nextApp,
    };
  }

  const shouldTake = finish <= typicalLeave + buffer;
  const leaveLabel = fromShiftMinutes(typicalLeave);
  const finishLabel = fromShiftMinutes(finish);
  const lastLabel = latestAccept != null ? fromShiftMinutes(latestAccept) : null;
  const rideLabel = Math.round(avgRide);

  if (shouldTake) {
    return {
      app: input.app,
      nowMinutes: input.nowMinutes,
      typicalLeaveMinutes: typicalLeave,
      avgRideMinutes: avgRide,
      finishMinutes: finish,
      latestAcceptMinutes: latestAccept,
      shouldTake: true,
      reason: `Πάρ’ το. Στο ${appName} συνήθως φεύγεις στις ${leaveLabel}. Ένα νούμερο κρατάει ~${rideLabel} λεπτά, οπότε τελειώνεις στις ${finishLabel}.`,
      nextApp,
    };
  }

  const nextName = nextApp ? APP_BY_ID[nextApp].name : null;
  const switchHint = nextName ? ` Καλύτερα πέρασε στο ${nextName}.` : "";
  const lastHint = lastLabel ? ` Τελευταία ώρα για νούμερο: ${lastLabel}.` : "";

  return {
    app: input.app,
    nowMinutes: input.nowMinutes,
    typicalLeaveMinutes: typicalLeave,
    avgRideMinutes: avgRide,
    finishMinutes: finish,
    latestAcceptMinutes: latestAccept,
    shouldTake: false,
    reason: `Μην το πάρεις αν θες να είσαι στην ώρα σου. Συνήθως φεύγεις από ${appName} στις ${leaveLabel}, αλλά αυτό θα σε πάει στις ${finishLabel}.${switchHint}${lastHint}`,
    nextApp,
  };
}

export function adviseRideFromShifts(input: {
  app: AppId;
  nowMinutes: number;
  weekday: number;
  shifts: Shift[];
  bufferMinutes?: number;
}): RideAdvice {
  return adviseRide({
    app: input.app,
    nowMinutes: input.nowMinutes,
    forecast: forecastForWeekday(input.shifts, input.weekday),
    bufferMinutes: input.bufferMinutes,
  });
}
