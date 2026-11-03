"""Command line: `python -m survey_torch train [options]`."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from survey_torch.train import TrainConfig, fit


def main(argv: list[str] | None = None) -> int:
    """Train once and print the comparison with the baseline."""
    parser = argparse.ArgumentParser(prog="survey_torch")
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("train", help="train the network and the baseline")
    defaults = TrainConfig()
    train.add_argument("--seed", type=int, default=defaults.seed)
    train.add_argument("--hidden", type=int, default=defaults.hidden)
    train.add_argument("--lr", type=float, default=defaults.lr)
    train.add_argument("--batch-size", type=int, default=defaults.batch_size)
    train.add_argument("--max-epochs", type=int, default=defaults.max_epochs)
    train.add_argument("--patience", type=int, default=defaults.patience)
    train.add_argument("--curve", type=Path, help="write the loss curve to this CSV file")
    args = parser.parse_args(argv)

    config = TrainConfig(
        seed=args.seed,
        hidden=args.hidden,
        lr=args.lr,
        batch_size=args.batch_size,
        max_epochs=args.max_epochs,
        patience=args.patience,
    )
    result = fit(config)
    print(config)
    print(f"baseline  val loss {result.baseline_loss:.4f}  accuracy {result.baseline_accuracy:.4f}")
    print(f"network   val loss {result.model_loss:.4f}  accuracy {result.model_accuracy:.4f}")
    print(f"epochs run: {result.epochs_run}")
    if args.curve:
        with args.curve.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["epoch", "train_loss", "val_loss"])
            for epoch, (train_loss, val_loss) in enumerate(result.history, start=1):
                writer.writerow([epoch, f"{train_loss:.6f}", f"{val_loss:.6f}"])
        print(f"loss curve written to {args.curve}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
