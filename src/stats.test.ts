import { describe, expect, it } from "vitest";
import { blendAverages, computeAppAverages, emptyShift, forecastForWeekday, latestAcceptTime, minutesPerRide } from "./stats";
import { fromShiftMinutes } from "./time";
import type { Shift } from "./types";

function shiftOn(
  date: string,
  values: Partial<Record<"bolt" | "uber" | "freenow", { start?: string; leave?: string; rides?: number; stuck?: boolean }>>,
): Shift {
  const shift = emptyShift(date, new Date("2026-09-26T12:00:00"));
  shift.slots = shift.slots.map((slot) => {
    const extra = values[slot.app];
    if (!extra) return slot;
    return {
      ...slot,
      startTime: extra.start ?? null,
      leaveTime: extra.leave ?? null,
      rides: extra.rides ?? 0,
      stuck: extra.stuck ?? false,
    };
  });
  return shift;
}

describe("minutes per ride", () => {
  it("uses the previous app leave time when start is missing", () => {
    const slot = {
      app: "uber" as const,
      startTime: null,
      leaveTime: "21:30",
      rides: 10,
      stuck: true,
      skipped: false,
      notes: "",
    };
    expect(minutesPerRide(slot, "19:00")).toBe(15);
  });
});

describe("averages", () => {
  const saturdays: Shift[] = [
    shiftOn("2026-09-05", {
      bolt: { start: "17:00", leave: "19:00", rides: 6 },
      uber: { start: "19:05", leave: "21:30", rides: 10, stuck: true },
      freenow: { start: "21:40", leave: "00:00", rides: 5 },
    }),
    shiftOn("2026-09-12", {
      bolt: { start: "16:50", leave: "18:50", rides: 5 },
      uber: { start: "19:00", leave: "21:20", rides: 7 },
      freenow: { start: "21:30", leave: "23:50", rides: 4 },
    }),
    shiftOn("2026-09-19", {
      bolt: { start: "17:10", leave: "19:10", rides: 7 },
      uber: { start: "19:15", leave: "21:40", rides: 10, stuck: true },
      freenow: { start: "21:45", leave: "00:10", rides: 6 },
    }),
  ];

  it("averages Saturday leave times including midnight FreeNow", () => {
    const bolt = computeAppAverages(saturdays, "bolt", 6);
    const uber = computeAppAverages(saturdays, "uber", 6);
    const freenow = computeAppAverages(saturdays, "freenow", 6);

    expect(fromShiftMinutes(bolt.avgLeaveMinutes!)).toBe("19:00");
    expect(fromShiftMinutes(uber.avgLeaveMinutes!)).toBe("21:30");
    expect(fromShiftMinutes(freenow.avgLeaveMinutes!)).toBe("00:00");
    expect(uber.avgRides).toBeCloseTo(9, 5);
    expect(uber.stuckRate).toBeCloseTo(2 / 3, 5);
    expect(uber.extraMinutesWhenStuck).toBeGreaterThan(0);
  });

  it("uses weekday samples when they are enough, otherwise blends", () => {
    const monday = shiftOn("2026-09-21", {
      bolt: { start: "17:00", leave: "18:30", rides: 4 },
    });
    const weekday = computeAppAverages([...saturdays, monday], "bolt", 1);
    const overall = computeAppAverages([...saturdays, monday], "bolt");
    const blended = blendAverages(weekday, overall);
    expect(weekday.samples).toBe(1);
    expect(blended.avgLeaveMinutes).not.toBe(weekday.avgLeaveMinutes);
    expect(blended.avgLeaveMinutes).toBeLessThan(overall.avgLeaveMinutes!);
  });

  it("suggests the last time to take a ride before leaving", () => {
    const sameUber = [
      shiftOn("2026-09-05", { uber: { start: "19:00", leave: "21:30", rides: 10 } }),
      shiftOn("2026-09-12", { uber: { start: "19:00", leave: "21:30", rides: 10 } }),
      shiftOn("2026-09-19", { uber: { start: "19:00", leave: "21:30", rides: 10 } }),
    ];
    const uber = computeAppAverages(sameUber, "uber", 6);
    const latest = latestAcceptTime(uber);
    expect(latest).not.toBeNull();
    expect(fromShiftMinutes(latest!)).toBe("21:15");
  });
});

describe("forecast", () => {
  it("builds a next-day plan from the same weekday", () => {
    const shifts = [
      shiftOn("2026-09-05", {
        bolt: { leave: "19:00", rides: 6 },
        uber: { leave: "21:30", rides: 10, stuck: true },
        freenow: { leave: "00:00", rides: 5 },
      }),
      shiftOn("2026-09-12", {
        bolt: { leave: "19:00", rides: 6 },
        uber: { leave: "21:30", rides: 10, stuck: true },
        freenow: { leave: "00:00", rides: 5 },
      }),
      shiftOn("2026-09-19", {
        bolt: { leave: "19:00", rides: 6 },
        uber: { leave: "21:30", rides: 10, stuck: true },
        freenow: { leave: "00:00", rides: 5 },
      }),
    ];

    const forecast = forecastForWeekday(shifts, 6);
    expect(forecast.weekdayLabel).toBe("Σάββατο");
    expect(forecast.apps[0].source).toBe("weekday");
    expect(fromShiftMinutes(forecast.apps[0].avgLeaveMinutes!)).toBe("19:00");
    expect(fromShiftMinutes(forecast.apps[1].avgLeaveMinutes!)).toBe("21:30");
    expect(fromShiftMinutes(forecast.apps[2].avgLeaveMinutes!)).toBe("00:00");
  });
});
