import type { Metadata } from "next";

export const metadata: Metadata = { title: "Players" };

export default function PlayersLayout({ children }: { children: React.ReactNode }) {
  return children;
}
