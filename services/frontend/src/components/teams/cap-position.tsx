import {
  CAP_BAND_CLASS,
  capBarBands,
  capDistances,
  capPercent,
  capPositionSummary,
  capRestrictions,
  capScale,
  capTier,
  capTierLabel,
  formatCapDistance,
  layoutCapBarMarkers,
  resolveCapFlags,
} from "@/lib/cba";
import { formatUsdMillions } from "@/lib/format";
import { cn } from "@/lib/utils";

export type CapPositionTeam = {
  current_season_payroll?: number | null;
  current_remaining_guaranteed?: number | null;
  current_contract_season?: string | null;
  salary_cap?: number | null;
  luxury_tax?: number | null;
  first_apron?: number | null;
  second_apron?: number | null;
  over_luxury_tax?: boolean | null;
  over_first_apron?: boolean | null;
  over_second_apron?: boolean | null;
};

export function CapPosition({ team }: { team: CapPositionTeam }) {
  const payroll = team.current_season_payroll ?? null;
  const remaining = team.current_remaining_guaranteed ?? null;
  const lines = {
    luxury_tax: team.luxury_tax,
    first_apron: team.first_apron,
    second_apron: team.second_apron,
  };
  const flags = resolveCapFlags(team, payroll, lines);
  const tier = capTier(flags);
  const scale = capScale([
    payroll,
    team.salary_cap,
    team.luxury_tax,
    team.first_apron,
    team.second_apron,
  ]);
  const bands = scale ? capBarBands(scale, lines) : [];
  const markers = scale
    ? layoutCapBarMarkers(
        [
          { id: "tax", label: "Tax", value: team.luxury_tax },
          { id: "first", label: "1st apron", value: team.first_apron },
          { id: "second", label: "2nd apron", value: team.second_apron },
        ],
        scale
      )
    : [];
  const markerLanes = markers.some((marker) => marker.lane === 1);
  const pinPct = scale && payroll != null ? capPercent(payroll, scale.min, scale.max) : null;
  const distances = capDistances(payroll, lines);
  const summary = capPositionSummary(payroll, lines);
  const restrictions = tier ? capRestrictions(tier) : [];
  const hasMoney = payroll != null || remaining != null || team.luxury_tax != null;

  return (
    <section className="border-y border-border py-6">
      <div className="flex flex-wrap items-center gap-3">
        <p className="type-eyebrow">
          Cap position
          {team.current_contract_season ? ` · ${team.current_contract_season}` : ""}
        </p>
        {tier ? (
          <span
            className={cn(
              "px-2 py-0.5 text-[11px] font-medium tracking-wide uppercase",
              tier >= 3 && "bg-destructive text-primary-foreground",
              tier === 2 && "bg-secondary text-foreground",
              tier === 1 && "bg-primary text-primary-foreground"
            )}
          >
            {capTierLabel(tier)}
          </span>
        ) : null}
      </div>

      {!hasMoney ? (
        <p className="mt-3 text-sm text-ink-2">No BRef payroll snapshot for this team yet.</p>
      ) : (
        <>
          <div className="mt-4 grid gap-8 lg:grid-cols-[1.4fr_0.6fr]">
            <div>
              <dl className="flex flex-wrap gap-8">
                <div>
                  <dt className="text-xs text-muted-foreground">Team total</dt>
                  <dd className="type-hero-stat tabular">{formatUsdMillions(payroll)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Remaining gtd.</dt>
                  <dd className="type-hero-stat tabular">{formatUsdMillions(remaining)}</dd>
                </div>
              </dl>

              {scale && bands.length > 0 ? (
                <div className={cn("relative mt-6 pt-6", markerLanes ? "pb-16" : "pb-10")}>
                  {pinPct != null && payroll != null ? (
                    <div
                      className="absolute top-0 z-10 flex flex-col items-center"
                      style={{ left: `${pinPct}%`, transform: "translateX(-50%)" }}
                    >
                      <span className="text-xs font-semibold tabular">
                        {formatUsdMillions(payroll)}
                      </span>
                      <span className="mt-0.5 h-5 w-px bg-foreground" />
                    </div>
                  ) : null}
                  <div className="relative h-3 bg-skel-1">
                    {bands.map((band, index) => (
                      <div
                        key={`${band.tone}-${index}`}
                        className={cn("absolute inset-y-0", CAP_BAND_CLASS[band.tone])}
                        style={{
                          left: `${band.start}%`,
                          width: `${band.end - band.start}%`,
                        }}
                      />
                    ))}
                    {pinPct != null ? (
                      <div
                        className="absolute inset-y-0 z-10 w-px bg-foreground"
                        style={{ left: `${pinPct}%` }}
                      />
                    ) : null}
                  </div>
                  {markers.map((marker) => (
                    <div
                      key={marker.id}
                      className="absolute top-6"
                      style={{ left: `${marker.pct}%`, transform: "translateX(-50%)" }}
                    >
                      <div className="h-3 w-px bg-foreground" />
                      <p
                        data-lane={marker.lane}
                        title={`${marker.label} ${formatUsdMillions(marker.value)}`}
                        className={cn(
                          "whitespace-nowrap text-[10px] tracking-wide text-ink-3 uppercase",
                          marker.lane === 0 ? "mt-1" : "mt-6"
                        )}
                      >
                        {marker.label} {formatUsdMillions(marker.value)}
                      </p>
                    </div>
                  ))}
                </div>
              ) : null}

              {summary ? <p className="mt-2 text-sm text-ink-2">{summary}</p> : null}
            </div>

            {distances.length > 0 ? (
              <dl className="space-y-3">
                {distances.map((row) => (
                  <div key={row.id} className="flex items-baseline justify-between gap-4">
                    <dt className="text-sm text-ink-2">
                      {row.label} · {formatUsdMillions(row.line)}
                    </dt>
                    <dd
                      className={cn(
                        "text-sm font-medium tabular",
                        row.over ? "text-destructive" : "text-primary"
                      )}
                    >
                      {formatCapDistance(row.delta)}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>

          {restrictions.length > 0 ? (
            <div className="mt-6 border-t border-border pt-4">
              <p className="type-eyebrow">What this tier restricts</p>
              <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                {restrictions.map((item) => (
                  <li key={item.id} className="flex items-start gap-2 text-sm">
                    <span
                      className={cn(
                        "mt-0.5 w-3 font-semibold",
                        item.allowed ? "text-primary" : "text-destructive"
                      )}
                      aria-hidden
                    >
                      {item.allowed ? "✓" : "×"}
                    </span>
                    <span>{item.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}

      <p className="type-caption mt-4">
        BRef remaining-year snapshot (team Totals) compared to official CBA tax/apron seeds. Not a
        tax bill. Restriction checks are the 2023 CBA apron rules for this tier; repeater status and
        exception dollar amounts are not modeled.
      </p>
    </section>
  );
}
