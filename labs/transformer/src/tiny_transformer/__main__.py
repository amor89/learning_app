"""Command line: `python -m tiny_transformer train [--no-positions] [--seed N]`."""

from __future__ import annotations

import argparse

from tiny_transformer.train import TrainConfig, run


def main(argv: list[str] | None = None) -> int:
    """Train once and print validation accuracy and the loss curve."""
    parser = argparse.ArgumentParser(prog="tiny_transformer")
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train", help="train the classifier")
    train.add_argument("--seed", type=int, default=TrainConfig().seed)
    train.add_argument("--no-positions", action="store_true", help="leave out position encodings")
    args = parser.parse_args(argv)

    config = TrainConfig(seed=args.seed, use_positions=not args.no_positions)
    result = run(config)
    print(config)
    print(f"validation accuracy {result.val_accuracy:.4f}")
    print("training loss by epoch:", ", ".join(f"{loss:.3f}" for loss in result.losses))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
