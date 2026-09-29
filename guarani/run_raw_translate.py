"""
run_raw_translate.py

Single-shot translation only — no verifier, no correction loop, no automated
accept/reject. Unlike run_ai_eval.py, this never calls verifier.py or
analyzer.py at all: correctness here is judged by a human, not the Coq
verifier's well-formedness predicates.

For each sentence, both context conditions ("none" and "coq") are translated
once each (single LLM call per condition — no correction iterations), and
written to a flat JSONL log plus (optionally) a blind side-by-side CSV: each
row holds both conditions' output for the same sentence, in randomized
column order with the condition hidden in a separate column, so a human
rater can judge correctness/naturalness without knowing which output came
from which condition until they decode it afterward.

Usage (run from the project root):
    python -m guarani.run_raw_translate --sentences data/exp2_sentences.txt \
                       --models deepseek-chat --temperature 0.1 \
                       --output results/exp3_raw.jsonl \
                       --review-csv results/exp3_review.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Ensure the project root (parent of guarani/) is importable, same as run_ai_eval.py.
sys.path.insert(0, str(Path(__file__).parent.parent))

from guarani.run_ai_eval import load_sentences, build_llm_fns
from guarani.loop import (
    TRANSLATION_PROMPT_TEMPLATE,
    CONTEXT_PROMPT_PREFIX_TEMPLATE,
    load_coq_context_once,
    _sanitize_llm_output,
    _DEFAULT_COQ_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

CONTEXT_MODES = ("none", "coq")


def translate_once(spanish: str, llm_fn, context_mode: str, coq_context: str) -> str:
    prefix = (
        CONTEXT_PROMPT_PREFIX_TEMPLATE.format(coq_context=coq_context)
        if context_mode == "coq" else ""
    )
    prompt = prefix + TRANSLATION_PROMPT_TEMPLATE.format(spanish=spanish)
    return _sanitize_llm_output(llm_fn(prompt))


def export_review_csv(records: list[dict], path: str) -> None:
    """One row per (sentence, model): both context-mode outputs side by side,
    column order randomized per row and the condition hidden in its own
    column, so correctness can be judged blind to context_mode."""
    by_key: dict[tuple[str, str], dict[str, str]] = {}
    for r in records:
        key = (r["source_sentence"], r["model_name"])
        by_key.setdefault(key, {})[r["context_mode"]] = r["output"]

    rows = []
    for (spanish, model), outs in sorted(by_key.items()):
        if "none" not in outs or "coq" not in outs:
            continue
        if random.random() < 0.5:
            a, b, a_is_coq = outs["none"], outs["coq"], False
        else:
            a, b, a_is_coq = outs["coq"], outs["none"], True
        rows.append({
            "spanish": spanish,
            "model": model,
            "output_a": a,
            "output_b": b,
            "a_is_coq_context": a_is_coq,  # hidden from rater; for decoding after
            "correct_a": "",               # filled in manually
            "correct_b": "",
            "notes": "",
        })

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Review CSV written to %s (%d rows)", path, len(rows))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Single-shot translation only, no verifier/correction loop "
                    "-- for manual (human) correctness review instead of Coq."
    )
    parser.add_argument("--sentences", required=True,
                        help="Path to file with one Spanish sentence per line")
    parser.add_argument("--models", nargs="+", default=["deepseek-chat"],
                        help="Model names to evaluate (space-separated)")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Override LLM sampling temperature (default: each "
                             "model factory's own default, currently 0.3)")
    parser.add_argument("--coq-dir", default=None,
                        help="Coq grammar directory for context_mode=coq "
                             "(default: $COQ_LIB_DIR or ./rocq)")
    parser.add_argument("--output", default="results/raw_translate.jsonl",
                        help="Flat JSONL log path (both context modes)")
    parser.add_argument("--review-csv", default=None,
                        help="Blind side-by-side CSV path for manual review")
    parser.add_argument("--rate-limit-delay", type=float, default=0.5,
                        help="Seconds to sleep between API calls")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only run the first N sentences (useful for quick tests)")
    args = parser.parse_args()

    sentences = load_sentences(args.sentences)
    if args.limit:
        sentences = sentences[: args.limit]
        logger.info("Limited to first %d sentences", args.limit)

    llm_fns = build_llm_fns(args.models, temperature=args.temperature)
    if not llm_fns:
        logger.error("No valid models found. Exiting.")
        sys.exit(1)

    coq_context = load_coq_context_once(args.coq_dir or _DEFAULT_COQ_DIR)

    records: list[dict] = []
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for spanish in sentences:
            for model_name, llm_fn in llm_fns.items():
                for context_mode in CONTEXT_MODES:
                    if args.rate_limit_delay > 0:
                        time.sleep(args.rate_limit_delay)
                    output = translate_once(spanish, llm_fn, context_mode, coq_context)
                    rec = {
                        "source_sentence": spanish,
                        "model_name": model_name,
                        "context_mode": context_mode,
                        "output": output,
                    }
                    records.append(rec)
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    logger.info("[%s][%s] %s -> %s", model_name, context_mode, spanish, output)

    logger.info("Wrote %d raw translations to %s", len(records), args.output)

    if args.review_csv:
        export_review_csv(records, args.review_csv)


if __name__ == "__main__":
    main()
