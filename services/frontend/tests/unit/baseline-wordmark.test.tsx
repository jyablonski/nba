import { readFileSync } from "node:fs";
import path from "node:path";

import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  BASELINE_INK,
  BASELINE_LINE_GREEN,
  BASELINE_PAPER,
  FAVICON_RULE_D,
  FAVICON_VIEWBOX,
  WORDMARK_ARC_D,
  WORDMARK_BAR_D,
  WORDMARK_SRC,
  WORDMARK_VIEWBOX,
} from "@/components/brand/baseline-mark";
import { BaselineWordmark } from "@/components/brand/baseline-wordmark";

describe("BaselineWordmark", () => {
  it("renders the official lockup as a single image", () => {
    render(<BaselineWordmark />);
    const img = document.querySelector(`img[src="${WORDMARK_SRC}"]`);
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("alt", "");
    expect(img).toHaveAttribute("width", "198");
    expect(img).toHaveAttribute("height", "59");

    const lockup = readFileSync(
      path.resolve(__dirname, "../../public/logo/baseline-lockup.svg"),
      "utf8"
    );
    expect(lockup).toContain(`viewBox="${WORDMARK_VIEWBOX}"`);
    expect(lockup).toContain(`stroke="${BASELINE_LINE_GREEN}"`);
    expect(lockup).toContain(WORDMARK_BAR_D);
    expect(lockup).toContain(WORDMARK_ARC_D);
    expect(lockup).toContain(BASELINE_INK);
    expect(lockup).toContain('font-family="IBM Plex Sans, Helvetica, Arial, sans-serif"');
  });
});

describe("favicon mark", () => {
  it("uses the official B-on-the-line mark and flips the B in dark color-scheme", () => {
    const iconSvg = readFileSync(path.resolve(__dirname, "../../src/app/icon.svg"), "utf8");
    expect(iconSvg).toContain(`viewBox="${FAVICON_VIEWBOX}"`);
    expect(iconSvg).toContain("@media (prefers-color-scheme: dark)");
    expect(iconSvg).toContain(BASELINE_INK);
    expect(iconSvg).toContain(BASELINE_PAPER);
    expect(iconSvg).toContain(BASELINE_LINE_GREEN);
    expect(iconSvg).toContain(FAVICON_RULE_D);
    expect(iconSvg).not.toContain("<text");
    expect(iconSvg).not.toContain("a17 17");
  });
});
