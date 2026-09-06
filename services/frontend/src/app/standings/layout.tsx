import type { Metadata } from "next";

export const metadata: Metadata = { title: "Standings" };

export default function StandingsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
