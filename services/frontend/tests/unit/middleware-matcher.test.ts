import { describe, expect, it, vi } from "vitest";

// middleware.ts re-exports the NextAuth handler, so importing it would boot
// NextAuth (which wants AUTH_SECRET and GitHub credentials). Only the matcher
// is under test here.
vi.mock("@/auth", () => ({ auth: () => {} }));

import { config } from "@/middleware";

/** Next compiles each matcher string to an anchored path regex. */
function gated(pathname: string): boolean {
  return config.matcher.some((pattern) => new RegExp(`^${pattern}$`).test(pathname));
}

describe("admin middleware matcher", () => {
  it("gates the console and everything nested under it", () => {
    expect(gated("/admin")).toBe(true);
    expect(gated("/admin/jobs")).toBe(true);
    expect(gated("/admin/jobs/7")).toBe(true);
  });

  it("leaves the sign-in page itself open", () => {
    // Gating this would bounce unauthenticated users into a redirect loop.
    expect(gated("/admin/signin")).toBe(false);
    expect(gated("/admin/signin/callback")).toBe(false);
  });

  it("still gates paths that merely start with signin", () => {
    // The hazard the anchored `signin$|signin/` exists to prevent: a loose
    // `(?!signin)` would leave all of these reachable without a session.
    expect(gated("/admin/signin-anything")).toBe(true);
    expect(gated("/admin/signinx")).toBe(true);
    expect(gated("/admin/signin2/secrets")).toBe(true);
  });

  it("does not gate unrelated routes", () => {
    expect(gated("/")).toBe(false);
    expect(gated("/teams")).toBe(false);
    // No prefix match on a sibling route that happens to start with "admin".
    expect(gated("/administrators")).toBe(false);
  });
});
