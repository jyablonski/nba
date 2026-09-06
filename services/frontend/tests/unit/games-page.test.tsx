import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/games",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    listGames: async () => ({
      data: [
        {
          game_id: "0042500405",
          season: "2025-26",
          game_date: "2026-06-13",
          home_team_abbreviation: "SAS",
          away_team_abbreviation: "NYK",
          home_score: 125,
          away_score: 108,
          score_margin: 17,
        },
      ],
      meta: { total: 1, limit: 15, offset: 0 },
    }),
  },
  queryErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "error"),
}));

import GamesPage from "@/app/games/page";
import { Providers } from "@/components/providers";

describe("games index", () => {
  it("lists recent final games with play-by-play links", async () => {
    render(
      <Providers>
        <GamesPage />
      </Providers>
    );
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Play-by-play →" })).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "Game flow" })).toBeInTheDocument();
    expect(screen.getByText("Recent final games")).toBeInTheDocument();
    expect(screen.getByText("Margin")).toBeInTheDocument();
    expect(screen.getByText("NYK")).toBeInTheDocument();
    expect(screen.getByText("SAS")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Play-by-play →" })).toHaveAttribute(
      "href",
      "/games/0042500405"
    );
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });
});
