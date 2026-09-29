"""
analyse_results.py

Reads the JSONL output from run_eval.py and produces:
  - Acceptance rate per model
  - Predicate failure frequency distribution per model
  - Cases where verifier fired but LLM failed to correct (for error analysis)
  - CSV export ready for native speaker rating sheet

Usage:
    python analyse_results.py results/eval.jsonl
    python analyse_results.py results/eval.jsonl --export-csv results/for_rating.csv
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_results(path: str) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _context_mode(r: dict) -> str:
    return r.get("context_mode", "none")


def acceptance_rate_table(records: list[dict]) -> None:
    by_model_context: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        by_model_context[(r["model_name"], _context_mode(r))].append(r)

    print("\nACCEPTANCE RATES (per model x context mode)")
    print(f"{'Model':<30} {'Context':<8} {'Total':>6} {'Accepted':>9} {'Rate':>7} {'Avg iters':>10}")
    print("-" * 76)
    for model, mode in sorted(by_model_context):
        rs = by_model_context[(model, mode)]
        n = len(rs)
        acc = sum(1 for r in rs if r["accepted"])
        avg_iters = sum(r["iterations_used"] for r in rs) / n if n else 0
        print(f"{model:<30} {mode:<8} {n:>6} {acc:>9} {acc/n*100:>6.1f}% {avg_iters:>10.2f}")


def acceptance_by_context_table(records: list[dict]) -> None:
    """Per-condition breakdown: first-try acceptance (verifier passed with no
    correction) vs. correction success (passed only after >=1 correction
    iteration) vs. overall acceptance rate. Rows are context_mode values
    ("none" / "coq"), so the ablation is directly readable."""
    by_context: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_context[_context_mode(r)].append(r)

    print("\nACCEPTANCE BY CONTEXT MODE")
    print(f"{'Context':<10} {'Total':>6} {'1st-try':>8} {'1st %':>7} "
          f"{'Corrected':>10} {'Corr %':>7} {'Overall %':>10}")
    print("-" * 68)
    for mode in sorted(by_context):
        rs = by_context[mode]
        n = len(rs)
        first_try = sum(1 for r in rs if r["accepted"] and r["iterations_used"] == 1)
        corrected = sum(1 for r in rs if r["accepted"] and r["iterations_used"] > 1)
        overall = first_try + corrected
        print(
            f"{mode:<10} {n:>6} {first_try:>8} {first_try / n * 100:>6.1f}% "
            f"{corrected:>10} {corrected / n * 100:>6.1f}% {overall / n * 100:>9.1f}%"
        )


def _split_parse_errors(records: list[dict], key_fn) -> tuple[dict, dict]:
    """Splits predicate_history entries into PARSE_ERROR counts (tokenizer/
    analyzer couldn't find a verb at all — a tooling/lexicon-coverage artifact,
    never reached the Coq verifier) and real verifier predicate-failure counts
    (a well-formedness rule the Coq verifier actually evaluated and rejected).
    These are different failure types and conflating them under one frequency
    table misattributes lexicon-coverage gaps to grammar-rule violations."""
    parse_errors: dict = defaultdict(int)
    verifier_failures: dict = defaultdict(Counter)
    for r in records:
        key = key_fn(r)
        for pred in r["predicate_history"]:
            if pred is None:
                continue
            if pred == "PARSE_ERROR":
                parse_errors[key] += 1
            else:
                verifier_failures[key][pred] += 1
    return parse_errors, verifier_failures


def predicate_frequency_by_context_table(records: list[dict]) -> None:
    parse_errors, verifier_failures = _split_parse_errors(records, _context_mode)

    print("\nPARSE ERRORS (per context mode — analyzer couldn't parse the output; "
          "not a grammar-rule failure)")
    print(f"  {'Context':<10} {'Parse errors':>12}")
    for mode in sorted(parse_errors):
        print(f"  {mode:<10} {parse_errors[mode]:>12}")

    print("\nVERIFIER PREDICATE FAILURES (per context mode, PARSE_ERROR excluded)")
    for mode in sorted(verifier_failures):
        counts = verifier_failures[mode]
        total = sum(counts.values())
        print(f"\n  context={mode}  (total verifier failures: {total})")
        print(f"  {'Predicate':<35} {'Count':>6} {'%':>6}")
        print("  " + "-" * 50)
        for pred, count in counts.most_common():
            print(f"  {pred:<35} {count:>6} {count/total*100:>5.1f}%")


def predicate_frequency_table(records: list[dict]) -> None:
    parse_errors, verifier_failures = _split_parse_errors(
        records, lambda r: (r["model_name"], _context_mode(r))
    )

    print("\nPARSE ERRORS (per model x context mode — analyzer couldn't parse the "
          "output; not a grammar-rule failure)")
    print(f"  {'Model':<25} {'Context':<8} {'Parse errors':>12}")
    for model, mode in sorted(parse_errors):
        print(f"  {model:<25} {mode:<8} {parse_errors[(model, mode)]:>12}")

    print("\nVERIFIER PREDICATE FAILURES (per model x context mode, PARSE_ERROR excluded)")
    for model, mode in sorted(verifier_failures):
        counts = verifier_failures[(model, mode)]
        total = sum(counts.values())
        print(f"\n  {model}  context={mode}  (total verifier failures: {total})")
        print(f"  {'Predicate':<35} {'Count':>6} {'%':>6}")
        print("  " + "-" * 50)
        for pred, count in counts.most_common():
            print(f"  {pred:<35} {count:>6} {count/total*100:>5.1f}%")


def uncorrected_failures(records: list[dict]) -> None:
    """Sentences where verifier fired on every iteration and LLM never corrected."""
    print("\nUNCORRECTED FAILURES (verifier fired, LLM never passed)")
    print(f"{'Model':<25} {'Spanish':<40} {'Final output':<40} {'Last predicate'}")
    print("-" * 130)
    for r in records:
        if not r["accepted"] and any(p is not None for p in r["predicate_history"]):
            model = r["model_name"][:24]
            spanish = r["source_sentence"][:39]
            final = r["final_output"][:39]
            last_pred = next(
                (p for p in reversed(r["predicate_history"]) if p is not None), "?"
            )
            print(f"{model:<25} {spanish:<40} {final:<40} {last_pred}")


def export_rating_csv(records: list[dict], path: str) -> None:
    """
    Exports a CSV for native speaker blind rating.
    Each row = one sentence, with columns for LLM-only output (initial)
    and LLM+verifier output (final), randomized column order per row
    so raters can't tell which is which by position.
    """
    import random
    rows = []
    for r in records:
        # Only include sentences where the verifier actually changed something
        if r["initial_output"] == r["final_output"]:
            continue
        # Randomize which column is A/B
        if random.random() < 0.5:
            a, b = r["initial_output"], r["final_output"]
            a_is_initial = True
        else:
            a, b = r["final_output"], r["initial_output"]
            a_is_initial = False
        rows.append({
            "sentence_id": len(rows),
            "model": r["model_name"],
            "context_mode": _context_mode(r),
            "spanish": r["source_sentence"],
            "output_a": a,
            "output_b": b,
            "a_is_llm_only": a_is_initial,   # hidden from rater, for decoding after
            "last_predicate": next(
                (p for p in reversed(r["predicate_history"]) if p is not None), ""
            ),
            "grammaticality_a": "",   # filled by rater
            "naturalness_a": "",
            "grammaticality_b": "",
            "naturalness_b": "",
            "notes": "",
        })

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nRating CSV written to {path} ({len(rows)} rows)")


def _semantic_flag(initial: str, final: str) -> bool:
    """Best-effort heuristic flag for "the correction loop may have changed
    what the sentence means, not just fixed its grammar". No ground-truth
    semantics available (the verifier only checks well-formedness), so this
    is a coarse content-word-overlap proxy, not a real adequacy check — see
    result.md for why a real one (back-translation / embedding similarity /
    human rating) is needed before trusting this signal. Flags True when
    initial and final differ and share less than half their content words
    (tokens longer than 2 chars, accent/apostrophe-normalized, to filter out
    short function words/particles)."""
    if initial == final:
        return False

    def content_tokens(s: str) -> set:
        return {
            re.sub(r"[^\w]", "", t.lower()).replace("'", "").replace("’", "")
            for t in s.split()
            if len(t) > 2
        }

    a, b = content_tokens(initial), content_tokens(final)
    if not a or not b:
        return bool(a or b)
    overlap = len(a & b) / len(a | b)
    return overlap < 0.5


def export_sentences_csv(records: list[dict], path: str) -> None:
    """Exports one row per (sentence, model, context_mode) result: the raw
    initial/final outputs, acceptance outcome, and a best-effort semantic_flag
    (see _semantic_flag) — a plain per-sentence audit trail, distinct from
    export_rating_csv's randomized-column blind-rating sheet."""
    rows = []
    for r in records:
        rows.append({
            "spanish": r["source_sentence"],
            "context_mode": _context_mode(r),
            "initial_output": r["initial_output"],
            "final_output": r["final_output"],
            "accepted": r["accepted"],
            "iterations_used": r["iterations_used"],
            "semantic_flag": _semantic_flag(r["initial_output"], r["final_output"]),
        })

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    flagged = sum(1 for row in rows if row["semantic_flag"])
    print(f"\nSentences CSV written to {path} ({len(rows)} rows, {flagged} semantic_flag=True)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse eval results")
    parser.add_argument("results", help="Path to JSONL results file")
    parser.add_argument("--export-csv", default=None,
                        help="Export blind rating CSV to this path")
    parser.add_argument("--export-sentences-csv", default=None,
                        help="Export per-sentence CSV (spanish, context_mode, "
                             "initial/final output, accepted, iterations_used, "
                             "semantic_flag) to this path")
    args = parser.parse_args()

    records = load_results(args.results)
    print(f"Loaded {len(records)} records from {args.results}")

    acceptance_rate_table(records)
    acceptance_by_context_table(records)
    predicate_frequency_table(records)
    predicate_frequency_by_context_table(records)
    uncorrected_failures(records)

    if args.export_csv:
        export_rating_csv(records, args.export_csv)
    if args.export_sentences_csv:
        export_sentences_csv(records, args.export_sentences_csv)


if __name__ == "__main__":
    main()