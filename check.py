"""
check.py

CLI to test analyzer + Coq verifier end-to-end.

Usage:
    python check.py "ha'e omano"
"""

import sys
from guarani.analyzer import load_lexicon, load_noun_lexicon, analyze, analyze_np
from guarani.types import Sentence
from guarani.verifier import Verifier

LEXICON_CSV = "merged.csv"


def build_candidate_sentences(tokens: list[str]) -> list[Sentence]:
    """
    Naive 2-token SVO assembly: find the first token that parses as a verb,
    treat the other token(s) as subject NP candidates.
    """
    candidates: list[Sentence] = []

    for verb_idx, tok in enumerate(tokens):
        verb_parses = analyze(tok)
        if not verb_parses:
            continue

        subj_tokens = tokens[:verb_idx]
        obj_tokens = tokens[verb_idx + 1:]

        subj_candidates = []
        for st in subj_tokens:
            subj_candidates.extend(analyze_np(st))
        obj_candidates = []
        for ot in obj_tokens:
            obj_candidates.extend(analyze_np(ot))

        subj_list = [r.np for r in subj_candidates] or [None]
        obj_list = [r.np for r in obj_candidates] or [None]

        for vp in verb_parses:
            for s in subj_list:
                for o in obj_list:
                    candidates.append(Sentence(
                        verb=vp.conj_verb,
                        subject=s,
                        direct_obj=o,
                    ))

    return candidates


def main():
    if len(sys.argv) < 2:
        print("usage: python check.py <guarani sentence>", file=sys.stderr)
        sys.exit(2)

    load_lexicon(LEXICON_CSV)
    load_noun_lexicon(LEXICON_CSV)

    sentence = " ".join(sys.argv[1:])
    tokens = sentence.split()
    print(f"Sentence: {sentence}")

    candidates = build_candidate_sentences(tokens)
    print(f"Built {len(candidates)} candidate sentence(s).")

    verifier = Verifier()
    result = verifier.verify_candidates(candidates)

    print()
    print(f"Well-formed: {result.wf}")
    if result.failed_predicate:
        print(f"Failed predicate: {result.failed_predicate}")
    if result.feedback:
        print(f"Feedback: {result.feedback}")


if __name__ == "__main__":
    main()