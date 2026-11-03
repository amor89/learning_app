"""Command line: train, promote, export, serve and drift.

Set MLFLOW_TRACKING_URI first, for example `sqlite:///mlflow.db`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from serve_lab.data import make_answers
from serve_lab.drift import drift_status, psi
from serve_lab.model import save_artifact, train

MODEL_NAME = "survey_topics"


def drift_report(n: int, seed: int) -> list[tuple[str, float, str]]:
    """PSI of answer length and model confidence, training-like batch against a shifted one."""
    model, _ = train(seed=seed)
    base, _ = make_answers(n, seed + 10)
    later, _ = make_answers(n, seed + 11, shifted=True)
    rows: list[tuple[str, float, str]] = []
    for name, feature in (
        ("answer_length", lambda t: np.array([len(x.split()) for x in t], dtype=float)),
        ("confidence", lambda t: model.predict_proba(t).max(axis=1)),
    ):
        value = psi(feature(base), feature(later))
        rows.append((name, value, drift_status(value)))
    same = psi(
        model.predict_proba(base).max(axis=1),
        model.predict_proba(make_answers(n, seed + 12)[0]).max(axis=1),
    )
    rows.append(("confidence, unshifted batch", same, drift_status(same)))
    return rows


def main(argv: list[str] | None = None) -> int:
    """Run one command."""
    parser = argparse.ArgumentParser(prog="serve_lab")
    commands = parser.add_subparsers(dest="command", required=True)
    tr = commands.add_parser("train", help="train, log to MLflow and register a new version")
    tr.add_argument("--c", type=float, default=1.0, help="inverse regularisation strength")
    pr = commands.add_parser("promote", help="point an alias at a version")
    pr.add_argument("version")
    pr.add_argument("--alias", default="champion")
    ex = commands.add_parser("export", help="save the aliased version for the container")
    ex.add_argument("--alias", default="champion")
    ex.add_argument("--out", type=Path, default=Path("model"))
    sv = commands.add_parser("serve", help="serve the exported model with uvicorn")
    sv.add_argument("--port", type=int, default=8000)
    dr = commands.add_parser("drift", help="PSI report on a shifted batch")
    dr.add_argument("--n", type=int, default=1_000)
    args = parser.parse_args(argv)

    if args.command == "train":
        from serve_lab.registry import register
        from serve_lab.tracking import log_run

        model, accuracy = train(c=args.c)
        version = register(log_run(model, accuracy, {"C": args.c}), MODEL_NAME)
        print(f"registered {MODEL_NAME} version {version}, validation accuracy {accuracy:.4f}")
    elif args.command == "promote":
        from serve_lab.registry import promote

        promote(MODEL_NAME, args.version, args.alias)
        print(f"{MODEL_NAME}@{args.alias} -> version {args.version}")
    elif args.command == "export":
        from serve_lab.registry import load_alias

        model, meta = load_alias(MODEL_NAME, args.alias)
        save_artifact(model, meta, args.out)
        print(f"exported {meta.name} version {meta.version} to {args.out}")
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("serve_lab.app:build", factory=True, host="127.0.0.1", port=args.port)
    else:
        for name, value, status in drift_report(args.n, seed=0):
            print(f"{name:<28} PSI {value:.3f}  {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
