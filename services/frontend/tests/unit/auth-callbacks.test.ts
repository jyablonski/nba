import { beforeAll, describe, expect, it, vi } from "vitest";

/**
 * `isAllowedLogin` is covered directly in admin-access.test.ts. What is tested
 * here is the wiring around it: that auth.ts actually calls it in both places,
 * and that the session carries the login the allowlist is checked against. A
 * callback quietly returning true would hand the console to any GitHub user
 * while every allowlist test stayed green.
 */
const captured = vi.hoisted(() => ({ config: null as Record<string, never> | null }));

vi.mock("next-auth", () => ({
  default: (config: Record<string, never>) => {
    captured.config = config;
    return { handlers: {}, auth: () => {}, signIn: () => {}, signOut: () => {} };
  },
}));

vi.mock("next-auth/providers/github", () => ({ default: () => ({ id: "github" }) }));

type Callbacks = {
  signIn: (args: { profile?: { login?: string } }) => boolean;
  jwt: (args: { token: Record<string, unknown>; profile?: { login?: string } }) => {
    login?: string;
  };
  session: (args: { session: { user?: { login?: string } }; token: Record<string, unknown> }) => {
    user?: { login?: string };
  };
  authorized: (args: { auth: { user?: { login?: string } } | null }) => boolean;
};

let callbacks: Callbacks;

beforeAll(async () => {
  vi.stubEnv("ADMIN_GITHUB_LOGINS", "allowed-user");
  await import("@/auth");
  callbacks = (captured.config as unknown as { callbacks: Callbacks }).callbacks;
});

describe("auth callbacks", () => {
  it("routes sign-in and errors to the admin sign-in page", () => {
    const pages = (captured.config as unknown as { pages: Record<string, string> }).pages;
    // Both must stay under /admin or a rejected user lands on NextAuth's default page.
    expect(pages.signIn).toBe("/admin/signin");
    expect(pages.error).toBe("/admin/signin");
  });

  it("admits an allowlisted GitHub login and rejects everyone else", () => {
    expect(callbacks.signIn({ profile: { login: "allowed-user" } })).toBe(true);
    expect(callbacks.signIn({ profile: { login: "ALLOWED-USER" } })).toBe(true);
    expect(callbacks.signIn({ profile: { login: "stranger" } })).toBe(false);
    expect(callbacks.signIn({ profile: {} })).toBe(false);
    // No profile at all must not throw its way into a granted session.
    expect(callbacks.signIn({})).toBe(false);
  });

  it("carries the GitHub login from profile to token to session", () => {
    const token = callbacks.jwt({ token: {}, profile: { login: "allowed-user" } });
    expect(token.login).toBe("allowed-user");
    const session = callbacks.session({ session: { user: {} }, token });
    expect(session.user?.login).toBe("allowed-user");
  });

  it("leaves the token untouched when GitHub returns no login", () => {
    expect(callbacks.jwt({ token: { login: "existing" }, profile: {} })).toMatchObject({
      login: "existing",
    });
    // A session with no user (signed out) must not be dereferenced.
    expect(callbacks.session({ session: {}, token: {} })).toEqual({});
  });

  it("re-checks the allowlist on every request rather than trusting the session", () => {
    // This is what makes revoking access a config change instead of a wait for
    // an existing session to expire.
    expect(callbacks.authorized({ auth: { user: { login: "allowed-user" } } })).toBe(true);
    expect(callbacks.authorized({ auth: { user: { login: "stranger" } } })).toBe(false);
    expect(callbacks.authorized({ auth: null })).toBe(false);
  });
});
