"""Command line: `python -m digits_cnn train [--augment] [--seed N]`."""

from __future__ import annotations

import argparse

import numpy as np

from digits_cnn.train import TrainConfig, run


def main(argv: list[str] | None = None) -> int:
    """Train both models once and print the comparison."""
    parser = argparse.ArgumentParser(prog="digits_cnn")
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train", help="train the dense network and the CNN")
    train.add_argument("--seed", type=int, default=TrainConfig().seed)
    train.add_argument("--augment", action="store_true", help="train with random one-pixel shifts")
    args = parser.parse_args(argv)

    config = TrainConfig(seed=args.seed, augment=args.augment)
    print(config)
    for result in run(config):
        print(
            f"{result.name:5}  parameters {result.n_parameters:5}  val loss {result.val_loss:.4f}"
            f"  accuracy {result.val_accuracy:.4f}  epochs {result.epochs_run}"
        )
        recall = np.array2string(result.recall, precision=2, separator=", ")
        print(f"       recall by digit {recall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
