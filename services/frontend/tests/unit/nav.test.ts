import { describe, expect, it } from "vitest";

import { isNavActive, PRIMARY_NAV, withSeason } from "@/lib/nav";

describe("nav", () => {
  it("lists primary tabs including Ask", () => {
    expect(PRIMARY_NAV.map((item) => item.label)).toEqual([
      "Home",
      "Schedule",
      "Players",
      "Teams",
      "Compare",
      "Ask",
      "About",
    ]);
  });

  it("marks player profiles under Players, not Compare", () => {
    expect(isNavActive("/players/202695", "/players")).toBe(true);
    expect(isNavActive("/players/compare", "/players")).toBe(false);
    expect(isNavActive("/players/compare", "/players/compare")).toBe(true);
    expect(isNavActive("/", "/")).toBe(true);
    expect(isNavActive("/ask", "/ask")).toBe(true);
    expect(isNavActive("/teams/1", "/teams")).toBe(true);
    expect(isNavActive("/games/0022400001", "/games")).toBe(true);
    expect(isNavActive("/games", "/games")).toBe(true);
    expect(isNavActive("/schedule", "/schedule")).toBe(true);
    expect(isNavActive("/schedule", "/games")).toBe(false);
  });

  it("appends season to links", () => {
    expect(withSeason("/players", "2025-26")).toBe("/players?season=2025-26");
    expect(withSeason("/players?search=kawhi", "2025-26")).toBe(
      "/players?search=kawhi&season=2025-26"
    );
    expect(withSeason("/ask", "")).toBe("/ask");
  });
});
