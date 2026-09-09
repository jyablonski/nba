import { auth } from "@/auth";

/**
 * Gate every /admin route on an allowlisted GitHub session.
 *
 * The matcher is a security boundary, so the sign-in exemption is anchored:
 * a loose `(?!signin)` would also leave a future /admin/signin-anything
 * ungated. /admin/signin itself must stay open or unauthenticated users hit a
 * redirect loop. The page re-checks the session too — this regex is not the
 * only thing standing between a stranger and the data.
 */
export default auth;

export const config = {
  matcher: ["/admin", "/admin/((?!signin$|signin/).*)"],
};
