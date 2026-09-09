const REPO_URL = "https://github.com/jyablonski/baseline";

// Baked by `next build` from the NEXT_PUBLIC_GIT_SHA build arg (see Dockerfile).
// Local dev and unbaked builds report "dev".
export const GIT_SHA = process.env.NEXT_PUBLIC_GIT_SHA || "dev";

export function shortSha(sha: string = GIT_SHA): string {
  return sha === "dev" ? "dev" : sha.slice(0, 7);
}

export function commitUrl(sha: string = GIT_SHA): string | null {
  return sha === "dev" ? null : `${REPO_URL}/commit/${sha}`;
}
