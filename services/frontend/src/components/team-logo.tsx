import Link from "next/link";

import { nbaTeamLogoUrl } from "@/lib/team-logo";
import { cn } from "@/lib/utils";

export function TeamLogo({
  teamId,
  size = 18,
  className,
}: {
  teamId: number | null | undefined;
  size?: number;
  className?: string;
}) {
  if (teamId == null || !Number.isFinite(teamId)) return null;
  return (
    // next/image would need images.remotePatterns for cdn.nba.com plus
    // dangerouslyAllowSVG, which proxies arbitrary remote SVG through our own
    // origin. Not worth an XSS vector to optimize an 18px icon.
    // eslint-disable-next-line @next/next/no-img-element -- remote SVG team logo
    <img
      src={nbaTeamLogoUrl(teamId)}
      alt=""
      width={size}
      height={size}
      className={cn("inline-block shrink-0 object-contain", className)}
      loading="lazy"
    />
  );
}

export function TeamAbbrLink({
  teamId,
  abbreviation,
  href,
  className,
}: {
  teamId: number;
  abbreviation: string;
  href: string;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn("inline-flex items-center gap-1.5 font-semibold hover:text-primary", className)}
    >
      <TeamLogo teamId={teamId} />
      {abbreviation}
    </Link>
  );
}
