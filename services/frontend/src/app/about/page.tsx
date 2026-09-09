import { commitUrl, shortSha } from "@/lib/version";

export default function AboutPage() {
  const sha = shortSha();
  const href = commitUrl();

  return (
    <article className="space-y-8">
      <header>
        <h1 className="type-about">About</h1>
      </header>

      <p className="type-prose">
        An NBA analytics app covering box scores, player and team stats, contract snapshots, betting
        odds, and ML-powered win predictions, updated daily throughout the season.
      </p>

      <Section title="Sources">
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>
            <span className="font-medium text-foreground">Basketball-Reference</span>: teams,
            players, the season slate, box scores, standings, play-by-play, remaining-year player
            salaries, team payroll, and the current injury report. Snapshots, not a paid ledger or
            injury history.
          </li>
          <li>
            <span className="font-medium text-foreground">The Odds API</span>: upcoming NBA
            moneylines and spreads when a key is configured. A market snapshot, not a book.
          </li>
          <li>
            <span className="font-medium text-foreground">Reddit</span>: r/nba posts and their top
            comments when Reddit access is configured. No Baseline Social page yet.
          </li>
        </ul>
      </Section>

      <Section title="How the data gets here">
        <p>
          The sources are scraped everyday on a schedule, transformed and enriched into analytics
          tables, and then served out over this app.
        </p>
      </Section>

      <Section title="Coverage">
        <p>Coverage defaults to the latest season only.</p>
      </Section>

      <Section title="Developer">
        <div className="flex items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo/profile.png"
            alt="Jacob Yablonski"
            width={72}
            height={72}
            className="h-18 w-18 rounded-full border border-rule object-cover"
          />
          <div>
            <p className="font-medium text-foreground">Jacob Yablonski</p>
            <p className="mt-1 flex gap-3">
              <a
                className="underline underline-offset-2"
                href="https://github.com/jyablonski"
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
              <a
                className="underline underline-offset-2"
                href="https://www.linkedin.com/in/jacobyablonski/"
                target="_blank"
                rel="noreferrer"
              >
                LinkedIn
              </a>
            </p>
          </div>
        </div>
      </Section>

      <Section title="Version">
        {href ? (
          <a className="underline underline-offset-2" href={href} target="_blank" rel="noreferrer">
            {sha}
          </a>
        ) : (
          <p>{sha}</p>
        )}
      </Section>
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
