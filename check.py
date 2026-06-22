"""
check.py

CLI utility to test the parser analyzer and Coq formal verification engine 
end-to-end on arbitrary Guaraní string sentences.
"""

import sys
from typing import Optional
from guarani.analyzer import load_lexicon, load_noun_lexicon, analyze, analyze_np_span, load_adj_lexicon
from guarani.types import Sentence, NP
from guarani.verifier import Verifier

LEXICON_CSV = "data/merged.csv"
load_lexicon(LEXICON_CSV)
load_noun_lexicon(LEXICON_CSV)
load_adj_lexicon(LEXICON_CSV)


def build_candidate_sentences(tokens: list[str]) -> list[Sentence]:
    """Partitions sentence tokens around a verb index to generate SVO candidate structures."""
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

    print(f"\nWell-formed: {result.wf}")
    if result.failed_predicate:
        print(f"Failed predicate: {result.failed_predicate}")
    if result.feedback:
        print(f"Feedback: {result.feedback}")


if __name__ == "__main__":
    main()