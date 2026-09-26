import { describe, expect, it } from "vitest";
import {
  addDays,
  durationMinutes,
  formatDisplayDate,
  fromShiftMinutes,
  mean,
  median,
  startOfWeekMonday,
  toShiftMinutes,
  weekdayOf,
} from "./time";

describe("shift clock", () => {
  it("keeps evening times on the same shift day", () => {
    expect(toShiftMinutes("19:00")).toBe(19 * 60);
    expect(toShiftMinutes("21:30")).toBe(21 * 60 + 30);
  });

  it("treats midnight and morning as after the evening shift", () => {
    expect(toShiftMinutes("00:00")).toBe(24 * 60);
    expect(toShiftMinutes("02:15")).toBe(26 * 60 + 15);
    expect(fromShiftMinutes(24 * 60)).toBe("00:00");
    expect(fromShiftMinutes(26 * 60 + 15)).toBe("02:15");
  });

  it("measures overnight duration", () => {
    expect(durationMinutes("21:40", "00:00")).toBe(140);
    expect(durationMinutes("19:00", "21:30")).toBe(150);
  });

  it("rejects invalid times", () => {
    expect(toShiftMinutes("25:00")).toBeNull();
    expect(toShiftMinutes("19")).toBeNull();
  });
});

describe("calendar helpers", () => {
  it("formats and walks dates", () => {
    expect(formatDisplayDate("2026-09-26")).toBe("26/09/2026");
    expect(addDays("2026-09-26", 1)).toBe("2026-09-27");
    expect(weekdayOf("2026-09-26")).toBe(6);
    expect(startOfWeekMonday("2026-09-26")).toBe("2026-09-21");
  });

  it("computes mean and median", () => {
    expect(mean([10, 20, 30])).toBe(20);
    expect(median([10, 20, 30])).toBe(20);
    expect(median([10, 20])).toBe(15);
    expect(mean([])).toBeNull();
  });
});
