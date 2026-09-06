"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Menu, X } from "lucide-react";

import { BaselineWordmark } from "@/components/brand/baseline-wordmark";
import { api } from "@/lib/api";
import { formatScrapedAt } from "@/lib/format";
import { isNavActive, PRIMARY_NAV } from "@/lib/nav";
import { cn } from "@/lib/utils";

export function Header() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const statusQuery = useQuery({
    queryKey: ["status"],
    queryFn: () => api.getStatus(),
  });

  const scraped = formatScrapedAt(statusQuery.data?.last_scraped_at);

  return (
    <header className="sticky top-0 z-20 border-b border-rule-strong bg-raised">
      <div className="mx-auto flex h-[var(--ct-header-h-sm)] max-w-[1280px] items-center gap-3 px-[14px] sm:h-[var(--ct-header-h)] sm:px-6">
        <Link href="/" aria-label="Baseline" className="shrink-0">
          <BaselineWordmark className="block h-[38px] w-auto" />
        </Link>

        <nav aria-label="Primary" className="hidden h-full items-center gap-5 md:flex">
          {PRIMARY_NAV.map((item) => {
            const active = isNavActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn("ct-tab", active && "ct-tab-active")}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <button
          type="button"
          className="ml-auto inline-flex size-8 items-center justify-center border border-rule text-foreground md:hidden"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
        </button>

        <p className="ml-auto hidden type-timestamp shrink-0 whitespace-nowrap md:block">
          Scraped {scraped}
        </p>
      </div>

      {menuOpen ? (
        <div className="border-t border-rule px-[14px] py-3 md:hidden">
          <nav aria-label="Primary mobile" className="flex flex-col gap-2">
            {PRIMARY_NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className={cn(
                  "type-nav py-1",
                  isNavActive(pathname, item.href) ? "font-semibold text-foreground" : "text-ink-2"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <p className="type-timestamp mt-3">Scraped {scraped}</p>
        </div>
      ) : null}
    </header>
  );
}
