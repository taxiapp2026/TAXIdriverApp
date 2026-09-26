/** @vitest-environment jsdom */

import { describe, expect, it } from "vitest";
import { createApp } from "./app";

describe("app shell", () => {
  it("renders the shift tracker and forecast from demo data", () => {
    window.localStorage.clear();
    const root = document.createElement("div");
    document.body.append(root);
    createApp(root);
    expect(root.textContent).toContain("Βάρδια");
    expect(root.textContent).toContain("Bolt");
    const forecast = root.querySelector<HTMLButtonElement>("[data-tab=forecast]");
    forecast?.click();
    expect(root.textContent).toContain("Παίρνω νούμερο τώρα");
    expect(root.textContent).toContain("Τελευταίο νούμερο");
  });
});
