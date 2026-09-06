import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/teams",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    listSeasons: async () => ({
      data: [{ season: "2025-26" }, { season: "2024-25" }],
      meta: { total: 2, limit: 2, offset: 0 },
    }),
  },
}));

import { Providers } from "@/components/providers";
import { useSeason } from "@/hooks/use-season";

describe("useSeason default", () => {
  it("uses the latest loaded season when the URL has no season", async () => {
    const { result } = renderHook(() => useSeason(), { wrapper: Providers });
    await waitFor(() => {
      expect(result.current.season).toBe("2025-26");
    });
    expect(result.current.seasons).toEqual(["2025-26", "2024-25"]);
  });
});
