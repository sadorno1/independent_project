"""
check.py

CLI utility to test the parser analyzer and Coq formal verification engine 
end-to-end on arbitrary Guaraní string sentences.
"""

import sys
from dataclasses import replace
from typing import Optional
from guarani.analyzer import (
    load_lexicon, load_noun_lexicon, load_adj_lexicon, load_neg_pron_lexicon,
    analyze, analyze_np_span,
    analyze_chendal_pair, analyze_prohibitive_pair, diagnose_verb_token, diagnose_chendal_pair,
    is_unknown_token, _nfc, _strip_postposition, _CHENDAL_MARKER_SURFACES,
)
from guarani.loop import (
    _best_np, tokenize, strip_piko, strip_evidential, sentence_type_for, word_order_for,
    _find_adv_boundaries, _strip_adv_enclitic, _is_known_adv_subordinator,
    build_nonverbal_candidates, _DATIVE_TOKENS,
)
from guarani.types import (
    Sentence, NP, Postposition, POSTPOSITION_FORM_INDEX,
    AdvClause, AdverbialSentence, ADV_SUBORDINATOR_FORM_INDEX, CoordinatedSentence,
    NonverbalSentence, Transitivity, WordOrder,
    VF_Regular,
)
from guarani.verifier import Verifier

LEXICON_CSV = "data/merged.csv"
load_lexicon(LEXICON_CSV)
load_noun_lexicon(LEXICON_CSV)
load_adj_lexicon(LEXICON_CSV)
load_neg_pron_lexicon(LEXICON_CSV)


def _np_candidates(span: list[str]) -> list[NP]:
    parsed = [r.np for r in analyze_np_span(span, 0) if r.num_consumed == len(span)]
    if parsed:
        return parsed
    best = _best_np(span)
    return [best] if best else []


def _postp_candidates(obj_span: list[str]) -> list[tuple[NP, Postposition]]:
    """Readings of the object span as NP + postposition ('ka'aguy pe' / 'ka'aguype')."""
    readings: list[tuple[list[str], list[Postposition]]] = []
    last = _nfc(obj_span[-1])

    pps = POSTPOSITION_FORM_INDEX.get(last)
    if pps and len(obj_span) > 1:
        readings.append((obj_span[:-1], pps))

    for remainder, pp in _strip_postposition(last):
        readings.append((obj_span[:-1] + [remainder], [pp]))

    candidates: list[tuple[NP, Postposition]] = []
    for np_tokens, pps in readings:
        for np in _np_candidates(np_tokens):
            for pp in pps:
                candidates.append((np, pp))
    return candidates


def _ditransitive_io_candidates(obj_span: list[str], verb_transitivity: Optional[Transitivity]) -> list[tuple[list[str], list[str]]]:
    """For Ditransitive verbs, finds every reading of obj_span as (direct-
    object tokens, indirect-object tokens): either a closed dative pronoun
    (chupe, ndéve, ...) or a full NP marked with the =pe/=me postposition
    fused onto one of its tokens — e.g. "amombe'u mitãme la noticia" ("I
    tell the child the news"). ss_indir_obj is typed as a plain
    option guarani_np in Coq (no postposition slot the way ss_postp_obj
    has), so the =pe/=me marking is purely a surface cue for which span to
    read as indirect_obj, not part of the resulting term — the postposition
    itself is stripped and discarded, same as the dative-pronoun case
    already discards "to/for" semantics into a plain NP."""
    if verb_transitivity != Transitivity.Ditransitive:
        return []
    splits: list[tuple[list[str], list[str]]] = []
    for i, tok in enumerate(obj_span):
        nfc_tok = _nfc(tok)
        remaining = obj_span[:i] + obj_span[i + 1:]
        if nfc_tok in _DATIVE_TOKENS:
            splits.append((remaining, [tok]))
        for remainder, pp in _strip_postposition(nfc_tok):
            if pp == Postposition.Post_Pe:
                splits.append((remaining, [remainder]))
        # Standalone postposition token ("mitã me", two words), mirroring
        # _postp_candidates' handling of postp_comp: the immediately
        # preceding token is the IO NP, this token is just the marker.
        if i > 0 and Postposition.Post_Pe in POSTPOSITION_FORM_INDEX.get(nfc_tok, []):
            splits.append((obj_span[:i - 1] + obj_span[i + 1:], [obj_span[i - 1]]))
    return splits


def build_candidate_sentences(tokens: list[str], enforce_orality: bool = True) -> list[Sentence]:
    """Partitions sentence tokens around a verb index to generate SVO candidate structures."""
    tokens, has_piko = strip_piko(tokens)
    tokens, evidential = strip_evidential(tokens)
    candidates: list[Sentence] = []

    for verb_idx, tok in enumerate(tokens):
        # Verb pivots: the token itself, a Chendal person marker written
        # separately from its predicate root ("che kane'o" = "chekane'o"),
        # or the prohibitive particle "ani" written separately ("ani reho").
        pivots = [(analyze(tok, enforce_orality=enforce_orality), verb_idx + 1)]
        if verb_idx + 1 < len(tokens):
            pivots.append((
                analyze_chendal_pair(tok, tokens[verb_idx + 1], enforce_orality=enforce_orality),
                verb_idx + 2,
            ))
            pivots.append((
                analyze_prohibitive_pair(tok, tokens[verb_idx + 1], enforce_orality=enforce_orality),
                verb_idx + 2,
            ))
        if evidential is not None:
            pivots = [
                ([replace(vp, conj_verb=replace(vp.conj_verb, evidential=evidential)) for vp in verb_parses], obj_start)
                for verb_parses, obj_start in pivots
            ]

        for verb_parses, obj_start in pivots:
            if not verb_parses:
                continue

            subj_span = tokens[:verb_idx]
            obj_span = tokens[obj_start:]
            hikuai = bool(obj_span) and _nfc(obj_span[0]) in ("hikuái", "hikuai")
            if hikuai:
                obj_span = obj_span[1:]

            subj_candidates: list[Optional[NP]] = _np_candidates(subj_span) if subj_span else [None]

            obj_candidates: list[Optional[NP]] = _np_candidates(obj_span) if obj_span else [None]
            postp_candidates = _postp_candidates(obj_span) if obj_span else []

            subj_idx = 0 if subj_span else None
            word_order = word_order_for(subj_idx, verb_idx, hikuai)

            for vp in verb_parses:
                verb_transitivity = (
                    vp.conj_verb.verb_form.verb.v_transitivity
                    if isinstance(vp.conj_verb.verb_form, VF_Regular) else None
                )
                io_splits = _ditransitive_io_candidates(obj_span, verb_transitivity) if obj_span else []

                for s in subj_candidates:
                    s_interrog = s is not None and s.interrog_pron is not None
                    # Ditransitive IO/DO splits are tried BEFORE the plain
                    # direct_obj fallback below: both can independently
                    # verify well-formed (ss_transitivity_ok accepts a
                    # Ditransitive verb with only a direct_obj too), and
                    # verify_candidates accepts the first well-formed
                    # candidate it finds — so the more specific, actually-
                    # correct IO/DO split needs to come first, or a
                    # same-span fallback that swallows the whole object
                    # span into one bogus NP can win the race instead.
                    for do_span, io_span in io_splits:
                        do_candidates: list[Optional[NP]] = _np_candidates(do_span) if do_span else [None]
                        for io in _np_candidates(io_span):
                            io_interrog = s_interrog or io.interrog_pron is not None
                            for do in do_candidates:
                                has_interrog_arg = io_interrog or (do is not None and do.interrog_pron is not None)
                                sent_type, interrog = sentence_type_for(vp.conj_verb, has_piko, has_interrog_arg)
                                candidates.append(Sentence(
                                    verb=vp.conj_verb,
                                    subject=s,
                                    direct_obj=do,
                                    indirect_obj=io,
                                    word_order=word_order,
                                    sent_type=sent_type,
                                    interrog=interrog,
                                    hikuai=hikuai,
                                ))
                    for o in obj_candidates:
                        has_interrog_arg = s_interrog or (o is not None and o.interrog_pron is not None)
                        sent_type, interrog = sentence_type_for(vp.conj_verb, has_piko, has_interrog_arg)
                        candidates.append(Sentence(
                            verb=vp.conj_verb,
                            subject=s,
                            direct_obj=o,
                            word_order=word_order,
                            sent_type=sent_type,
                            interrog=interrog,
                            hikuai=hikuai,
                        ))
                    for np, pp in postp_candidates:
                        has_interrog_arg = s_interrog or np.interrog_pron is not None
                        sent_type, interrog = sentence_type_for(vp.conj_verb, has_piko, has_interrog_arg)
                        candidates.append(Sentence(
                            verb=vp.conj_verb,
                            subject=s,
                            postp_comp=(np, pp),
                            word_order=word_order,
                            sent_type=sent_type,
                            interrog=interrog,
                            hikuai=hikuai,
                        ))

                # Fronted object: the pre-verb span read as a fronted direct
                # object with an omitted/pro-dropped subject (OSV), instead
                # of forcing it into subject position — e.g. "mba'eve
                # ndajapói" ("I don't do anything"): mba'eve is the object,
                # not the subject, of a verb whose 1sg prefix already
                # supplies the dropped "I". Only tried when nothing follows
                # the verb, so there's no separate obj_span reading to
                # conflict with (ss_dir_obj only has room for one NP).
                if subj_span and not obj_span:
                    for fronted_obj in subj_candidates:
                        has_interrog_arg = fronted_obj is not None and fronted_obj.interrog_pron is not None
                        sent_type, interrog = sentence_type_for(vp.conj_verb, has_piko, has_interrog_arg)
                        candidates.append(Sentence(
                            verb=vp.conj_verb,
                            direct_obj=fronted_obj,
                            word_order=WordOrder.WO_OSV,
                            sent_type=sent_type,
                            interrog=interrog,
                            hikuai=hikuai,
                        ))

                # Fronted object plus a trailing indirect object/adjunct
                # still after the verb — e.g. "la noticia amombe'u ndéve"
                # ("I tell you the news", noticia fronted, ndéve trailing
                # dative). Reuses io_splits, but only the splits whose
                # do_span is empty (obj_span is entirely consumed by the
                # IO marker, e.g. a bare dative pronoun or a single =pe/=me
                # -marked token) — a non-empty do_span there would be a
                # second, conflicting direct object competing with the
                # fronted one (ss_dir_obj only has room for one NP).
                # Transitive verbs get the analogous postp_comp version,
                # since ss_postp_obj is left free for them to hold a
                # locative/other adjunct alongside a direct object.
                if subj_span and obj_span:
                    for do_span, io_span in io_splits:
                        if do_span:
                            continue
                        for io in _np_candidates(io_span):
                            io_interrog = io.interrog_pron is not None
                            for fronted_obj in subj_candidates:
                                has_interrog_arg = io_interrog or (fronted_obj is not None and fronted_obj.interrog_pron is not None)
                                sent_type, interrog = sentence_type_for(vp.conj_verb, has_piko, has_interrog_arg)
                                candidates.append(Sentence(
                                    verb=vp.conj_verb,
                                    direct_obj=fronted_obj,
                                    indirect_obj=io,
                                    word_order=WordOrder.WO_OSV,
                                    sent_type=sent_type,
                                    interrog=interrog,
                                    hikuai=hikuai,
                                ))
                    if verb_transitivity == Transitivity.Transitive:
                        for np, pp in postp_candidates:
                            np_interrog = np.interrog_pron is not None
                            for fronted_obj in subj_candidates:
                                has_interrog_arg = np_interrog or (fronted_obj is not None and fronted_obj.interrog_pron is not None)
                                sent_type, interrog = sentence_type_for(vp.conj_verb, has_piko, has_interrog_arg)
                                candidates.append(Sentence(
                                    verb=vp.conj_verb,
                                    direct_obj=fronted_obj,
                                    postp_comp=(np, pp),
                                    word_order=WordOrder.WO_OSV,
                                    sent_type=sent_type,
                                    interrog=interrog,
                                    hikuai=hikuai,
                                ))

    return candidates


def _build_subordinate_candidates(sub_tokens: list[str], enforce_orality: bool = True) -> list[Sentence]:
    """Builds candidates for a subordinate clause: sub_tokens[0] is the clause's
    verb (immediately before the subordinator), sub_tokens[1:] its trailing
    argument. That argument is tried as either direct object or subject, since
    these clauses commonly place their sole argument after the verb regardless
    of its grammatical role (e.g. purposive 'ovy'a haguã mitã' = 'mitã' is the
    subject of intransitive 'ovy'a', not its object)."""
    if not sub_tokens:
        return []
    verb_parses = analyze(sub_tokens[0], enforce_orality=enforce_orality)
    if not verb_parses:
        return []
    arg_span = sub_tokens[1:]
    arg_candidates: list[Optional[NP]] = _np_candidates(arg_span) if arg_span else [None]

    candidates: list[Sentence] = []
    for vp in verb_parses:
        for arg in arg_candidates:
            has_interrog_arg = arg is not None and arg.interrog_pron is not None
            sent_type, interrog = sentence_type_for(vp.conj_verb, has_interrog_arg=has_interrog_arg)
            candidates.append(Sentence(verb=vp.conj_verb, direct_obj=arg, sent_type=sent_type, interrog=interrog))
            if arg is not None:
                candidates.append(Sentence(verb=vp.conj_verb, subject=arg, sent_type=sent_type, interrog=interrog))
    return candidates


def build_complex_candidates(tokens: list[str], enforce_orality: bool = True) -> list[AdverbialSentence]:
    """Builds CS_Adverbial candidates (main clause + subordinator + subordinate
    clause) for each detected free-standing subordinator boundary, trying both
    plausible word orders since it differs by subordinator and isn't otherwise
    resolvable from the surface form alone:

    - postposed (plain haguã, jave, aja, mboyve, ...): the subordinate clause's
      OWN verb sits immediately before the subordinator, with that verb's
      trailing argument (ambiguous subject/object) after it — 'aha aikuaa
      haguã ñe'ẽ pyahu' = main 'aha' + subordinate 'aikuaa ... ñe'ẽ pyahu'.
    - preposed (ani haguã, porque, ...): the subordinator sits cleanly between
      two ordinary clauses — 'oguata ani haguã ojaho'i' = main 'oguata' +
      subordinate 'ojaho'i'.

    A wrong-order split just fails to build a well-formed candidate (or fails
    to parse as a clause at all); verify_candidates picks whichever succeeds.
    """
    candidates: list[AdverbialSentence] = []
    for start, after, surface, ac_types in _find_adv_boundaries(tokens):
        # Which ac_type a shared morpheme resolves to doesn't affect
        # wf_adv_clause's truth value (it's a pure string match per type), so
        # any one compatible type is equivalent — no need to fan out.
        ac = AdvClause(ac_type=ac_types[0], ac_subord=surface)

        splits: list[tuple[list[str], list[str], bool]] = []
        if start >= 1 and tokens[:start - 1]:
            splits.append((tokens[:start - 1], [tokens[start - 1]] + tokens[after:], True))
        if tokens[:start] and tokens[after:]:
            splits.append((tokens[:start], tokens[after:], False))

        for main_tokens, sub_tokens, postposed in splits:
            main_candidates = build_candidate_sentences(main_tokens, enforce_orality=enforce_orality)
            if not main_candidates:
                continue
            sub_candidates = (
                _build_subordinate_candidates(sub_tokens, enforce_orality=enforce_orality) if postposed
                else build_candidate_sentences(sub_tokens, enforce_orality=enforce_orality)
            )
            if not sub_candidates:
                continue
            for m in main_candidates:
                for s in sub_candidates:
                    candidates.append(AdverbialSentence(main=m, ac=ac, subord=s))

    return candidates


def build_enclitic_complex_candidates(tokens: list[str], enforce_orality: bool = True) -> list[AdverbialSentence]:
    """Builds CS_Adverbial candidates from an enclitic fused onto the last
    token of one clause, with the other clause on the opposite side — tried in
    both orders (subordinate-first and subordinate-last), since Guaraní
    causal/conditional/temporal clauses attach these forms to whichever word
    ends the subordinate clause (verb or its final argument) and can appear on
    either side of the main clause; nothing in the surface form alone
    disambiguates it. As with build_complex_candidates, a wrong split just
    fails to produce a well-formed (or any) candidate."""
    candidates: list[AdverbialSentence] = []
    n = len(tokens)

    def _add(main_tokens: list[str], enclitic_tokens: list[str]) -> None:
        if not main_tokens or not enclitic_tokens:
            return
        for remainder, ac_type, surf in _strip_adv_enclitic(enclitic_tokens[-1]):
            sub_tokens = enclitic_tokens[:-1] + [remainder]
            sub_candidates = build_candidate_sentences(sub_tokens, enforce_orality=enforce_orality)
            if not sub_candidates:
                continue
            main_candidates = build_candidate_sentences(main_tokens, enforce_orality=enforce_orality)
            if not main_candidates:
                continue
            ac = AdvClause(ac_type=ac_type, ac_subord=surf)
            for m in main_candidates:
                for s in sub_candidates:
                    candidates.append(AdverbialSentence(main=m, ac=ac, subord=s))

    for k in range(1, n):
        left, right = tokens[:k], tokens[k:]
        _add(main_tokens=left, enclitic_tokens=right)   # main first, subordinate (enclitic) last
        _add(main_tokens=right, enclitic_tokens=left)   # subordinate (enclitic) first, main last

    return candidates


def build_coordinated_candidates(tokens: list[str], enforce_orality: bool = True) -> list[CoordinatedSentence]:
    """Builds CS_Coordinated candidates: two full clauses joined by a
    free-standing 'ha' ("and") token — e.g. "ajogua ha aheja" = "I buy and
    sell" (scope.md test #50). wf_complex stores no conjunction morpheme at
    all (just wf_sentence(s1) && wf_sentence(s2)), so every free-standing
    'ha' is tried as a split point."""
    candidates: list[CoordinatedSentence] = []
    for i, tok in enumerate(tokens):
        if _nfc(tok) != "ha":
            continue
        left_tokens, right_tokens = tokens[:i], tokens[i + 1:]
        if not left_tokens or not right_tokens:
            continue
        s1_candidates = build_candidate_sentences(left_tokens, enforce_orality=enforce_orality)
        s2_candidates = build_candidate_sentences(right_tokens, enforce_orality=enforce_orality)
        for s1 in s1_candidates:
            for s2 in s2_candidates:
                candidates.append(CoordinatedSentence(s1=s1, s2=s2))
    return candidates


def _describe_conj_verb(cv) -> str:
    vf = cv.verb_form
    if isinstance(vf, VF_Regular):
        v = vf.verb
        root_desc = (f"root='{v.v_root}' class={v.v_class.value} "
                     f"transitivity={v.v_transitivity.value} orality={v.v_orality.value}")
    else:
        root_desc = f"irregular={vf.irreg.value}"
    suffixes = ",".join(s.value for s in cv.suffixes) or "none"
    incl = cv.incl.value if cv.incl else "-"
    return (f"verb: {root_desc} person={cv.person.value} number={cv.number.value} "
            f"incl={incl} mood={cv.mood.value} polarity={cv.polarity.value} suffixes=[{suffixes}]")


def _describe_verb_parse(pr) -> str:
    """Human-readable summary of one analyze()/analyze_chendal_pair() ParseResult."""
    return f"verb parse: {_describe_conj_verb(pr.conj_verb)[len('verb: '):]} (confidence={pr.confidence})"


def _describe_np(np: NP) -> str:
    parts = [f"NP('{np.surface}')", f"person={np.person.value}", f"number={np.number.value}"]
    if np.pronoun is not None:
        parts.append(f"pronoun={np.pronoun.value}")
    if np.noun is not None:
        parts.append(f"noun='{np.noun.n_root}'(human={np.noun.n_human})")
    if np.possessor is not None:
        parts.append(f"possessor={np.possessor.value}")
    if np.demonstrative is not None:
        parts.append(f"demonstrative={np.demonstrative.value}")
    if np.adjective is not None:
        parts.append(f"adjective='{np.adjective.a_form}'")
    if np.neg_pron is not None:
        parts.append(f"neg_pron={np.neg_pron.value}")
    return " ".join(parts)


def _describe_np_parse(r) -> str:
    return f"NP parse: {_describe_np(r.np)} (confidence={r.confidence}, tokens_consumed={r.num_consumed})"


def _describe_token(tok: str) -> list[str]:
    """Every analysis the pipeline is able to derive for a single surface
    token, in isolation: candidate verb parses, candidate NP parses,
    postposition readings (standalone or fused), and subordinator readings
    (standalone or fused)."""
    nfc_tok = _nfc(tok)
    lines: list[str] = []

    for pr in analyze(tok):
        lines.append(_describe_verb_parse(pr))

    for r in analyze_np_span([tok], 0):
        lines.append(_describe_np_parse(r))

    pps = POSTPOSITION_FORM_INDEX.get(nfc_tok)
    if pps:
        lines.append(f"standalone postposition: {[p.value for p in pps]}")
    for remainder, pp in _strip_postposition(nfc_tok):
        lines.append(f"fused postposition: strips to NP '{remainder}' + {pp.value}")

    if nfc_tok in ADV_SUBORDINATOR_FORM_INDEX:
        lines.append(f"standalone subordinator: {[t.value for t in ADV_SUBORDINATOR_FORM_INDEX[nfc_tok]]}")
    for remainder, ac_type, surf in _strip_adv_enclitic(tok):
        lines.append(f"fused subordinator enclitic: strips '{surf}' -> remainder '{remainder}', type={ac_type.value}")

    if nfc_tok in _CHENDAL_MARKER_SURFACES:
        lines.append("chendal person marker: may combine with the following word as its predicate root")

    if not lines:
        notes = diagnose_verb_token(tok)
        if notes:
            lines.extend(f"! {n}" for n in notes)
        else:
            lines.append("(no recognized analysis for this token in isolation)")

    return lines


def _describe_sentence_roles(sentence: Sentence) -> list[str]:
    lines = [f"word_order={sentence.word_order.value} sent_type={sentence.sent_type.value} hikuai={sentence.hikuai}"]
    lines.append("subject: " + (_describe_np(sentence.subject) if sentence.subject else "(none / Ø)"))
    lines.append(_describe_conj_verb(sentence.verb))
    lines.append("direct_obj: " + (_describe_np(sentence.direct_obj) if sentence.direct_obj else "(none)"))
    if sentence.indirect_obj:
        lines.append("indirect_obj: " + _describe_np(sentence.indirect_obj))
    if sentence.postp_comp:
        np, pp = sentence.postp_comp
        lines.append(f"postp_comp: {_describe_np(np)} + {pp.value}")
    return lines


def _print_predicate_trace(verifier: Verifier, sentence: Sentence, label: str = "") -> None:
    for name, result in verifier.predicate_trace(sentence):
        status = "PASS" if result is True else ("FAIL" if result is False else "ERROR")
        print(f"  {label}[{name}] = {status}")


def _print_winning_candidate(verifier: Verifier, sentence) -> None:
    print("\n--- Winning/best-effort candidate structure ---")
    if isinstance(sentence, AdverbialSentence):
        print(f"Complex sentence: adverbial clause '{sentence.ac.ac_subord}' (type={sentence.ac.ac_type.value})")
        print("Main clause:")
        for line in _describe_sentence_roles(sentence.main):
            print("  " + line)
        print("Subordinate clause:")
        for line in _describe_sentence_roles(sentence.subord):
            print("  " + line)
        print("\n--- Predicate-by-predicate trace ---")
        print("Main clause:")
        _print_predicate_trace(verifier, sentence.main)
        print("Subordinate clause:")
        _print_predicate_trace(verifier, sentence.subord)
    elif isinstance(sentence, CoordinatedSentence):
        print("Complex sentence: coordinated (CS_Coordinated)")
        print("First clause:")
        for line in _describe_sentence_roles(sentence.s1):
            print("  " + line)
        print("Second clause:")
        for line in _describe_sentence_roles(sentence.s2):
            print("  " + line)
        print("\n--- Predicate-by-predicate trace ---")
        print("First clause:")
        _print_predicate_trace(verifier, sentence.s1)
        print("Second clause:")
        _print_predicate_trace(verifier, sentence.s2)
    elif isinstance(sentence, NonverbalSentence):
        print(f"Non-verbal sentence (no verb pivot, no factored predicate chain): {sentence.coq_term}")
    else:
        for line in _describe_sentence_roles(sentence):
            print(line)
        print("\n--- Predicate-by-predicate trace ---")
        _print_predicate_trace(verifier, sentence)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    argv = sys.argv[1:]
    verbose = False
    while "-v" in argv or "--verbose" in argv:
        if "-v" in argv:
            argv.remove("-v")
        if "--verbose" in argv:
            argv.remove("--verbose")
        verbose = True

    if not argv:
        print("usage: python check.py [-v|--verbose] <guarani sentence>", file=sys.stderr)
        sys.exit(2)

    sentence = " ".join(argv)
    tokens = tokenize(sentence)
    print(f"Sentence: {sentence}")

    if verbose:
        print("\n--- Token analysis ---")
        for i, tok in enumerate(tokens):
            print(f"[{i}] '{tok}':")
            for line in _describe_token(tok):
                print("  " + line)

    candidates: list = build_candidate_sentences(tokens)
    candidates += build_complex_candidates(tokens)
    candidates += build_enclitic_complex_candidates(tokens)
    candidates += build_coordinated_candidates(tokens)
    candidates += build_nonverbal_candidates(tokens)
    print(f"\nBuilt {len(candidates)} candidate sentence(s).")

    token_notes: list[str] = []
    for tok in tokens:
        for note in diagnose_verb_token(tok):
            if note not in token_notes:
                token_notes.append(note)
    for i in range(len(tokens) - 1):
        if _nfc(tokens[i]) in _CHENDAL_MARKER_SURFACES:
            for note in diagnose_chendal_pair(tokens[i], tokens[i + 1]):
                if note not in token_notes:
                    token_notes.append(note)

    if not candidates:
        print(f"\nWell-formed: False")
        print(f"Failed predicate: parse_error")
        if token_notes:
            print("Feedback: " + " ".join(token_notes))
        else:
            print("Feedback: No token could be analyzed as a conjugated verb.")
        return

    verifier = Verifier()
    result = verifier.verify_candidates(candidates)

    if verbose and result.sentence is not None and result.failed_predicate != "COQ_ERROR":
        _print_winning_candidate(verifier, result.sentence)

    print(f"\nWell-formed: {result.wf}")
    if result.failed_predicate:
        print(f"Failed predicate: {result.failed_predicate}")
    if result.feedback:
        print(f"Feedback: {result.feedback}")
    if not result.wf:
        for note in token_notes:
            print(f"Hint: {note}")
    else:
        for tok in tokens:
            if _nfc(tok) in ("ani", "piko"):
                continue
            if is_unknown_token(tok) and not _is_known_adv_subordinator(tok):
                print(f"Note: '{_nfc(tok)}' is not in the dictionary; it was treated as an unanalyzed noun.")


if __name__ == "__main__":
    main()