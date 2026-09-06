import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TeamAbbrLink, TeamLogo } from "@/components/team-logo";
import { nbaTeamLogoUrl } from "@/lib/team-logo";

describe("nbaTeamLogoUrl", () => {
  it("uses the public NBA CDN path", () => {
    expect(nbaTeamLogoUrl(1610612738)).toBe(
      "https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg"
    );
  });
});

describe("TeamLogo", () => {
  it("renders a decorative CDN image", () => {
    render(<TeamLogo teamId={1610612738} />);
    const image = screen.getByRole("presentation");
    expect(image).toHaveAttribute("src", nbaTeamLogoUrl(1610612738));
    expect(image).toHaveAttribute("alt", "");
  });

  it("skips missing team ids", () => {
    const { container } = render(<TeamLogo teamId={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("TeamAbbrLink", () => {
  it("keeps the abbreviation as the accessible name", () => {
    render(<TeamAbbrLink teamId={1610612738} abbreviation="BOS" href="/teams/1610612738" />);
    const link = screen.getByRole("link", { name: "BOS" });
    expect(link).toHaveAttribute("href", "/teams/1610612738");
    expect(link.querySelector("img")).toHaveAttribute("src", nbaTeamLogoUrl(1610612738));
  });
});
