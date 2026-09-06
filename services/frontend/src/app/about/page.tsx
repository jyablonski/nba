"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { formatScrapedAt } from "@/lib/format";

export default function AboutPage() {
  const statusQuery = useQuery({
    queryKey: ["status"],
    queryFn: () => api.getStatus(),
  });
  const scraped = formatScrapedAt(statusQuery.data?.last_scraped_at);

  return (
    <article className="space-y-8">
      <header>
        <h1 className="type-about">Baseline</h1>
      </header>

      <p className="type-prose">
        A personal analytics desk for NBA box scores and remaining-contract snapshots. Humans browse
        the same facts they can also ask about: a bounded set of questions, not a general chatbot.
      </p>

      <Section title="Sources">
        <p>
          Data comes from the feeds below. Some feeds only appear in Ask until a dedicated screen
          exists.
        </p>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>
            <span className="font-medium text-foreground">NBA Stats</span>: teams, players, the
            season slate, box scores, standings, and play-by-play for completed games.
          </li>
          <li>
            <span className="font-medium text-foreground">Basketball-Reference</span>:
            remaining-year player salaries and team payroll, plus the current injury report.
            Snapshots, not a paid ledger or injury history.
          </li>
          <li>
            <span className="font-medium text-foreground">The Odds API</span>: upcoming NBA
            moneylines and spreads when a key is configured. A market snapshot, not a book.
          </li>
          <li>
            <span className="font-medium text-foreground">Reddit</span>: r/nba posts (not comments)
            when Reddit access is configured. No Baseline Social page yet.
          </li>
        </ul>
      </Section>

      <Section title="How the data gets here">
        <p>
          Those sources are collected and served here. This browser talks to that served data only.
        </p>
      </Section>

      <Section title="Coverage">
        <p>
          Coverage defaults to the latest season. Counts in the header and home strip come from
          what&apos;s actually here, not invented scale. Contracts are a remaining-year snapshot and
          are not refreshed every day.
        </p>
      </Section>

      <section>
        <h2 className="type-module border-b border-rule pb-1">Last scraped</h2>
        <p className="type-timestamp mt-3">Scraped {scraped}</p>
        <p className="type-prose mt-3">
          Same timestamp as the header, not a live feed. Health checks are not displayed.
        </p>
      </section>
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="type-module border-b border-rule pb-1">{title}</h2>
      <div className="type-prose mt-3">{children}</div>
    </section>
  );
}
