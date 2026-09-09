import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user?: {
      /** GitHub login, carried through so the allowlist can be re-checked. */
      login?: string;
    } & DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    login?: string;
  }
}
