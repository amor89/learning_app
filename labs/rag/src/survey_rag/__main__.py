"""Command line: `python -m survey_rag eval` or `python -m survey_rag ask "..."`."""

from __future__ import annotations

import argparse
from pathlib import Path

from survey_rag.corpus import load_chunks
from survey_rag.evaluate import evaluate_retrieval, load_gold
from survey_rag.index import Index
from survey_rag.llm import DEFAULT_MODEL, make_claude_caller
from survey_rag.pipeline import answer_question
from survey_rag.prompt import SYSTEM, build_messages

LAB = Path(__file__).resolve().parents[2]
NOTES = LAB / "notes"
GOLD = LAB / "eval" / "questions.jsonl"


def main(argv: list[str] | None = None) -> int:
    """Run one command and return the exit code."""
    parser = argparse.ArgumentParser(prog="survey_rag")
    parser.add_argument("--size", type=int, default=80, help="words per chunk")
    parser.add_argument("--overlap", type=int, default=20, help="words shared by neighbours")
    commands = parser.add_subparsers(dest="command", required=True)
    ev = commands.add_parser("eval", help="score retrieval on the gold questions")
    ev.add_argument("--k", type=int, default=3)
    ask = commands.add_parser("ask", help="answer one question")
    ask.add_argument("question")
    ask.add_argument("--k", type=int, default=5)
    ask.add_argument("--budget", type=int, default=300, help="words of source text")
    ask.add_argument("--model", default=DEFAULT_MODEL)
    ask.add_argument("--dry-run", action="store_true", help="print the prompt, call nothing")
    args = parser.parse_args(argv)

    index = Index(load_chunks(NOTES, args.size, args.overlap))
    if args.command == "eval":
        scores = evaluate_retrieval(index, load_gold(GOLD), args.k)
        for name, value in scores.items():
            print(f"{name}: {value:.3f}")
        return 0
    if args.dry_run:
        messages, _ = build_messages(
            args.question, index.search(args.question)[: args.k], args.budget
        )
        print(SYSTEM, "\n---\n", messages[0]["content"], sep="")
        return 0
    result = answer_question(
        args.question, index, make_claude_caller(SYSTEM, args.model), args.k, args.budget
    )
    print(result.text)
    print("sources:", ", ".join(result.sources) or "none")
    print("problems:", ", ".join(result.problems) or "none")
    return 1 if result.problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
