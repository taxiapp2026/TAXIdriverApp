import { createDemoShifts } from "./demo";
import { adviseRide } from "./rideCheck";
import { emptyShift, forecastForWeekday, normalizeShift, realShifts, shiftsForStats } from "./stats";
import {
  deleteShift,
  exportPayload,
  hasDemoShifts,
  importPayload,
  loadShifts,
  saveShifts,
  upsertShift,
} from "./storage";
import {
  WEEKDAY_LABELS,
  WEEKDAY_SHORT,
  addDays,
  formatDisplayDate,
  formatMinutesLabel,
  nowShiftMinutes,
  startOfWeekMonday,
  todayISO,
  toShiftMinutes,
  weekdayOf,
} from "./time";
import { APP_BY_ID, APP_IDS, type AppId, type AppSlot, type Shift, type TabId } from "./types";

interface State {
  tab: TabId;
  selectedDate: string;
  weekStart: string;
  forecastWeekday: number;
  checkApp: AppId;
  checkTime: string;
  shifts: Shift[];
  toast: string | null;
}

const tabs: Array<{ id: TabId; label: string }> = [
  { id: "today", label: "Σήμερα" },
  { id: "forecast", label: "Αύριο" },
  { id: "week", label: "Εβδομάδα" },
  { id: "history", label: "Ιστορικό" },
];

function currentClock(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function sourceLabel(source: string): string {
  if (source === "weekday") return "ίδια μέρα";
  if (source === "blended") return "ίδια μέρα + γενικός μέσος";
  if (source === "overall") return "γενικός μέσος όρος";
  return "λίγα στοιχεία";
}

export function createApp(root: HTMLElement): void {
  const today = todayISO();
  const state: State = {
    tab: "today",
    selectedDate: today,
    weekStart: startOfWeekMonday(today),
    forecastWeekday: weekdayOf(addDays(today, 1)),
    checkApp: "uber",
    checkTime: currentClock(),
    shifts: loadShifts(),
    toast: null,
  };

  let toastTimer = 0;

  function persist(next: Shift[]): void {
    state.shifts = next;
    saveShifts(next);
  }

  function toast(message: string): void {
    state.toast = message;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      state.toast = null;
      render();
    }, 2600);
    render();
  }

  function shiftFor(date: string): Shift {
    return normalizeShift(state.shifts.find((shift) => shift.date === date) ?? emptyShift(date));
  }

  function patchSlot(date: string, app: AppId, patch: Partial<AppSlot>): void {
    const shift = shiftFor(date);
    shift.slots = shift.slots.map((slot) => (slot.app === app ? { ...slot, ...patch } : slot));
    persist(upsertShift(state.shifts, shift));
    render();
  }

  function renderToday(): string {
    const shift = shiftFor(state.selectedDate);
    const weekday = WEEKDAY_LABELS[weekdayOf(state.selectedDate)];
    const filled = shift.slots.filter((slot) => slot.leaveTime || slot.rides);
    const summary = filled
      .map((slot) => `${APP_BY_ID[slot.app].name} ${slot.leaveTime ?? "—"}`)
      .join(" · ");

    return `
      <div class="card">
        <label class="field">Ημέρα βάρδιας
          <input type="date" data-action="date" value="${shift.date}">
        </label>
        <p class="muted">${weekday}. Κατάγραψε πότε έφυγες από κάθε εφαρμογή και πόσα νούμερα πήρες.</p>
      </div>
      ${shift.slots
        .map((slot) => {
          const start = slot.startTime ?? "";
          const leave = slot.leaveTime ?? "";
          return `
            <section class="card app ${slot.app}">
              <div class="row">
                <h2>${APP_BY_ID[slot.app].name}</h2>
                <button class="toggle ${slot.stuck ? "on" : ""}" data-action="stuck" data-app="${slot.app}">
                  ${slot.stuck ? "Κόλλησε" : "Κόλλησε;"}
                </button>
              </div>
              <div class="fields" style="margin-top:12px">
                <label class="field">Άνοιξα
                  <input type="time" data-action="start" data-app="${slot.app}" value="${start}">
                </label>
                <label class="field">Έφυγα
                  <input type="time" data-action="leave" data-app="${slot.app}" value="${leave}">
                </label>
              </div>
              <label class="field" style="margin-top:10px">Νούμερα
                <div class="stepper">
                  <button type="button" data-action="rides" data-app="${slot.app}" data-delta="-1">−</button>
                  <strong>${slot.rides}</strong>
                  <button type="button" data-action="rides" data-app="${slot.app}" data-delta="1">+</button>
                </div>
              </label>
              <label class="field" style="margin-top:10px">Σημείωση
                <input type="text" data-action="notes" data-app="${slot.app}" value="${escapeHtml(slot.notes)}" placeholder="π.χ. 10 νούμερα και κόλλησε">
              </label>
            </section>
          `;
        })
        .join("")}
      ${summary ? `<div class="banner info">Σήμερα: ${escapeHtml(summary)}</div>` : ""}
      <p class="muted">Αποθηκεύεται μόνο σε αυτή τη συσκευή. Όσο μαζεύεις μέρες, ο μέσος όρος για αύριο γίνεται πιο ακριβής.</p>
    `;
  }

  function renderForecast(): string {
    const statsShifts = shiftsForStats(state.shifts);
    const forecast = forecastForWeekday(statsShifts, state.forecastWeekday);
    const tomorrow = addDays(todayISO(), 1);
    const isTomorrow = state.forecastWeekday === weekdayOf(tomorrow);
    const nowMinutes = toShiftMinutes(state.checkTime) ?? nowShiftMinutes();
    const advice = adviseRide({
      app: state.checkApp,
      nowMinutes,
      forecast,
    });
    const demoNote = realShifts(state.shifts).length === 0 && state.shifts.length
      ? `<div class="banner info">Βλέπεις παράδειγμα εβδομάδων. Βάλε τις δικές σου μέρες από το Σήμερα για να γίνει δικός σου ο μέσος όρος.</div>`
      : "";

    return `
      ${demoNote}
      <div class="card">
        <h2>${isTomorrow ? "Αύριο" : "Μέσος όρος"} · ${forecast.weekdayLabel}</h2>
        <p class="muted">Με βάση τις προηγούμενες ${forecast.weekdayLabel} και όλη την εβδομάδα, αυτές είναι οι ώρες που συνήθως φεύγεις.</p>
        <div class="chips" style="margin-top:12px">
          ${WEEKDAY_LABELS.map(
            (label, index) => `
              <button class="chip ${index === state.forecastWeekday ? "on" : ""}" data-action="forecast-day" data-day="${index}">${label}</button>
            `,
          ).join("")}
        </div>
      </div>
      <div class="timeline">
        ${forecast.apps
          .map((app) => {
            const stuck =
              app.extraMinutesWhenStuck && app.stuckRate >= 0.3
                ? `Όταν έχεις πολλά νούμερα και κολλάς, φεύγεις ~${Math.round(app.extraMinutesWhenStuck)} λεπτά αργότερα.`
                : "";
            return `
              <section class="card app ${app.app}">
                <div class="row">
                  <h3>${APP_BY_ID[app.app].name}</h3>
                  <span class="muted">${sourceLabel(app.source)}</span>
                </div>
                <div class="time-big">${formatMinutesLabel(app.avgLeaveMinutes)}</div>
                <div class="kpi">
                  <div><span>Νούμερα</span><b>${app.avgRides == null ? "—" : app.avgRides.toFixed(1)}</b></div>
                  <div><span>Ανά νούμερο</span><b>${app.avgMinutesPerRide == null ? "—" : `${Math.round(app.avgMinutesPerRide)}′`}</b></div>
                  <div><span>Τελευταίο νούμερο</span><b>${formatMinutesLabel(app.latestAcceptMinutes)}</b></div>
                </div>
                ${stuck ? `<p class="muted" style="margin:10px 0 0">${stuck}</p>` : ""}
              </section>
            `;
          })
          .join("")}
      </div>
      <section class="card">
        <h2>Παίρνω νούμερο τώρα;</h2>
        <p class="muted">Βάλε την εφαρμογή και την ώρα, για να δεις αν προλαβαίνεις να φύγεις στην ώρα του μέσου όρου.</p>
        <div class="fields" style="margin-top:12px">
          <label class="field">Εφαρμογή
            <select data-action="check-app">
              ${APP_IDS.map(
                (id) => `<option value="${id}" ${id === state.checkApp ? "selected" : ""}>${APP_BY_ID[id].name}</option>`,
              ).join("")}
            </select>
          </label>
          <label class="field">Ώρα τώρα
            <input type="time" data-action="check-time" value="${state.checkTime}">
          </label>
        </div>
        <div class="banner ${advice.shouldTake ? "good" : "bad"}" style="margin:14px 0 0">
          ${escapeHtml(advice.reason)}
        </div>
      </section>
    `;
  }

  function renderWeek(): string {
    const days = Array.from({ length: 7 }, (_, index) => addDays(state.weekStart, index));
    const statsShifts = shiftsForStats(state.shifts);
    const end = addDays(state.weekStart, 6);

    return `
      <div class="card">
        <div class="row">
          <button class="ghost" style="width:auto" data-action="week-nav" data-delta="-7">‹</button>
          <div>
            <h2>${formatDisplayDate(state.weekStart)} – ${formatDisplayDate(end)}</h2>
            <p class="muted" style="margin:4px 0 0">Κάθε μέρα και ο μέσος όρος της ίδιας ημέρας σε όλη την ιστορία.</p>
          </div>
          <button class="ghost" style="width:auto" data-action="week-nav" data-delta="7">›</button>
        </div>
      </div>
      <div class="week">
        ${days
          .map((date) => {
            const shift = state.shifts.find((item) => item.date === date);
            const averages = forecastForWeekday(statsShifts, weekdayOf(date));
            return `
              <article class="week-day">
                <div>
                  <strong>${WEEKDAY_SHORT[weekdayOf(date)]}</strong>
                  <div class="muted">${formatDisplayDate(date).slice(0, 5)}</div>
                </div>
                <div class="week-apps">
                  ${APP_IDS.map((app) => {
                    const slot = shift?.slots.find((item) => item.app === app);
                    const avg = averages.apps.find((item) => item.app === app);
                    const actual = slot?.leaveTime ?? "—";
                    const predicted = formatMinutesLabel(avg?.avgLeaveMinutes ?? null);
                    return `
                      <div class="mini">
                        <span class="muted">${APP_BY_ID[app].name}</span>
                        <b>${actual}</b>
                        <span class="muted">μ.ο. ${predicted}${slot?.rides ? ` · ${slot.rides} νμ.` : ""}</span>
                      </div>
                    `;
                  }).join("")}
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    `;
  }

  function renderHistory(): string {
    const items = [...state.shifts].sort((a, b) => b.date.localeCompare(a.date));
    const realCount = realShifts(state.shifts).length;

    return `
      <div class="card">
        <h2>${realCount} δικές σου μέρες</h2>
        <p class="muted">Άνοιξε μια μέρα για διόρθωση, ή βγάλε αντίγραφο για να μην χαθούν οι ώρες.</p>
        <div class="small-actions">
          <button class="ghost" data-action="export">Αντίγραφο</button>
          <button class="ghost" data-action="import">Εισαγωγή</button>
          <button class="ghost" data-action="demo">${hasDemoShifts(state.shifts) ? "Καθάρισε παράδειγμα" : "Φόρτωσε παράδειγμα"}</button>
          <button class="danger" data-action="clear-all">Σβήσε όλα</button>
        </div>
        <input class="hidden-file" type="file" accept="application/json" data-role="import-file">
      </div>
      ${
        items.length === 0
          ? `<div class="banner info">Δεν υπάρχει ακόμα ιστορικό. Γράψε τη σημερινή βάρδια και από την επόμενη μέρα θα βγαίνει μέσος όρος.</div>`
          : items
              .map((shift) => {
                const line = shift.slots
                  .filter((slot) => slot.leaveTime || slot.rides)
                  .map((slot) => `${APP_BY_ID[slot.app].name} ${slot.leaveTime ?? "—"} (${slot.rides})`)
                  .join(" · ");
                return `
                  <button class="card history-item" data-action="open-day" data-date="${shift.date}">
                    <div class="row">
                      <strong>${WEEKDAY_LABELS[weekdayOf(shift.date)]} ${formatDisplayDate(shift.date)}</strong>
                      ${shift.isDemo ? `<span class="muted">παράδειγμα</span>` : ""}
                    </div>
                    <p class="muted" style="margin:8px 0 0">${escapeHtml(line || "Κενή μέρα")}</p>
                  </button>
                `;
              })
              .join("")
      }
    `;
  }

  function render(): void {
    const body =
      state.tab === "today"
        ? renderToday()
        : state.tab === "forecast"
          ? renderForecast()
          : state.tab === "week"
            ? renderWeek()
            : renderHistory();

    root.innerHTML = `
      <header class="top">
        <div>
          <p class="eyebrow">Bolt · Uber · FreeNow</p>
          <h1>Βάρδια</h1>
        </div>
        <div class="muted">${formatDisplayDate(todayISO())}</div>
      </header>
      <main>${body}</main>
      <nav class="nav">
        ${tabs
          .map(
            (tab) => `
              <button class="${tab.id === state.tab ? "active" : ""}" data-action="tab" data-tab="${tab.id}">${tab.label}</button>
            `,
          )
          .join("")}
      </nav>
      ${state.toast ? `<div class="toast">${escapeHtml(state.toast)}</div>` : ""}
    `;
  }

  root.addEventListener("click", (event) => {
    const target = (event.target as HTMLElement).closest<HTMLElement>("[data-action]");
    if (!target) return;
    const action = target.dataset.action;

    if (action === "tab" && target.dataset.tab) {
      state.tab = target.dataset.tab as TabId;
      render();
      return;
    }
    if (action === "stuck" && target.dataset.app) {
      const slot = shiftFor(state.selectedDate).slots.find((item) => item.app === target.dataset.app);
      patchSlot(state.selectedDate, target.dataset.app as AppId, { stuck: !slot?.stuck });
      return;
    }
    if (action === "rides" && target.dataset.app) {
      const slot = shiftFor(state.selectedDate).slots.find((item) => item.app === target.dataset.app);
      const next = Math.max(0, (slot?.rides ?? 0) + Number(target.dataset.delta));
      patchSlot(state.selectedDate, target.dataset.app as AppId, { rides: next });
      return;
    }
    if (action === "forecast-day") {
      state.forecastWeekday = Number(target.dataset.day);
      render();
      return;
    }
    if (action === "week-nav") {
      state.weekStart = addDays(state.weekStart, Number(target.dataset.delta));
      render();
      return;
    }
    if (action === "open-day" && target.dataset.date) {
      state.selectedDate = target.dataset.date;
      state.tab = "today";
      render();
      return;
    }
    if (action === "demo") {
      if (hasDemoShifts(state.shifts)) {
        persist(realShifts(state.shifts));
        toast("Καθάρισα το παράδειγμα.");
      } else {
        persist([...state.shifts, ...createDemoShifts()]);
        toast("Φόρτωσα 3 εβδομάδες παράδειγμα.");
      }
      return;
    }
    if (action === "export") {
      const blob = new Blob([exportPayload(state.shifts)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "vardia-backup.json";
      link.click();
      URL.revokeObjectURL(url);
      toast("Το αντίγραφο κατέβηκε.");
      return;
    }
    if (action === "import") {
      root.querySelector<HTMLInputElement>("[data-role=import-file]")?.click();
      return;
    }
    if (action === "clear-all" && window.confirm("Να σβηστούν όλες οι βάρδιες από αυτή τη συσκευή;")) {
      persist([]);
      toast("Καθάρισα το ιστορικό.");
    }
  });

  root.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    const action = target.dataset.action;
    if (action === "date") {
      state.selectedDate = target.value || todayISO();
      render();
      return;
    }
    if ((action === "start" || action === "leave" || action === "notes") && target.dataset.app) {
      const key = action === "start" ? "startTime" : action === "leave" ? "leaveTime" : "notes";
      const value = target.value.trim() || null;
      patchSlot(state.selectedDate, target.dataset.app as AppId, {
        [key]: key === "notes" ? target.value : value,
      });
      return;
    }
    if (action === "check-app") {
      state.checkApp = target.value as AppId;
      render();
      return;
    }
    if (action === "check-time") {
      state.checkTime = target.value || currentClock();
      render();
    }
  });

  root.addEventListener("change", (event) => {
    const input = event.target as HTMLInputElement;
    if (input.dataset.role !== "import-file" || !input.files?.[0]) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        persist(importPayload(String(reader.result)));
        toast("Η εισαγωγή έγινε.");
      } catch (error) {
        toast(error instanceof Error ? error.message : "Αποτυχία εισαγωγής.");
      }
    };
    reader.readAsText(input.files[0]);
  });

  if (!state.shifts.length) {
    persist(createDemoShifts());
    toast("Έβαλα παράδειγμα 3 εβδομάδων για να δεις τους μέσους όρους.");
    return;
  }

  render();
}
