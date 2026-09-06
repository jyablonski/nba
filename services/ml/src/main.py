"""CLI: python -m src.main  (eval / score)."""

from __future__ import annotations

import logging

import click

from scoring import evaluate, score_and_persist


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@click.group()
def cli() -> None:
    """Pregame Elo win probability (Regular Season only). Writes source.game_predictions."""
    _configure_logging()


@cli.command("eval")
def eval_cmd() -> None:
    """Walk-forward Elo on gold Regular Season Finals; print logloss / Brier / accuracy."""
    result = evaluate()
    click.echo(f"model={result['model_name']} version={result['model_version']}")
    click.echo(f"holdout_season={result['holdout_season']}")
    click.echo(f"n={int(result['n'])}")
    click.echo(f"logloss={result['logloss']}")
    click.echo(f"brier={result['brier']}")
    click.echo(f"accuracy={result['accuracy']}")
    click.echo(f"home_always_accuracy={result['home_always_accuracy']}")


@cli.command("score")
def score_cmd() -> None:
    """Fit Elo on Regular Season Finals and persist pregame WP for upcoming games."""
    result = score_and_persist()
    click.echo(f"model={result['model_name']} version={result['model_version']}")
    click.echo(f"history_games={result['history_games']}")
    click.echo(f"upcoming_games={result['upcoming_games']}")
    click.echo(f"written={result['written']}")
    click.echo(f"as_of={result['as_of']}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
