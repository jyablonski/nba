import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TeamAbbrLink, TeamLogo } from "@/components/team-logo";
import { teamLogoLabel } from "@/lib/team-logo";

describe("teamLogoLabel", () => {
  it("uses the canonical abbreviation as a neutral local label", () => {
    expect(teamLogoLabel(" warriors ")).toBe("WAR");
    expect(teamLogoLabel(null)).toBe("NBA");
  });
});

describe("TeamLogo", () => {
  it("renders a decorative local badge", () => {
    render(<TeamLogo teamId="7bf8726a-a852-452d-b81f-14839127c5fb" abbreviation="GSW" />);
    expect(screen.getByText("GSW")).toBeInTheDocument();
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
