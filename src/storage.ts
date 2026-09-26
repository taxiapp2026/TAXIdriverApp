import { normalizeShift } from "./stats";
import type { Shift } from "./types";

const STORAGE_KEY = "taxi-shift-tracker-v1";

interface StorePayload {
  version: 1;
  shifts: Shift[];
}

function isSlot(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  const slot = value as Record<string, unknown>;
  return (
    (slot.app === "bolt" || slot.app === "uber" || slot.app === "freenow") &&
    (slot.startTime === null || typeof slot.startTime === "string") &&
    (slot.leaveTime === null || typeof slot.leaveTime === "string") &&
    typeof slot.rides === "number"
  );
}

function isShift(value: unknown): value is Shift {
  if (!value || typeof value !== "object") return false;
  const shift = value as Record<string, unknown>;
  return (
    typeof shift.id === "string" &&
    typeof shift.date === "string" &&
    Array.isArray(shift.slots) &&
    shift.slots.every(isSlot)
  );
}

export function loadShifts(): Shift[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StorePayload;
    if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.shifts)) return [];
    return parsed.shifts.filter(isShift).map(normalizeShift);
  } catch {
    return [];
  }
}

export function saveShifts(shifts: Shift[]): void {
  const payload: StorePayload = { version: 1, shifts: shifts.map(normalizeShift) };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

export function upsertShift(shifts: Shift[], next: Shift): Shift[] {
  const normalized = normalizeShift({ ...next, updatedAt: new Date().toISOString() });
  const index = shifts.findIndex((shift) => shift.date === normalized.date);
  if (index === -1) return [...shifts, normalized].sort((a, b) => a.date.localeCompare(b.date));
  const copy = [...shifts];
  copy[index] = { ...normalized, createdAt: shifts[index].createdAt };
  return copy;
}

export function deleteShift(shifts: Shift[], date: string): Shift[] {
  return shifts.filter((shift) => shift.date !== date);
}

export function exportPayload(shifts: Shift[]): string {
  return JSON.stringify({ version: 1, shifts }, null, 2);
}

export function importPayload(raw: string): Shift[] {
  const parsed = JSON.parse(raw) as StorePayload;
  if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.shifts)) {
    throw new Error("Μη έγκυρο αρχείο αντιγράφου.");
  }
  const shifts = parsed.shifts.filter(isShift).map(normalizeShift);
  if (!shifts.length) throw new Error("Το αρχείο δεν έχει βάρδιες.");
  return shifts;
}

export function hasDemoShifts(shifts: Shift[]): boolean {
  return shifts.some((shift) => shift.isDemo);
}
