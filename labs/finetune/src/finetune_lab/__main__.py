"""Command line: `python -m finetune_lab pretrain` then `python -m finetune_lab compare`."""

from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean

from finetune_lab.train import (
    STRATEGIES,
    FinetuneConfig,
    ModelConfig,
    PretrainConfig,
    finetune,
    load_checkpoint,
    pretrain,
    save_checkpoint,
)

DEFAULT_CHECKPOINT = Path("checkpoints/encoder.pt")


def main(argv: list[str] | None = None) -> int:
    """Pretrain and save a checkpoint, or compare the four strategies on it."""
    parser = argparse.ArgumentParser(prog="finetune_lab")
    commands = parser.add_subparsers(dest="command", required=True)
    pre = commands.add_parser("pretrain", help="masked-token pretraining")
    pre.add_argument("--out", type=Path, default=DEFAULT_CHECKPOINT)
    cmp_ = commands.add_parser("compare", help="fine-tune four ways and compare")
    cmp_.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    cmp_.add_argument("--n-train", type=int, default=FinetuneConfig().n_train)
    cmp_.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    args = parser.parse_args(argv)

    if args.command == "pretrain":
        state, losses = pretrain(PretrainConfig(), ModelConfig())
        save_checkpoint(state, args.out)
        print("masked-token loss by epoch:", ", ".join(f"{loss:.3f}" for loss in losses))
        print(f"saved {args.out}")
        return 0

    checkpoint = load_checkpoint(args.checkpoint)
    print(f"{args.n_train} labelled sequences, seeds {args.seeds}")
    print(f"{'strategy':<9} {'trainable':>9} {'total':>7}  accuracy by seed      mean")
    for strategy in STRATEGIES:
        results = [
            finetune(
                FinetuneConfig(strategy=strategy, seed=s, n_train=args.n_train),
                ModelConfig(),
                checkpoint,
            )
            for s in args.seeds
        ]
        scores = " ".join(f"{r.accuracy:.3f}" for r in results)
        mean_acc = mean(r.accuracy for r in results)
        counts = f"{results[0].trainable:>9,} {results[0].total:>7,}"
        print(f"{strategy:<9} {counts}  {scores:<20} {mean_acc:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
