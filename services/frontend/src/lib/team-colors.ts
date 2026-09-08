export const FALLBACK_HOME = "#2D5A27";
export const FALLBACK_AWAY = "#8C4A2F";
export const TIED_COLOR = "#A39C8C";
export const CHART_BACKGROUND = "#FBFAF5";
export const NEAR_BLACK = "#000000";
export const COLOR_DISTANCE_THRESHOLD = 70;
export const CHART_LIGHT_DISTANCE = 70;
export const CHART_DARK_DISTANCE = 50;
export const LUMINANCE_TOO_LIGHT = 0.82;
export const LUMINANCE_TOO_DARK = 0.01;

export type PlotColors = {
  home: string;
  away: string;
  tied: string;
};

export type LeaderSide = "home" | "away" | "tied";

export function normalizeHex(value: string | null | undefined): string | null {
  if (!value) return null;
  const match = value.trim().match(/^#?([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!match) return null;
  let hex = match[1];
  if (hex.length === 3) {
    hex = hex
      .split("")
      .map((part) => part + part)
      .join("");
  }
  return `#${hex.toUpperCase()}`;
}

export function hexToRgb(hex: string): [number, number, number] | null {
  const normalized = normalizeHex(hex);
  if (!normalized) return null;
  return [
    parseInt(normalized.slice(1, 3), 16),
    parseInt(normalized.slice(3, 5), 16),
    parseInt(normalized.slice(5, 7), 16),
  ];
}

export function colorDistance(left: string, right: string): number {
  const a = hexToRgb(left);
  const b = hexToRgb(right);
  if (!a || !b) return Number.POSITIVE_INFINITY;
  const dr = a[0] - b[0];
  const dg = a[1] - b[1];
  const db = a[2] - b[2];
  return Math.sqrt(dr * dr + dg * dg + db * db);
}

export function colorsCollide(
  left: string,
  right: string,
  threshold = COLOR_DISTANCE_THRESHOLD
): boolean {
  return colorDistance(left, right) < threshold;
}

export function relativeLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0;
  const [r, g, b] = rgb.map((channel) => {
    const scaled = channel / 255;
    return scaled <= 0.03928 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function rgbToHex(rgb: [number, number, number]): string {
  return `#${rgb
    .map((channel) => Math.max(0, Math.min(255, channel)).toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase()}`;
}

function darkenHex(hex: string, amount: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  return rgbToHex(
    rgb.map((channel) => Math.round(channel * (1 - amount))) as [number, number, number]
  );
}

function lightenHex(hex: string, amount: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  return rgbToHex(
    rgb.map((channel) => Math.round(channel + (255 - channel) * amount)) as [number, number, number]
  );
}

export function isTooLightOnChart(hex: string): boolean {
  return (
    colorsCollide(hex, CHART_BACKGROUND, CHART_LIGHT_DISTANCE) ||
    relativeLuminance(hex) > LUMINANCE_TOO_LIGHT
  );
}

export function isTooDarkOnChart(hex: string): boolean {
  return (
    colorsCollide(hex, NEAR_BLACK, CHART_DARK_DISTANCE) ||
    relativeLuminance(hex) < LUMINANCE_TOO_DARK
  );
}

export function isUnreadableOnChart(hex: string): boolean {
  return isTooLightOnChart(hex) || isTooDarkOnChart(hex);
}

export function ensureReadableOnChart(hex: string): string {
  if (isTooLightOnChart(hex)) {
    return darkenHex(hex, 0.45);
  }
  if (isTooDarkOnChart(hex)) {
    return lightenHex(hex, 0.45);
  }
  return hex;
}

function preferReadable(primary: string, alternate: string | null): string {
  if (!isUnreadableOnChart(primary) || !alternate) return primary;
  return alternate;
}

function shiftAwayFrom(color: string, other: string): string {
  const lum = relativeLuminance(color);
  const shifted = lum > 0.4 ? darkenHex(color, 0.5) : lightenHex(color, 0.45);
  if (!colorsCollide(shifted, other) && !isUnreadableOnChart(shifted)) {
    return shifted;
  }
  return lum > 0.5 ? "#1A1A1A" : FALLBACK_AWAY;
}

export function resolvePlotColors(input: {
  homePrimary?: string | null;
  homeAlternate?: string | null;
  awayPrimary?: string | null;
  awayAlternate?: string | null;
}): PlotColors {
  const homePrimary = normalizeHex(input.homePrimary) ?? FALLBACK_HOME;
  const homeAlternate = normalizeHex(input.homeAlternate);
  const awayPrimary = normalizeHex(input.awayPrimary) ?? FALLBACK_AWAY;
  const awayAlternate = normalizeHex(input.awayAlternate);

  let home = ensureReadableOnChart(preferReadable(homePrimary, homeAlternate));
  let away = ensureReadableOnChart(preferReadable(awayPrimary, awayAlternate));

  if (colorsCollide(home, away)) {
    const awayAlt = awayAlternate ? ensureReadableOnChart(awayAlternate) : null;
    const homeAlt = homeAlternate ? ensureReadableOnChart(homeAlternate) : null;
    if (awayAlt && !colorsCollide(home, awayAlt)) {
      away = awayAlt;
    } else if (homeAlt && !colorsCollide(homeAlt, away)) {
      home = homeAlt;
    } else if (homeAlt && awayAlt && !colorsCollide(homeAlt, awayAlt)) {
      home = homeAlt;
      away = awayAlt;
    } else {
      away = ensureReadableOnChart(shiftAwayFrom(away, home));
    }
  }

  return {
    home,
    away,
    tied: TIED_COLOR,
  };
}

export function leaderFromDifferential(differential: number): LeaderSide {
  if (differential > 0) return "home";
  if (differential < 0) return "away";
  return "tied";
}

export function colorForLeader(leader: LeaderSide, colors: PlotColors): string {
  return colors[leader];
}

export function colorForScoringSide(
  scoringSide: string | null | undefined,
  colors: PlotColors
): string {
  if (scoringSide === "home") return colors.home;
  if (scoringSide === "away") return colors.away;
  return colors.tied;
}

export function leadSegments<T extends { score_differential: number }>(
  points: T[],
  colors: PlotColors
): { color: string; points: T[] }[] {
  if (points.length === 0) return [];
  const leaders = points.map((point) => leaderFromDifferential(point.score_differential));
  const segments: { color: string; points: T[] }[] = [];
  let start = 0;
  for (let index = 1; index <= points.length; index += 1) {
    if (index < points.length && leaders[index] === leaders[start]) continue;
    const slice = points.slice(start, index);
    const connected = index < points.length ? [...slice, points[index]] : slice;
    segments.push({
      color: colorForLeader(leaders[start], colors),
      points: connected,
    });
    start = index;
  }
  return segments;
}
