"""
run_eval.py

Entry point for running the multi-model batch evaluation.

Usage (run from the project root):
    python -m guarani.run_ai_eval --sentences data/spanish_sentences.txt \
                       --models gemini-3.6-flash deepseek-chat \
                       --output results/eval.jsonl \
                       --workers 4

The sentences file should have one Spanish sentence per line.
Results are written as JSONL, one record per (sentence, model) pair.

After the run, use analyse_results.py to get the frequency distribution
of failed predicates and acceptance rates per model.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Ensure the project root (parent of guarani/) is importable so the package's
# relative imports (e.g. loop.py's `from .analyzer import ...`) resolve.
sys.path.insert(0, str(Path(__file__).parent.parent))

from guarani.loop import (
    run_batch_eval,
    LLM_REGISTRY,
    EvalResult,
    make_deepseek_fn,
    make_gemini_fn,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def load_sentences(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    sentences = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
    logger.info("Loaded %d sentences from %s", len(sentences), path)
    return sentences


def build_llm_fns(model_names: list[str], temperature: float | None = None) -> dict:
    fns = {}
    for name in model_names:
        if name not in LLM_REGISTRY:
            logger.warning("Unknown model '%s', skipping. Available: %s", name, list(LLM_REGISTRY))
            continue
        # Check required env var is set before building the fn
        if name.startswith("deepseek") and not os.environ.get("DEEPSEEK_API_KEY"):
            logger.error("DEEPSEEK_API_KEY not set, skipping %s", name)
            continue
        if name.startswith("gemini") and not os.environ.get("GEMINI_API_KEY"):
            logger.error("GEMINI_API_KEY not set, skipping %s", name)
            continue
        if temperature is None:
            fns[name] = LLM_REGISTRY[name]()
        elif name.startswith("deepseek"):
            fns[name] = make_deepseek_fn(name, temperature=temperature)
        elif name.startswith("gemini"):
            fns[name] = make_gemini_fn(name, temperature=temperature)
        else:
            fns[name] = LLM_REGISTRY[name]()
        logger.info("Loaded model: %s%s", name, f" (temperature={temperature})" if temperature is not None else "")
    return fns


def print_summary(results: list[EvalResult]) -> None:
    """Prints a quick summary table to stdout after the run."""
    by_model: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_model[r.model_name].append(r)

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    for model, model_results in sorted(by_model.items()):
        n = len(model_results)
        accepted = sum(1 for r in model_results if r.accepted)
        acceptance_rate = accepted / n * 100 if n else 0

        # Predicate frequency: only count iterations that actually fired
        predicate_counts: Counter = Counter()
        for r in model_results:
            for pred in r.predicate_history:
                if pred is not None:
                    predicate_counts[pred] += 1

        print(f"\nModel: {model}")
        print(f"  Sentences:       {n}")
        print(f"  Accepted:        {accepted}/{n} ({acceptance_rate:.1f}%)")
        print(f"  Top errors:")
        for pred, count in predicate_counts.most_common(5):
            print(f"    {pred:<35} {count}")

    print("\n" + "=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-model Guaraní evaluation")
    parser.add_argument("--sentences", required=True,
                        help="Path to file with one Spanish sentence per line")
    parser.add_argument("--models", nargs="+",
                        default=["gemini-3.6-flash", "deepseek-chat"],
                        help="Model names to evaluate (space-separated)")
    parser.add_argument("--output", default="results/eval.jsonl",
                        help="Output JSONL file path")
    parser.add_argument("--lexicon", default=None,
                        help="Path to merged.csv (default: data/merged.csv relative to package)")
    parser.add_argument("--coq-lib-dir", default=None,
                        help="Path to Coq library directory (default: $COQ_LIB_DIR or ./rocq)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel workers")
    parser.add_argument("--max-iterations", type=int, default=3,
                        help="Max correction iterations per sentence")
    parser.add_argument("--rate-limit-delay", type=float, default=0.5,
                        help="Seconds to sleep between API calls per worker")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only run the first N sentences (useful for quick tests)")
    parser.add_argument("--context", choices=["none", "coq"], default="none",
                        help="Grammar context mode (default: none)")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Override LLM sampling temperature (default: each "
                             "model factory's own default, currently 0.3)")
    args = parser.parse_args()

    sentences = load_sentences(args.sentences)
    if args.limit:
        sentences = sentences[: args.limit]
        logger.info("Limited to first %d sentences", args.limit)

    llm_fns = build_llm_fns(args.models, temperature=args.temperature)
    if not llm_fns:
        logger.error("No valid models found. Exiting.")
        sys.exit(1)

    kwargs = {}
    if args.lexicon:
        kwargs["lexicon_csv"] = args.lexicon
    if args.coq_lib_dir:
        kwargs["coq_lib_dir"] = args.coq_lib_dir

    results = run_batch_eval(
        spanish_sentences=sentences,
        llm_fns=llm_fns,
        output_path=args.output,
        max_workers=args.workers,
        max_iterations=args.max_iterations,
        rate_limit_delay=args.rate_limit_delay,
        context_mode=args.context,
        **kwargs,
    )

    print_summary(results)
    logger.info("Results written to %s", args.output)


if __name__ == "__main__":
    main()