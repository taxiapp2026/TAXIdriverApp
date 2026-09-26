import { afterEach, describe, expect, it } from "vitest";
import { emptyShift } from "./stats";
import { deleteShift, exportPayload, importPayload, upsertShift } from "./storage";

describe("shift collection", () => {
  afterEach(() => {
    // storage helpers used here are pure except load/save
  });

  it("replaces a shift on the same date and keeps order", () => {
    const first = emptyShift("2026-09-25");
    first.slots[0].leaveTime = "19:00";
    const second = emptyShift("2026-09-26");
    const updated = emptyShift("2026-09-25");
    updated.slots[0].leaveTime = "19:15";
    updated.slots[1].rides = 10;

    const next = upsertShift(upsertShift([second], first), updated);
    expect(next.map((shift) => shift.date)).toEqual(["2026-09-25", "2026-09-26"]);
    expect(next[0].slots[0].leaveTime).toBe("19:15");
    expect(next[0].slots[1].rides).toBe(10);
  });

  it("exports and imports a backup", () => {
    const shifts = [emptyShift("2026-09-26")];
    shifts[0].slots[1].rides = 10;
    const raw = exportPayload(shifts);
    const imported = importPayload(raw);
    expect(imported).toHaveLength(1);
    expect(imported[0].slots[1].rides).toBe(10);
  });

  it("rejects a broken backup", () => {
    expect(() => importPayload("{}")).toThrow(/Μη έγκυρο/);
  });

  it("deletes by date", () => {
    const shifts = [emptyShift("2026-09-25"), emptyShift("2026-09-26")];
    expect(deleteShift(shifts, "2026-09-25")).toHaveLength(1);
  });
});
