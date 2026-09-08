import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TeamAbbrLink, TeamLogo } from "@/components/team-logo";
import { teamLogoLabel, teamLogoUrl } from "@/lib/team-logo";

describe("teamLogoLabel", () => {
  it("uses the canonical abbreviation as a neutral local label", () => {
    expect(teamLogoLabel(" warriors ")).toBe("WAR");
    expect(teamLogoLabel(null)).toBe("NBA");
  });
});

describe("teamLogoUrl", () => {
  it("maps abbreviations to NBA CDN logos", () => {
    expect(teamLogoUrl("GSW")).toBe("https://cdn.nba.com/logos/nba/1610612744/primary/L/logo.svg");
    expect(teamLogoUrl("unknown")).toBeNull();
  });
});

describe("TeamLogo", () => {
  it("renders the CDN logo for a canonical abbreviation", () => {
    const { container } = render(
      <TeamLogo teamId="7bf8726a-a852-452d-b81f-14839127c5fb" abbreviation="GSW" />
    );
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "https://cdn.nba.com/logos/nba/1610612744/primary/L/logo.svg"
    );
  });

  it("skips missing team ids", () => {
    const { container } = render(<TeamLogo teamId={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("TeamAbbrLink", () => {
  it("keeps the abbreviation as the accessible name", () => {
    render(
      <TeamAbbrLink
        teamId="7bf8726a-a852-452d-b81f-14839127c5fb"
        abbreviation="GSW"
        href="/teams/7bf8726a-a852-452d-b81f-14839127c5fb"
      />
    );
    expect(screen.getByRole("link", { name: "GSW" })).toBeInTheDocument();
  });
});
