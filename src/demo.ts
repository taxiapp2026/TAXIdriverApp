import { emptyShift } from "./stats";
import { addDays, todayISO, weekdayOf } from "./time";
import type { AppId, Shift } from "./types";

type Pattern = Record<AppId, [start: string, leave: string, rides: number, stuck: boolean]>;

const PATTERNS: Record<number, Pattern> = {
  0: {
    bolt: ["16:20", "18:35", 5, false],
    uber: ["18:40", "20:45", 6, false],
    freenow: ["20:50", "23:10", 4, false],
  },
  1: {
    bolt: ["17:10", "19:20", 6, false],
    uber: ["19:25", "21:15", 5, false],
    freenow: ["21:20", "23:40", 4, false],
  },
  2: {
    bolt: ["17:00", "19:05", 5, false],
    uber: ["19:10", "21:20", 7, false],
    freenow: ["21:25", "23:50", 5, false],
  },
  3: {
    bolt: ["17:15", "19:10", 5, false],
    uber: ["19:15", "21:25", 6, false],
    freenow: ["21:30", "23:55", 4, false],
  },
  4: {
    bolt: ["17:00", "19:00", 6, false],
    uber: ["19:05", "21:35", 8, false],
    freenow: ["21:40", "00:10", 5, false],
  },
  5: {
    bolt: ["16:50", "18:55", 6, false],
    uber: ["19:00", "21:40", 9, true],
    freenow: ["21:50", "00:20", 6, false],
  },
  6: {
    bolt: ["17:00", "19:00", 6, false],
    uber: ["19:05", "21:30", 10, true],
    freenow: ["21:40", "00:00", 5, false],
  },
};

function jitterMinutes(date: string, base: string, spread: number): string {
  const [hours, minutes] = base.split(":").map(Number);
  const day = Number(date.slice(-2));
  const offset = ((day % 3) - 1) * spread;
  const total = hours * 60 + minutes + offset;
  const wrapped = ((total % (24 * 60)) + 24 * 60) % (24 * 60);
  const nextHours = Math.floor(wrapped / 60);
  const nextMinutes = wrapped % 60;
  return `${String(nextHours).padStart(2, "0")}:${String(nextMinutes).padStart(2, "0")}`;
}

export function createDemoShifts(now = new Date()): Shift[] {
  const today = todayISO(now);
  const shifts: Shift[] = [];

  for (let back = 21; back >= 1; back -= 1) {
    const date = addDays(today, -back);
    const weekday = weekdayOf(date);
    const pattern = PATTERNS[weekday];
    const shift = emptyShift(date, now);
    shift.isDemo = true;
    shift.slots = shift.slots.map((slot) => {
      const [start, leave, rides, stuck] = pattern[slot.app];
      return {
        ...slot,
        startTime: jitterMinutes(date, start, 5),
        leaveTime: jitterMinutes(date, leave, 5),
        rides: rides + (Number(date.slice(-2)) % 2),
        stuck: slot.app === "uber" ? stuck && Number(date.slice(-2)) % 2 === 0 : stuck,
        notes: stuck ? "Κόλλησε από πολλά νούμερα" : "",
      };
    });
    shifts.push(shift);
  }

  return shifts;
}
