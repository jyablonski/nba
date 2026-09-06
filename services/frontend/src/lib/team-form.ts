export type FormGame = {
  is_win?: boolean | null;
  result?: string | null;
};

function winFlag(game: FormGame): boolean | null {
  if (game.is_win === true) return true;
  if (game.is_win === false) return false;
  if (game.result === "W") return true;
  if (game.result === "L") return false;
  return null;
}

export function lastTenFromGames(games: FormGame[]): string | null {
  const recent = games.slice(0, 10);
  let wins = 0;
  let losses = 0;
  for (const game of recent) {
    const win = winFlag(game);
    if (win === true) wins += 1;
    else if (win === false) losses += 1;
  }
  if (wins + losses === 0) return null;
  return `${wins}–${losses}`;
}

export function streakFromGames(games: FormGame[]): string | null {
  if (games.length === 0) return null;
  const first = winFlag(games[0]);
  if (first == null) return null;
  let count = 0;
  for (const game of games) {
    const win = winFlag(game);
    if (win == null || win !== first) break;
    count += 1;
  }
  return `${first ? "W" : "L"}${count}`;
}
