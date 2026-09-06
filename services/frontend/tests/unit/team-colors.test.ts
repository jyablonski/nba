import { describe, expect, it } from "vitest";

import {
  FALLBACK_AWAY,
  FALLBACK_HOME,
  colorsCollide,
  ensureReadableOnChart,
  isTooDarkOnChart,
  leadSegments,
  normalizeHex,
  resolvePlotColors,
} from "@/lib/team-colors";

describe("normalizeHex", () => {
  it("accepts #RGB and #RRGGBB", () => {
    expect(normalizeHex("#abc")).toBe("#AABBCC");
    expect(normalizeHex("1d428a")).toBe("#1D428A");
    expect(normalizeHex("nope")).toBeNull();
  });
});

describe("ensureReadableOnChart", () => {
  it("treats near-black as unreadable on beige and lifts it", () => {
    expect(isTooDarkOnChart("#000000")).toBe(true);
    expect(isTooDarkOnChart("#1A1A1A")).toBe(true);
    expect(ensureReadableOnChart("#000000")).not.toBe("#000000");
    expect(isTooDarkOnChart(ensureReadableOnChart("#000000"))).toBe(false);
  });

  it("leaves dark navy primaries alone so they stay brand-colored", () => {
    expect(isTooDarkOnChart("#002D62")).toBe(false);
    expect(isTooDarkOnChart("#0C2340")).toBe(false);
    expect(ensureReadableOnChart("#002D62")).toBe("#002D62");
  });

  it("keeps Spurs silver readable without darkening it into charcoal", () => {
    expect(ensureReadableOnChart("#C4CED4")).toBe("#C4CED4");
  });
});

describe("resolvePlotColors", () => {
  it("keeps distinct readable primaries", () => {
    const colors = resolvePlotColors({
      homePrimary: "#CE1141",
      homeAlternate: "#000000",
      awayPrimary: "#006BB6",
      awayAlternate: "#F58426",
    });
    expect(colors.home).toBe("#CE1141");
    expect(colors.away).toBe("#006BB6");
  });

  it("uses the home alternate when the primary is near-black on beige", () => {
    const colors = resolvePlotColors({
      homePrimary: "#000000",
      homeAlternate: "#C4CED4",
      awayPrimary: "#006BB6",
      awayAlternate: "#F58426",
    });
    expect(colors.home).toBe(ensureReadableOnChart("#C4CED4"));
    expect(colors.home).not.toBe("#000000");
    expect(colors.away).toBe("#006BB6");
  });

  it("uses the away alternate when the primary is near-black on beige", () => {
    const colors = resolvePlotColors({
      homePrimary: "#006BB6",
      homeAlternate: "#F58426",
      awayPrimary: "#000000",
      awayAlternate: "#C4CED4",
    });
    expect(colors.home).toBe("#006BB6");
    expect(colors.away).toBe(ensureReadableOnChart("#C4CED4"));
    expect(colors.away).not.toBe("#000000");
  });

  it("lightens a near-black primary when no alternate is available", () => {
    const colors = resolvePlotColors({
      homePrimary: "#000000",
      awayPrimary: "#006BB6",
    });
    expect(colors.home).toBe(ensureReadableOnChart("#000000"));
    expect(colors.home).not.toBe("#000000");
    expect(colors.away).toBe("#006BB6");
  });

  it("moves the away team to its alternate when primaries collide", () => {
    const colors = resolvePlotColors({
      homePrimary: "#CE1141",
      homeAlternate: "#000000",
      awayPrimary: "#CE1141",
      awayAlternate: "#C4CED4",
    });
    expect(colors.home).toBe("#CE1141");
    expect(colors.away).toBe(ensureReadableOnChart("#C4CED4"));
    expect(colors.away).not.toBe("#CE1141");
    expect(colorsCollide(colors.home, colors.away)).toBe(false);
  });

  it("uses the home alternate when the away alternate still collides", () => {
    const colors = resolvePlotColors({
      homePrimary: "#000000",
      homeAlternate: "#C4CED4",
      awayPrimary: "#000000",
      awayAlternate: "#000000",
    });
    expect(colors.home).toBe(ensureReadableOnChart("#C4CED4"));
    expect(colors.away).toBe(ensureReadableOnChart("#000000"));
    expect(colors.away).not.toBe("#000000");
    expect(colorsCollide(colors.home, colors.away)).toBe(false);
  });

  it("darkens a near-white alternate so it reads on the beige chart", () => {
    const colors = resolvePlotColors({
      homePrimary: "#000000",
      awayPrimary: "#000000",
      awayAlternate: "#FFFFFF",
    });
    expect(colors.away).not.toBe("#FFFFFF");
    expect(colors.home).not.toBe("#000000");
    expect(colorsCollide(colors.home, colors.away)).toBe(false);
  });

  it("falls back when colors are missing", () => {
    const colors = resolvePlotColors({});
    expect(colors.home).toBe(FALLBACK_HOME);
    expect(colors.away).toBe(FALLBACK_AWAY);
  });
});

describe("leadSegments", () => {
  it("colors NYK @ SAS home-lead segments with silver, not brand black", () => {
    const colors = resolvePlotColors({
      homePrimary: "#000000",
      homeAlternate: "#C4CED4",
      awayPrimary: "#006BB6",
      awayAlternate: "#F58426",
    });
    const segments = leadSegments(
      [{ score_differential: 4 }, { score_differential: 8 }, { score_differential: -2 }],
      colors
    );
    expect(colors.home).toBe("#C4CED4");
    expect(colors.away).toBe("#006BB6");
    expect(segments[0].color).toBe("#C4CED4");
    expect(segments[1].color).toBe("#006BB6");
  });

  it("splits the series at lead changes and connects the boundary point", () => {
    const segments = leadSegments(
      [
        { score_differential: 2 },
        { score_differential: 4 },
        { score_differential: -1 },
        { score_differential: -3 },
      ],
      { home: "#111111", away: "#222222", tied: "#333333" }
    );
    expect(segments).toHaveLength(2);
    expect(segments[0].color).toBe("#111111");
    expect(segments[0].points).toHaveLength(3);
    expect(segments[1].color).toBe("#222222");
    expect(segments[1].points.map((point) => point.score_differential)).toEqual([-1, -3]);
  });
});
