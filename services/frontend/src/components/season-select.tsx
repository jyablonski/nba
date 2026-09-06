export function SeasonSelect({
  season,
  seasons,
  setSeason,
  label = "Season",
}: {
  season: string;
  seasons: string[];
  setSeason: (value: string) => void;
  label?: string;
}) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-ink-2">
      {label}
      <select
        className="field px-1.5"
        value={season}
        onChange={(event) => setSeason(event.target.value)}
      >
        {seasons.length === 0 ? <option value={season}>{season || "—"}</option> : null}
        {seasons.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
    </label>
  );
}
