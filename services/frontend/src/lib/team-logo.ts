export function teamLogoLabel(abbreviation: string | null | undefined): string {
  return abbreviation?.trim().slice(0, 3).toUpperCase() || "NBA";
}
