import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

import { isAllowedLogin } from "@/lib/admin-access";

/**
 * GitHub OAuth for /admin, restricted to an explicit allowlist.
 *
 * Fails closed: with ADMIN_GITHUB_LOGINS unset the allowlist is empty and the
 * signIn callback rejects every account, including the app owner's. An admin
 * console that silently accepts any GitHub user because a variable is missing
 * is worse than one nobody can reach.
 */
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [GitHub],
  pages: {
    signIn: "/admin/signin",
    error: "/admin/signin",
  },
  callbacks: {
    // Runs before a session is ever issued, so a rejected account never gets
    // a cookie rather than getting one and being filtered later.
    signIn({ profile }) {
      return isAllowedLogin(profile?.login as string | undefined);
    },
    jwt({ token, profile }) {
      if (profile?.login) token.login = profile.login as string;
      return token;
    },
    session({ session, token }) {
      if (session.user) session.user.login = token.login as string | undefined;
      return session;
    },
    // Re-checked on every request by middleware: revoking access is a config
    // change, not a wait for an existing session to expire.
    authorized({ auth: session }) {
      return isAllowedLogin(session?.user?.login);
    },
  },
});
