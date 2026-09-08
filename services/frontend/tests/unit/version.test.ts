import { describe, expect, it } from "vitest";

import { commitUrl, shortSha } from "@/lib/version";

describe("version", () => {
  it("shortens a real sha and links it to the commit", () => {
    expect(shortSha("0123456789abcdef")).toBe("0123456");
    expect(commitUrl("0123456789abcdef")).toBe(
      "https://github.com/jyablonski/baseline/commit/0123456789abcdef"
    );
  });

  it("leaves the unbaked dev marker alone and does not link it", () => {
    expect(shortSha("dev")).toBe("dev");
    expect(commitUrl("dev")).toBeNull();
  });
});
