import { describe, expect, it } from "vitest";
import { adviseRideFromShifts } from "./rideCheck";
import { emptyShift } from "./stats";
import { toShiftMinutes } from "./time";
import type { Shift } from "./types";

function saturday(date: string): Shift {
  const shift = emptyShift(date, new Date("2026-09-26T12:00:00"));
  shift.slots = [
    { app: "bolt", startTime: "17:00", leaveTime: "19:00", rides: 6, stuck: false, skipped: false, notes: "" },
    { app: "uber", startTime: "19:00", leaveTime: "21:30", rides: 10, stuck: true, skipped: false, notes: "" },
    { app: "freenow", startTime: "21:40", leaveTime: "00:00", rides: 5, stuck: false, skipped: false, notes: "" },
  ];
  return shift;
}

describe("ride advice", () => {
  const shifts = [saturday("2026-09-05"), saturday("2026-09-12"), saturday("2026-09-19")];

  it("says yes when a ride still finishes before the usual leave time", () => {
    const advice = adviseRideFromShifts({
      app: "uber",
      nowMinutes: toShiftMinutes("21:00")!,
      weekday: 6,
      shifts,
    });
    expect(advice.shouldTake).toBe(true);
    expect(advice.reason).toContain("21:30");
    expect(advice.reason).toContain("Πάρ’");
  });

  it("says no when ten Uber rides already made the driver late", () => {
    const advice = adviseRideFromShifts({
      app: "uber",
      nowMinutes: toShiftMinutes("21:25")!,
      weekday: 6,
      shifts,
    });
    expect(advice.shouldTake).toBe(false);
    expect(advice.nextApp).toBe("freenow");
    expect(advice.reason).toContain("FreeNow");
    expect(advice.latestAcceptMinutes).toBe(toShiftMinutes("21:15"));
  });

  it("is honest when there is no history yet", () => {
    const advice = adviseRideFromShifts({
      app: "bolt",
      nowMinutes: toShiftMinutes("18:00")!,
      weekday: 1,
      shifts: [],
    });
    expect(advice.shouldTake).toBe(true);
    expect(advice.typicalLeaveMinutes).toBeNull();
    expect(advice.reason).toContain("αρκετές μέρες");
  });
});
