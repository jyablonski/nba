import Link from "next/link";

import { teamLogoLabel } from "@/lib/team-logo";
import { cn } from "@/lib/utils";

export function TeamLogo({
  teamId,
  abbreviation,
  size = 18,
  className,
}: {
  teamId: string | null | undefined;
  abbreviation?: string | null;
  size?: number;
  className?: string;
}) {
  if (!teamId) return null;
  return (
    <span
      aria-hidden="true"
      style={{ width: size, height: size }}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-muted text-[8px] font-bold text-muted-foreground",
        className
      )}
    >
      {teamLogoLabel(abbreviation)}
    </span>
  );
}

export function TeamAbbrLink({
  teamId,
  abbreviation,
  href,
  className,
}: {
  teamId: string;
  abbreviation: string;
  href: string;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={cn("inline-flex items-center gap-1.5 font-semibold hover:text-primary", className)}
    >
      <TeamLogo teamId={teamId} abbreviation={abbreviation} />
      {abbreviation}
    </Link>
  );
}
