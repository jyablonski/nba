"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useSeason() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requested = searchParams.get("season") ?? "";

  const seasonsQuery = useQuery({
    queryKey: ["seasons"],
    queryFn: () => api.listSeasons(),
  });
  const seasons = (seasonsQuery.data?.data ?? []).map((item) => item.season);
  const season = requested && seasons.includes(requested) ? requested : (seasons[0] ?? requested);

  function setSeason(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (next) params.set("season", next);
    else params.delete("season");
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  }

  return {
    season,
    seasons,
    setSeason,
    isLoading: seasonsQuery.isPending,
  };
}
