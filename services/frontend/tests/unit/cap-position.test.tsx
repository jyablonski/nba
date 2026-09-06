import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CapPosition } from "@/components/teams/cap-position";

describe("cap position", () => {
  it("renders first-apron status, distances, and 2023 CBA restrictions", () => {
    render(
      <CapPosition
        team={{
          current_season_payroll: 221_300_000,
          current_remaining_guaranteed: 429_100_000,
          current_contract_season: "2026-27",
          salary_cap: 164_961_000,
          luxury_tax: 200_428_000,
          first_apron: 209_015_000,
          second_apron: 221_686_000,
          over_luxury_tax: true,
          over_first_apron: true,
          over_second_apron: false,
        }}
      />
    );

    expect(screen.getByText("Cap position · 2026-27")).toBeInTheDocument();
    expect(screen.getByText("Over 1st apron (tier 3 of 4)")).toBeInTheDocument();
    expect(screen.getAllByText("$221.3M").length).toBeGreaterThan(0);
    expect(screen.getByText("$429.1M")).toBeInTheDocument();
    expect(screen.getByText("+$20.9M over")).toBeInTheDocument();
    expect(screen.getByText("-$0.4M under")).toBeInTheDocument();
    expect(screen.getByText("Taxpayer mid-level exception")).toBeInTheDocument();
    expect(screen.getByText("Aggregating salaries in trade")).toBeInTheDocument();
    expect(screen.getByText(/Not a tax bill/)).toBeInTheDocument();
    expect(screen.queryByText(/tax bill of/i)).not.toBeInTheDocument();
  });

  it("shows an empty snapshot when payroll is missing", () => {
    render(<CapPosition team={{}} />);
    expect(screen.getByText("No BRef payroll snapshot for this team yet.")).toBeInTheDocument();
  });

  it("staggers close tax/apron labels so Detroit-like thresholds stay readable", () => {
    render(
      <CapPosition
        team={{
          current_season_payroll: 153_163_826,
          current_remaining_guaranteed: 327_526_339,
          current_contract_season: "2026-27",
          salary_cap: 164_961_000,
          luxury_tax: 200_428_000,
          first_apron: 209_015_000,
          second_apron: 221_686_000,
          over_luxury_tax: false,
          over_first_apron: false,
          over_second_apron: false,
        }}
      />
    );

    const tax = screen.getByText("Tax $200.4M");
    const first = screen.getByText("1st apron $209M");
    const second = screen.getByText("2nd apron $221.7M");
    expect(tax).toHaveAttribute("data-lane", "0");
    expect(first).toHaveAttribute("data-lane", "1");
    expect(second).toBeInTheDocument();
    expect(new Set([tax, first, second].map((node) => node.getAttribute("data-lane"))).size).toBe(
      2
    );
  });
});
