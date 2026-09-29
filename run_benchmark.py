"""
run_benchmark.py

Reads a benchmark CSV (one row per test case) and runs each sentence through
the Guaraní analyzer + Coq verifier pipeline, classifying every outcome into:

  PASS          — pipeline verdict matches expected_verdict
  FAIL          — pipeline verdict differs from expected_verdict

For every FAIL (and for any case whose verdict is ill-formed regardless of
whether it passed), the failure is further categorised:

  coq_error     — the Coq engine returned an internal error (COQ_ERROR)
  out_of_scope  — the pipeline produced no candidates at all (parse_error),
                  meaning the input is outside the analyser's coverage
  dictionary_gap — at least one token was unknown / not in the lexicon
  grammar_violation — a specific Coq predicate failed (the "normal" case)

Usage:
    python run_benchmark.py [path/to/benchmark.csv] [options]

Options:
    --csv PATH          Path to benchmark CSV (default: guarani_benchmark.csv)
    --out PATH          Path to write results CSV (default: benchmark_results.csv)
    --verbose / -v      Also print every row to stdout
    --summary / -s      Print a summary table at the end (default: on)
    --filter VERDICT    Only show rows with this verdict in verbose mode (wf/ill)
    --help / -h         Show this message

CSV format expected (header row required):
    theorem, module, section, sentence, expected_verdict,
    expected_failing_predicate, notes

The script imports check.py's internals directly to avoid subprocess overhead,
so it must be run from the same directory as check.py (or with PYTHONPATH set).
"""

import sys
import csv
import argparse
import textwrap
import time
from pathlib import Path
from typing import Optional

# ── resolve the project root so imports work regardless of cwd ──────────────
SCRIPT_DIR = Path(__file__).resolve().parent
# Walk up until we find check.py (handles both outputs/ subdirectory and root)
_project_root: Optional[Path] = None
for _candidate in [SCRIPT_DIR, SCRIPT_DIR.parent, SCRIPT_DIR.parent.parent]:
    if (_candidate / "check.py").exists():
        _project_root = _candidate
        break
if _project_root is None:
    sys.exit(
        "ERROR: cannot locate check.py — run this script from the project "
        "root, or place run_benchmark.py alongside check.py."
    )
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ── import pipeline internals ────────────────────────────────────────────────
try:
    from guarani.analyzer import (
        load_lexicon, load_noun_lexicon, load_adj_lexicon, load_neg_pron_lexicon,
        is_unknown_token, _nfc,
    )
    from guarani.loop import (
        tokenize, _is_known_adv_subordinator,
        build_nonverbal_candidates,
    )
    from guarani.verifier import Verifier
    from check import (
        build_candidate_sentences,
        build_complex_candidates,
        build_enclitic_complex_candidates,
        build_coordinated_candidates,
    )
except ImportError as exc:
    sys.exit(
        f"ERROR: could not import pipeline modules ({exc}).\n"
        "Make sure the guarani package and check.py are on PYTHONPATH."
    )

# ── load lexicons once ───────────────────────────────────────────────────────
_LEXICON_CSV = _project_root / "data" / "merged.csv"
if not _LEXICON_CSV.exists():
    sys.exit(f"ERROR: lexicon not found at {_LEXICON_CSV}")
load_lexicon(str(_LEXICON_CSV))
load_noun_lexicon(str(_LEXICON_CSV))
load_adj_lexicon(str(_LEXICON_CSV))
load_neg_pron_lexicon(str(_LEXICON_CSV))


# ── failure categories ────────────────────────────────────────────────────────
CATEGORY_COQ_ERROR    = "coq_error"
CATEGORY_OUT_OF_SCOPE = "out_of_scope"
CATEGORY_DICT_GAP     = "dictionary_gap"
CATEGORY_GRAMMAR      = "grammar_violation"
CATEGORY_NONE         = "—"          # used when the sentence is WF (no failure)


def _has_unknown_tokens(tokens: list[str]) -> bool:
    """True if any token is absent from the lexicon AND is not a known
    subordinator/postposition/particle."""
    for tok in tokens:
        nfc = _nfc(tok)
        # Particles that the pipeline handles structurally and that will never
        # appear in the lexicon are not dictionary gaps.
        if nfc in ("hikuái", "hikuai", "ha", "térã", "ani", "piko", "pa",
                   "porque", "mboyve", "rire", "vove", "jave", "aja",
                   "haguã", "hagua", "jepe", "voi", "niko", "ko", "ngo",
                   "ningo", "ndaje", "jeko", "kuri", "ra'e", "raka'e",
                   "mbora'e", "nipo", "hína"):
            continue
        if _is_known_adv_subordinator(tok):
            continue
        if is_unknown_token(tok):
            return True
    return False


def _classify_failure(failed_pred: str, tokens: list[str]) -> str:
    """Map a pipeline failure to one of the four benchmark categories."""
    if failed_pred == "COQ_ERROR":
        return CATEGORY_COQ_ERROR
    if failed_pred == "parse_error":
        # No candidates were built at all.
        if _has_unknown_tokens(tokens):
            return CATEGORY_DICT_GAP
        return CATEGORY_OUT_OF_SCOPE
    # A specific Coq predicate failed.  Even so, if a token is unknown the
    # dictionary gap may have caused a spurious parse path to be selected.
    if _has_unknown_tokens(tokens):
        return CATEGORY_DICT_GAP
    return CATEGORY_GRAMMAR


def run_sentence(sentence: str) -> dict:
    """Run the full pipeline on one surface string and return a result dict."""
    tokens = tokenize(sentence)
    t0 = time.perf_counter()

    candidates: list = build_candidate_sentences(tokens)
    candidates += build_complex_candidates(tokens)
    candidates += build_enclitic_complex_candidates(tokens)
    candidates += build_coordinated_candidates(tokens)
    candidates += build_nonverbal_candidates(tokens)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    if not candidates:
        unknown = _has_unknown_tokens(tokens)
        return {
            "pipeline_verdict": "ill",
            "pipeline_wf": False,
            "failed_predicate": "parse_error",
            "feedback": "No candidates built — input outside analyser coverage.",
            "has_unknown_tokens": unknown,
            "num_candidates": 0,
            "elapsed_ms": elapsed_ms,
        }

    verifier = Verifier()
    result = verifier.verify_candidates(candidates)
    unknown = _has_unknown_tokens(tokens)

    return {
        "pipeline_verdict": "wf" if result.wf else "ill",
        "pipeline_wf": result.wf,
        "failed_predicate": result.failed_predicate or "—",
        "feedback": result.feedback or "",
        "has_unknown_tokens": unknown,
        "num_candidates": len(candidates),
        "elapsed_ms": elapsed_ms,
    }


# ── output columns ────────────────────────────────────────────────────────────
OUTPUT_FIELDS = [
    "theorem",
    "module",
    "section",
    "sentence",
    "expected_verdict",
    "expected_failing_predicate",
    "pipeline_verdict",
    "pipeline_failed_predicate",
    "result",           # PASS / FAIL
    "failure_category", # grammar_violation / coq_error / out_of_scope / dictionary_gap / —
    "has_unknown_tokens",
    "num_candidates",
    "elapsed_ms",
    "feedback",
    "notes",
]


def _result_label(expected: str, pipeline: str) -> str:
    return "PASS" if expected.strip().lower() == pipeline.strip().lower() else "FAIL"


def evaluate_csv(
    input_path: Path,
    output_path: Path,
    verbose: bool = False,
    filter_verdict: Optional[str] = None,
) -> list[dict]:
    """Read input_path, run every row, write output_path, return result rows."""
    rows_in: list[dict] = []
    with open(input_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows_in.append(row)

    rows_out: list[dict] = []
    total = len(rows_in)

    for i, row in enumerate(rows_in, 1):
        sentence   = row.get("sentence", "").strip()
        expected   = row.get("expected_verdict", "").strip().lower()
        theorem    = row.get("theorem", "").strip()
        module_    = row.get("module", "").strip()
        section    = row.get("section", "").strip()
        exp_pred   = row.get("expected_failing_predicate", "").strip()
        notes      = row.get("notes", "").strip()

        if not sentence:
            continue

        sys.stdout.write(f"\r[{i:>4}/{total}] {sentence[:60]:<60}")
        sys.stdout.flush()

        run = run_sentence(sentence)
        tokens = tokenize(sentence)

        pipeline_verdict = run["pipeline_verdict"]
        failed_pred      = run["failed_predicate"]
        result_label     = _result_label(expected, pipeline_verdict)

        if result_label == "FAIL" or pipeline_verdict == "ill":
            failure_cat = _classify_failure(failed_pred, tokens)
        else:
            failure_cat = CATEGORY_NONE

        out_row = {
            "theorem":                    theorem,
            "module":                     module_,
            "section":                    section,
            "sentence":                   sentence,
            "expected_verdict":           expected,
            "expected_failing_predicate": exp_pred,
            "pipeline_verdict":           pipeline_verdict,
            "pipeline_failed_predicate":  failed_pred,
            "result":                     result_label,
            "failure_category":           failure_cat,
            "has_unknown_tokens":         str(run["has_unknown_tokens"]),
            "num_candidates":             str(run["num_candidates"]),
            "elapsed_ms":                 str(run["elapsed_ms"]),
            "feedback":                   run["feedback"],
            "notes":                      notes,
        }
        rows_out.append(out_row)

        if verbose:
            if filter_verdict and pipeline_verdict != filter_verdict:
                continue
            _print_row(out_row)

    sys.stdout.write("\r" + " " * 80 + "\r")  # clear progress line

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows_out)

    return rows_out


def _print_row(row: dict) -> None:
    result_icon = "✓" if row["result"] == "PASS" else "✗"
    cat = row["failure_category"]
    cat_str = f"  [{cat}]" if cat != CATEGORY_NONE else ""
    print(
        f"{result_icon} [{row['result']}] {row['theorem']}\n"
        f"  sentence : {row['sentence']}\n"
        f"  expected : {row['expected_verdict']}  "
        f"pipeline: {row['pipeline_verdict']}{cat_str}\n"
        f"  predicate: {row['pipeline_failed_predicate']}  "
        f"candidates: {row['num_candidates']}  "
        f"time: {row['elapsed_ms']} ms"
    )
    if row["feedback"]:
        print(f"  feedback : {row['feedback']}")
    print()


def _print_summary(rows: list[dict]) -> None:
    total      = len(rows)
    passed     = sum(1 for r in rows if r["result"] == "PASS")
    failed     = total - passed

    wf_correct = sum(1 for r in rows if r["expected_verdict"] == "wf"  and r["result"] == "PASS")
    ill_correct= sum(1 for r in rows if r["expected_verdict"] == "ill" and r["result"] == "PASS")
    wf_total   = sum(1 for r in rows if r["expected_verdict"] == "wf")
    ill_total  = sum(1 for r in rows if r["expected_verdict"] == "ill")

    cats = [CATEGORY_GRAMMAR, CATEGORY_DICT_GAP, CATEGORY_OUT_OF_SCOPE, CATEGORY_COQ_ERROR]
    cat_counts = {c: sum(1 for r in rows if r["failure_category"] == c) for c in cats}

    # Per-module breakdown
    modules = sorted({r["module"] for r in rows})
    mod_stats: dict[str, dict] = {}
    for m in modules:
        mod_rows = [r for r in rows if r["module"] == m]
        mod_stats[m] = {
            "total":  len(mod_rows),
            "passed": sum(1 for r in mod_rows if r["result"] == "PASS"),
        }

    bar_width = 40
    pct       = passed / total if total else 0
    bar_fill  = int(bar_width * pct)
    bar       = "█" * bar_fill + "░" * (bar_width - bar_fill)

    print("\n" + "═" * 60)
    print("  BENCHMARK SUMMARY")
    print("═" * 60)
    print(f"  Total cases : {total}")
    print(f"  PASS        : {passed}  ({100*pct:.1f}%)")
    print(f"  FAIL        : {failed}  ({100*(1-pct):.1f}%)")
    print(f"  [{bar}]")
    print()
    print(f"  WF cases    : {wf_correct}/{wf_total} correct")
    print(f"  ILL cases   : {ill_correct}/{ill_total} correct")
    print()
    print("  Failure categories (all ILL-verdict rows):")
    for c in cats:
        n = cat_counts[c]
        label = {
            CATEGORY_GRAMMAR:  "grammar_violation",
            CATEGORY_DICT_GAP: "dictionary_gap   ",
            CATEGORY_OUT_OF_SCOPE: "out_of_scope     ",
            CATEGORY_COQ_ERROR:    "coq_error        ",
        }[c]
        bar2 = "▪" * n
        print(f"    {label} : {n:>4}  {bar2}")
    print()
    print("  Per-module:")
    for m, st in mod_stats.items():
        pct_m = st["passed"] / st["total"] if st["total"] else 0
        print(f"    {m:<16} {st['passed']:>3}/{st['total']:<3}  ({100*pct_m:.0f}%)")
    print("═" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run_benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            Guaraní Grammar Benchmark Evaluator
            ────────────────────────────────────
            Runs each sentence in the CSV through the analyzer+verifier
            pipeline and classifies every outcome as:

              PASS             verdict matches expected
              FAIL             verdict differs from expected

            Failure categories (appear in every ILL-verdict row):
              grammar_violation  — a specific Coq predicate failed
              dictionary_gap     — an unknown token caused the failure
              out_of_scope       — no parse candidates could be built
              coq_error          — Coq engine returned an internal error
        """),
    )
    parser.add_argument(
        "--csv", "-i", default="data/guarani_benchmark.csv",
        metavar="PATH",
        help="Input benchmark CSV (default: guarani_benchmark.csv)",
    )
    parser.add_argument(
        "--out", "-o", default="benchmark_results.csv",
        metavar="PATH",
        help="Output results CSV (default: benchmark_results.csv)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print each row as it is evaluated",
    )
    parser.add_argument(
        "--filter", metavar="VERDICT", default=None,
        help="In verbose mode, only print rows with this pipeline verdict (wf/ill)",
    )
    parser.add_argument(
        "--no-summary", action="store_true",
        help="Suppress the summary table",
    )
    args = parser.parse_args()

    input_path  = Path(args.csv)
    output_path = Path(args.out)

    if not input_path.exists():
        # Try relative to script location
        alt = SCRIPT_DIR / input_path
        if alt.exists():
            input_path = alt
        else:
            sys.exit(f"ERROR: input CSV not found: {input_path}")

    print(f"Evaluating: {input_path}")
    print(f"Output  to: {output_path}")
    print()

    t_start = time.perf_counter()
    rows = evaluate_csv(
        input_path=input_path,
        output_path=output_path,
        verbose=args.verbose,
        filter_verdict=args.filter,
    )
    elapsed = time.perf_counter() - t_start

    if not args.no_summary:
        _print_summary(rows)

    print(f"\nResults written to: {output_path}")
    print(f"Total wall time   : {elapsed:.1f}s")


if __name__ == "__main__":
    main()
