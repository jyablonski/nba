export const PRIMARY_NAV = [
  { href: "/", label: "Home" },
  { href: "/schedule", label: "Schedule" },
  { href: "/players", label: "Players" },
  { href: "/teams", label: "Teams" },
  { href: "/ask", label: "Ask" },
  { href: "/social", label: "Social" },
  { href: "/about", label: "About" },
] as const;

export function isNavActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  if (href === "/players") return pathname === "/players" || pathname.startsWith("/players/");
  if (href === "/teams") return pathname === "/teams" || pathname.startsWith("/teams/");
  if (href === "/games") return pathname === "/games" || pathname.startsWith("/games/");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function withSeason(href: string, season: string) {
  if (!season) return href;
  const [path, existing] = href.split("?");
  const params = new URLSearchParams(existing);
  params.set("season", season);
  return `${path}?${params.toString()}`;
}
