export const SHIFT_DAY_START = 12 * 60;
export const DEFAULT_RIDE_MINUTES = 15;

export const WEEKDAY_LABELS = [
  "Κυριακή",
  "Δευτέρα",
  "Τρίτη",
  "Τετάρτη",
  "Πέμπτη",
  "Παρασκευή",
  "Σάββατο",
] as const;

export const WEEKDAY_SHORT = ["Κυρ", "Δευ", "Τρί", "Τετ", "Πέμ", "Παρ", "Σάβ"] as const;

export function parseHhmm(value: string): { h: number; m: number } | null {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const h = Number(match[1]);
  const m = Number(match[2]);
  if (h < 0 || h > 23 || m < 0 || m > 59) return null;
  return { h, m };
}

export function toShiftMinutes(hhmm: string): number | null {
  const parsed = parseHhmm(hhmm);
  if (!parsed) return null;
  let minutes = parsed.h * 60 + parsed.m;
  if (minutes < SHIFT_DAY_START) minutes += 24 * 60;
  return minutes;
}

export function fromShiftMinutes(minutes: number): string {
  const day = 24 * 60;
  let clock = Math.round(minutes) % day;
  if (clock < 0) clock += day;
  const h = Math.floor(clock / 60);
  const m = clock % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function formatMinutesLabel(minutes: number | null): string {
  if (minutes == null || Number.isNaN(minutes)) return "—";
  return fromShiftMinutes(minutes);
}

export function durationMinutes(start: string | null, leave: string | null): number | null {
  if (!start || !leave) return null;
  const a = toShiftMinutes(start);
  const b = toShiftMinutes(leave);
  if (a == null || b == null) return null;
  const diff = b - a;
  return diff > 0 ? diff : null;
}

export function parseISODate(date: string): Date {
  const [year, month, day] = date.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function toISODate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatDisplayDate(date: string): string {
  const dt = parseISODate(date);
  return `${String(dt.getDate()).padStart(2, "0")}/${String(dt.getMonth() + 1).padStart(2, "0")}/${dt.getFullYear()}`;
}

export function addDays(date: string, days: number): string {
  const dt = parseISODate(date);
  dt.setDate(dt.getDate() + days);
  return toISODate(dt);
}

export function weekdayOf(date: string): number {
  return parseISODate(date).getDay();
}

export function todayISO(now = new Date()): string {
  return toISODate(now);
}

export function nowShiftMinutes(now = new Date()): number {
  const hhmm = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  return toShiftMinutes(hhmm) ?? SHIFT_DAY_START;
}

export function startOfWeekMonday(date: string): string {
  const dt = parseISODate(date);
  const day = dt.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  dt.setDate(dt.getDate() + diff);
  return toISODate(dt);
}

export function mean(values: number[]): number | null {
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function roundMinutes(value: number | null): number | null {
  if (value == null) return null;
  return Math.round(value);
}
