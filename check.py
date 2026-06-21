"""
check.py

CLI to test analyzer + Coq verifier end-to-end.

Usage:
    python check.py "ha'e omano"
"""

import sys
from typing import Optional
from guarani.analyzer import load_lexicon, load_noun_lexicon, analyze, analyze_np_span, load_adj_lexicon
from guarani.types import Sentence, NP
from guarani.verifier import Verifier

LEXICON_CSV = "merged.csv"
load_lexicon(LEXICON_CSV)
load_noun_lexicon(LEXICON_CSV)
load_adj_lexicon(LEXICON_CSV)


def build_candidate_sentences(tokens: list[str]) -> list[Sentence]:
    """
    SVO assembly with multi-token NP spans.
    For each token position that parses as a verb, partition the
    remaining tokens into a subject span (before) and object span
    (after). Each span must be fully consumed by one or more NPs
    (currently just one NP per span — multi-NP spans deferred).
    Each non-verb token must be accounted for.
    """
    candidates: list[Sentence] = []

    for verb_idx, tok in enumerate(tokens):
        verb_parses = analyze(tok)
        if not verb_parses:
            continue

        subj_span = tokens[:verb_idx]
        obj_span = tokens[verb_idx + 1:]

        if not subj_span:
            subj_candidates: list[Optional[NP]] = [None]
        else:
            subj_candidates = [
                r.np for r in analyze_np_span(subj_span, 0)
                if r.num_consumed == len(subj_span)
            ]
            if not subj_candidates:
                continue

        if not obj_span:
            obj_candidates: list[Optional[NP]] = [None]
        else:
            obj_candidates = [
                r.np for r in analyze_np_span(obj_span, 0)
                if r.num_consumed == len(obj_span)
            ]
            if not obj_candidates:
                continue

        for vp in verb_parses:
            for s in subj_candidates:
                for o in obj_candidates:
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