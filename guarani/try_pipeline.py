"""
try_pipeline.py

Interactive REPL: type a Spanish sentence, see it go through the full
translate -> parse -> Coq-verify -> auto-correct loop, with every
iteration printed.

Usage (run from the project root):
    python -m guarani.try_pipeline
    python -m guarani.try_pipeline --model gemini-3.1-pro-preview
"""

import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from guarani.loop import load_all_lexicons, run_eval_sentence, LLM_REGISTRY
from guarani.verifier import Verifier

logging.basicConfig(level=logging.WARNING)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Interactively test the Spanish->Guarani pipeline")
    parser.add_argument("--model", default="gemini-3.6-flash",
                         help=f"Model to use. Available: {list(LLM_REGISTRY)}")
    parser.add_argument("--max-iterations", type=int, default=3)
    args = parser.parse_args()

    if args.model not in LLM_REGISTRY:
        sys.exit(f"Unknown model '{args.model}'. Available: {list(LLM_REGISTRY)}")

    load_all_lexicons()
    verifier = Verifier()
    llm_fn = LLM_REGISTRY[args.model]()

    print(f"Loaded model: {args.model}")
    print("Type a Spanish sentence and press Enter (Ctrl+C or empty line to quit).\n")

    while True:
        try:
            spanish = input("es> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not spanish:
            break

        result = run_eval_sentence(
            spanish_sentence=spanish,
            llm_fn=llm_fn,
            model_name=args.model,
            verifier=verifier,
            max_iterations=args.max_iterations,
        )

        for rec in result.iteration_records:
            status = "PARSE_ERROR" if rec.parse_error else ("WF" if rec.wf else f"FAIL:{rec.failed_predicate}")
            print(f"  [{rec.iteration}] {rec.guarani_output!r} -> {status}")
            if rec.feedback:
                print(f"      feedback: {rec.feedback}")

        print(f"Accepted: {result.accepted}  Final: {result.final_output!r}\n")


if __name__ == "__main__":
    main()
