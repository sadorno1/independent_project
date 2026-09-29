"""
loop.py

Orchestrates an LLM execution loop that feeds generations through the morph
analyzer and Coq verifier, sending programmatic feedback back for automatic
correction.

Now supports:
- Multiple LLM backends (DeepSeek, Google Gemini)
- Batch evaluation over lists of Spanish source sentences
- Richer logging: source sentence, per-iteration predicate history, convergence flag
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .analyzer import (
    load_lexicon, load_noun_lexicon, load_adj_lexicon, analyze, analyze_np_span,
    analyze_chendal_pair, analyze_prohibitive_pair, ParseResult, NPParseResult,
    _nfc, _strip_postposition,
)
from .coq_context import load_coq_context
from .types import (
    Sentence, ConjugatedVerb, NP, Person, Number, WordOrder, SentenceType,
    Orality, Noun, RootClass, word_ending_of, VerbalSuffix, VF_Regular,
    Transitivity, Postposition, POSTPOSITION_FORM_INDEX,
    SUBJ_PRONOUN_FORM_INDEX, _SUBJ_PRONOUN_PERSON, _SUBJ_PRONOUN_NUMBER,
    Mood, InterrogParticle, AdvClause, AdvClauseType, AdverbialSentence,
    ADV_SUBORDINATOR_FORM_INDEX, ADV_ENCLITIC_STRIP_INDEX, CoordinatedSentence,
    NonverbalSentence, Evidential, EVIDENTIAL_FORM_INDEX,
)
from .verifier import Verifier, VerifierResult

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3

TRANSLATION_PROMPT_TEMPLATE = """\
Translate the following Spanish sentence into Guaraní. Output only the Guaraní \
translation, nothing else.

Spanish: {spanish}
"""

CORRECTION_PROMPT_TEMPLATE = """\
The following Guaraní sentence has a grammatical error:

  sentence: {sentence}

Error: {feedback}

Please produce a corrected version of the sentence. Output only the corrected \
Guaraní sentence, nothing else.
"""

# Prepended to the translation prompt when context_mode == "coq" (condition
# B/C in the context-mode ablation). Not repeated on correction turns: each
# llm_fn call is a stateless single-shot completion (no chat history), so the
# grammar block only ever primes the initial translation attempt.
CONTEXT_PROMPT_PREFIX_TEMPLATE = """\
You are a Spanish-to-Guaraní translator.

The following Coq definitions specify the formal grammar for well-formed Guaraní.
Use them to guide your translation:

<coq_grammar>
{coq_context}
</coq_grammar>

"""

_MD_STRIP_RE = re.compile(r'^[\s*_>#\-\d.)]+|[\s*_]+$')


def _sanitize_llm_output(text: str) -> str:
    """Best-effort extraction of a bare sentence from an LLM response that
    ignored the "output only the sentence" instruction — models sometimes
    wrap the answer in a markdown explanation, bullet list, or code fence.
    Takes the first non-empty line and strips markdown decoration/quotes
    from it, since a full essay can't be tokenized as a candidate sentence
    anyway."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if "\n" in text and text.split("\n", 1)[0].strip().isalpha():
                text = text.split("\n", 1)[1]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return text
    line = _MD_STRIP_RE.sub("", lines[0])
    return line.strip(' "\'')


_DEFAULT_LEXICON = Path(__file__).parent.parent / "data" / "merged.csv"
_DEFAULT_COQ_DIR = Path(__file__).parent.parent / "rocq"

# ---------------------------------------------------------------------------
# One-time lexicon loading
# ---------------------------------------------------------------------------

_LEXICONS_LOADED = False


def load_all_lexicons(lexicon_csv: str | Path = _DEFAULT_LEXICON) -> None:
    """Load all lexicons once at process startup. Safe to call multiple times
    (subsequent calls are no-ops). Call this before any batch evaluation."""
    global _LEXICONS_LOADED
    if _LEXICONS_LOADED:
        return
    load_lexicon(lexicon_csv)
    load_noun_lexicon(lexicon_csv)
    load_adj_lexicon(lexicon_csv)
    _LEXICONS_LOADED = True
    logger.info("Lexicons loaded from %s", lexicon_csv)


# ---------------------------------------------------------------------------
# One-time Coq grammar context loading (context_mode == "coq")
# ---------------------------------------------------------------------------

_COQ_CONTEXT_CACHE: dict[str, str] = {}


def load_coq_context_once(coq_dir: str | Path = _DEFAULT_COQ_DIR) -> str:
    """Loads and extracts the Coq grammar context once per coq_dir, caching
    the result (mirrors the one-time lexicon loading pattern above). Call
    this before any batch evaluation run with context_mode == "coq"."""
    key = str(coq_dir)
    if key not in _COQ_CONTEXT_CACHE:
        _COQ_CONTEXT_CACHE[key] = load_coq_context(key)
        logger.info("Coq grammar context loaded from %s", coq_dir)
    return _COQ_CONTEXT_CACHE[key]


# ===========================================================================
# LLM Backends
# ===========================================================================

def make_deepseek_fn(
    model: str = "deepseek-chat",
    max_tokens: int = 512,
    temperature: float = 0.3,
) -> Callable[[str], str]:
    """Returns an llm_fn backed by the DeepSeek API (OpenAI-compatible)."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install openai")

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
    )

    def fn(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    fn.__name__ = f"deepseek/{model}"
    return fn


def make_gemini_fn(
    model: str = "gemini-3.6-flash",
    max_tokens: int = 512,
    temperature: float = 0.3,
) -> Callable[[str], str]:
    """Returns an llm_fn backed by the Google Gemini API.
    Requires: pip install google-generativeai
    Set GEMINI_API_KEY in your environment."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("pip install google-generativeai")

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    generation_config = genai.GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
    )
    client = genai.GenerativeModel(model, generation_config=generation_config)

    def fn(prompt: str) -> str:
        response = client.generate_content(prompt)
        return response.text.strip()

    fn.__name__ = f"gemini/{model}"
    return fn


# Convenience registry: name → factory function
LLM_REGISTRY: dict[str, Callable[[], Callable[[str], str]]] = {
    # DeepSeek
    "deepseek-chat":      lambda: make_deepseek_fn("deepseek-chat"),
    "deepseek-reasoner":  lambda: make_deepseek_fn("deepseek-reasoner"),
    # Google Gemini
    "gemini-3.6-flash":   lambda: make_gemini_fn("gemini-3.6-flash"),  # faster/cheaper
    "gemini-3.1-pro-preview": lambda: make_gemini_fn("gemini-3.1-pro-preview"),
}


# ===========================================================================
# Structural Extraction & AST Generator (unchanged from original)
# ===========================================================================

_DATIVE_TOKENS = frozenset([
    "ndéve", "chéve", "ichupe", "ñandéve", "oréve", "péve", "ichupekuéra",
    "ndeve", "cheve", "ñandeve", "oreve", "peve",
])

_EDGE_PUNCT = ".,;:!?¡¿\"""()[]{}…"


def tokenize(text: str) -> list[str]:
    return [t for t in (tok.strip(_EDGE_PUNCT) for tok in text.strip().split()) if t]


def _fallback_np(tokens: list[str]) -> NP:
    surface = " ".join(tokens)
    tok0 = tokens[0].strip().lower()
    pronoun = SUBJ_PRONOUN_FORM_INDEX.get(tok0)
    if pronoun is not None:
        return NP(
            surface=surface,
            person=_SUBJ_PRONOUN_PERSON[pronoun],
            number=_SUBJ_PRONOUN_NUMBER[pronoun],
            pronoun=pronoun,
        )
    is_nasal = any(c in surface for c in "ãẽĩõũỹñ")
    is_plural = any(t.lower() in ("hikuái", "hikuai", "kuéra", "kuera") for t in tokens)
    noun = Noun(
        n_root=tok0,
        n_orality=Orality.Nasal if is_nasal else Orality.Oral,
        n_ending=word_ending_of(tok0),
        n_root_class=RootClass.Uniform,
        n_human=False,
    )
    return NP(
        surface=surface,
        person=Person.Third,
        number=Number.Plural if is_plural else Number.Singular,
        noun=noun,
    )


def strip_piko(tokens: list[str]) -> tuple[list[str], bool]:
    has_piko = any(_nfc(t) == "piko" for t in tokens)
    if not has_piko:
        return tokens, False
    return [t for t in tokens if _nfc(t) != "piko"], True


def strip_evidential(tokens: list[str]) -> tuple[list[str], Optional[Evidential]]:
    """Evidential clitics (kuri, niko, ndaje, ra'e, ...) have free distribution
    in the clause (verb.v §7's own comment), so — like strip_piko above — this
    scans the whole token list rather than assuming a fixed position relative
    to the verb. Returns at most one match (the first found); the Coq grammar
    only gives conjugated_verb a single optional cv_evidential field, so a
    sentence can't represent more than one anyway.

    Bare "ko" is a special case: it's also the demonstrative adjective marker
    (e.g. "ko karai" = "this man", always prenominal — see DEM_ADJ_FORM_INDEX
    in types.py), indistinguishable from the niko-variant evidential "ko" by
    surface form alone. Since a demonstrative always has a noun after it, "ko"
    is only trusted as evidential when it's the last token — matching the
    benchmark's own "oho ko" (wf) vs. "ko karai" (demonstrative) expectations."""
    for i, tok in enumerate(tokens):
        norm = _nfc(tok)
        ev = EVIDENTIAL_FORM_INDEX.get(norm)
        if ev is None:
            continue
        if norm == "ko" and i != len(tokens) - 1:
            continue
        return tokens[:i] + tokens[i + 1:], ev
    return tokens, None


def sentence_type_for(
    cv: ConjugatedVerb, has_piko: bool = False, has_interrog_arg: bool = False,
) -> tuple[SentenceType, Optional["InterrogParticle"]]:
    if cv.mood == Mood.Prohibitive:
        return SentenceType.ST_Prohibitive, None
    if cv.mood in (Mood.Imperative, Mood.Optative):
        return SentenceType.ST_Imperative, None
    if VerbalSuffix.VS_InterrogPa in cv.suffixes:
        return SentenceType.ST_Interrog_YN, InterrogParticle.IntP_Pa
    if has_piko:
        return SentenceType.ST_Interrog_YN, InterrogParticle.IntP_Piko
    if has_interrog_arg:
        return SentenceType.ST_Interrog_Content, None
    return SentenceType.ST_Declarative, None


def word_order_for(subj_idx: Optional[int], verb_idx: int, hikuai: bool) -> WordOrder:
    if subj_idx is not None and subj_idx < verb_idx:
        return WordOrder.WO_SVO
    if hikuai:
        return WordOrder.WO_VSO
    return WordOrder.WO_SVO


def _best_np_sort_key(r: NPParseResult) -> tuple[int, int]:
    # exact_pronoun always wins; rel_clause/comp_clause next — a token that
    # verb-analyzes with a -va/-ha nominalizer suffix is a much stronger,
    # more specific signal than a same-length generic noun-noun reading
    # (e.g. analyzer.py's gen_noun fallback, which will happily treat any
    # unrecognized second token as a possessed noun), so it should win ties
    # on num_consumed against a generic reading rather than lose them just
    # by being appended later in _np_span's candidate list.
    if r.confidence == "exact_pronoun":
        tier = 0
    elif r.confidence in ("rel_clause", "comp_clause"):
        tier = 1
    else:
        tier = 2
    return (tier, -r.num_consumed)


def _best_np(tokens: list[str]) -> Optional[NP]:
    if not tokens:
        return None
    results = _np_span(tokens, 0)
    if results:
        results.sort(key=_best_np_sort_key)
        return results[0].np
    return _fallback_np(tokens)


def _trailing_postposition(tokens: list[str]) -> Optional[tuple[Optional[NP], Postposition]]:
    last = _nfc(tokens[-1])
    pps = POSTPOSITION_FORM_INDEX.get(last)
    if pps and len(tokens) > 1:
        return _best_np(tokens[:-1]), pps[0]
    stripped = _strip_postposition(last)
    if stripped:
        remainder, pp = stripped[0]
        return _best_np(tokens[:-1] + [remainder]), pp
    return None


def _find_verb_pivot(tokens: list[str]) -> Optional[tuple[ParseResult, int, int]]:
    for i, token in enumerate(tokens):
        parses = analyze(token)
        length = 1
        if not parses and i + 1 < len(tokens):
            parses = analyze_chendal_pair(token, tokens[i + 1])
            length = 2
        if not parses and i + 1 < len(tokens):
            parses = analyze_prohibitive_pair(token, tokens[i + 1])
            length = 2
        if parses:
            parses.sort(key=lambda p: 0 if p.confidence == "exact_irreg" else 1)
            return parses[0], i, length
    return None


def build_sentence(tokens: list[str]) -> Optional[Sentence]:
    tokens, has_piko = strip_piko(tokens)
    tokens, evidential = strip_evidential(tokens)
    pivot = _find_verb_pivot(tokens)
    if pivot is None:
        logger.warning("No verb parse found in tokens: %s", tokens)
        return None
    verb_parse, verb_idx, verb_len = pivot
    cv = verb_parse.conj_verb
    if evidential is not None:
        cv = replace(cv, evidential=evidential)
    post_verb = tokens[verb_idx + verb_len:]
    hikuai = bool(post_verb) and post_verb[0].lower() in ("hikuái", "hikuai")
    obj_tokens = post_verb[1:] if hikuai else post_verb
    subject = _best_np(tokens[:verb_idx])
    subj_idx = 0 if (verb_idx > 0 and subject is not None) else None
    word_order = word_order_for(subj_idx, verb_idx, hikuai)
    direct_obj: Optional[NP] = None
    indirect_obj: Optional[NP] = None
    postp_comp: Optional[tuple[NP, Postposition]] = None
    verb_transitivity = (
        cv.verb_form.verb.v_transitivity if isinstance(cv.verb_form, VF_Regular) else None
    )
    if obj_tokens:
        dative_idx = next(
            (i for i, t in enumerate(obj_tokens) if t.lower() in _DATIVE_TOKENS), -1
        )
        if dative_idx >= 0:
            direct_obj = _best_np(obj_tokens[:dative_idx]) if dative_idx > 0 else None
            indirect_obj = _best_np(obj_tokens[dative_idx:])
        else:
            io_np_tokens: Optional[list[str]] = None
            io_consumed: set[int] = set()
            if verb_transitivity == Transitivity.Ditransitive:
                for i, t in enumerate(obj_tokens):
                    nfc_t = _nfc(t)
                    fused = next((rem for rem, pp in _strip_postposition(nfc_t) if pp == Postposition.Post_Pe), None)
                    if fused is not None:
                        io_np_tokens, io_consumed = [fused], {i}
                        break
                    if i > 0 and Postposition.Post_Pe in POSTPOSITION_FORM_INDEX.get(nfc_t, []):
                        io_np_tokens, io_consumed = [obj_tokens[i - 1]], {i - 1, i}
                        break
            if io_np_tokens is not None:
                indirect_obj = _best_np(io_np_tokens)
                remaining = [t for j, t in enumerate(obj_tokens) if j not in io_consumed]
                direct_obj = _best_np(remaining) if remaining else None
            else:
                postp = (
                    _trailing_postposition(obj_tokens)
                    if verb_transitivity in (Transitivity.Intransitive, Transitivity.PostpComplement)
                    else None
                )
                if postp is not None and postp[0] is not None:
                    postp_comp = postp
                else:
                    direct_obj = _best_np(obj_tokens)
    has_interrog_arg = any(
        np is not None and np.interrog_pron is not None
        for np in (subject, direct_obj, indirect_obj)
    )
    sent_type, interrog = sentence_type_for(cv, has_piko, has_interrog_arg)
    return Sentence(
        verb=cv, subject=subject, direct_obj=direct_obj, indirect_obj=indirect_obj,
        postp_comp=postp_comp, word_order=word_order, sent_type=sent_type,
        interrog=interrog, hikuai=hikuai,
    )


def build_fronted_object_sentence(tokens: list[str]) -> Optional[Sentence]:
    tokens, has_piko = strip_piko(tokens)
    tokens, evidential = strip_evidential(tokens)
    pivot = _find_verb_pivot(tokens)
    if pivot is None:
        return None
    verb_parse, verb_idx, verb_len = pivot
    if verb_idx == 0:
        return None
    cv = verb_parse.conj_verb
    if evidential is not None:
        cv = replace(cv, evidential=evidential)
    fronted_obj = _best_np(tokens[:verb_idx])
    post_verb = tokens[verb_idx + verb_len:]
    indirect_obj: Optional[NP] = None
    if post_verb:
        verb_transitivity = (
            cv.verb_form.verb.v_transitivity if isinstance(cv.verb_form, VF_Regular) else None
        )
        if verb_transitivity != Transitivity.Ditransitive:
            return None
        if len(post_verb) == 1 and _nfc(post_verb[0]) in _DATIVE_TOKENS:
            indirect_obj = _best_np(post_verb)
        elif len(post_verb) == 1:
            fused = next((rem for rem, pp in _strip_postposition(_nfc(post_verb[0])) if pp == Postposition.Post_Pe), None)
            if fused is not None:
                indirect_obj = _best_np([fused])
        elif len(post_verb) == 2 and Postposition.Post_Pe in POSTPOSITION_FORM_INDEX.get(_nfc(post_verb[1]), []):
            indirect_obj = _best_np([post_verb[0]])
        if indirect_obj is None:
            return None
    has_interrog_arg = (
        (fronted_obj is not None and fronted_obj.interrog_pron is not None)
        or (indirect_obj is not None and indirect_obj.interrog_pron is not None)
    )
    sent_type, interrog = sentence_type_for(cv, has_piko, has_interrog_arg)
    return Sentence(
        verb=cv, direct_obj=fronted_obj, indirect_obj=indirect_obj,
        word_order=WordOrder.WO_OSV, sent_type=sent_type, interrog=interrog,
    )


_DEACCENT = str.maketrans("áéíóú", "aeiou")


def _deaccent(s: str) -> str:
    return s.translate(_DEACCENT)


def _analyze_nominalized_verb(token: str, suffix: VerbalSuffix) -> list[ConjugatedVerb]:
    """Best-effort support for NP_Rel/NP_Comp (rocq/noun_phrases.v): a relative
    clause is a verb carrying the -va nominalizer (VS_NomVa), a complement
    clause the -ha nominalizer (VS_NomHa). analyze() only matches verb forms
    already in its own suffix tables, which don't cover these two, so this
    strips the nominalizer surface here instead (trying both the accented
    remainder and its deaccented form, since e.g. "oiko" + "va" surfaces as
    "oikóva" — the stress shifts onto the new final syllable), re-parses the
    bare stem with the existing analyze(), and reattaches the nominalizer
    suffix to whatever ConjugatedVerb comes back."""
    surf = suffix.surface
    if not isinstance(surf, str):
        return []
    t = _nfc(token)
    if not t.endswith(surf) or len(t) <= len(surf):
        return []
    stem = t[: -len(surf)]
    candidates = [stem]
    deaccented = _deaccent(stem)
    if deaccented != stem:
        candidates.append(deaccented)

    out: list[ConjugatedVerb] = []
    seen: set[str] = set()
    for candidate in candidates:
        for parse in analyze(candidate):
            cv = parse.conj_verb
            if suffix in cv.suffixes:
                continue
            key = cv.to_coq()
            if key in seen:
                continue
            seen.add(key)
            out.append(replace(cv, suffixes=cv.suffixes + [suffix]))
    return out


def _rel_comp_np_candidates(tokens: list[str], start: int) -> list[NPParseResult]:
    """NP_Rel/NP_Comp candidates at position `start` — analyzer.py's own
    analyze_np_span() already has a code path for these two constructors, but
    it can never fire because analyze() can't parse -va/-ha nominalized verb
    forms (see _analyze_nominalized_verb). This rebuilds the same NP_Rel/
    NP_Comp coq_term construction here instead, without touching analyzer.py.
    Note: rocq/noun_phrases.v defines `embedded_clause := conjugated_verb` —
    the relativized/complement verb alone, with no argument slot of its own —
    so this only covers relative/complement clauses with no internal object
    or oblique complement (e.g. "kuimba'e oikóva" = "the man who lives", but
    not "the man who lives in the big house"); that's a limit of the Coq
    grammar itself, not something fixable from loop.py."""
    results: list[NPParseResult] = []

    # NP_Comp: a bare verb carrying -ha, e.g. "oguatáha" = "the act of walking".
    for cv in _analyze_nominalized_verb(tokens[start], VerbalSuffix.VS_NomHa):
        np = NP(
            surface=tokens[start], person=Person.Third, number=Number.Singular,
            human=False, coq_term=f"(NP_Comp {cv.to_coq()})",
        )
        results.append(NPParseResult(np=np, confidence="comp_clause", num_consumed=1))

    # NP_Rel: head noun + a verb carrying -va, e.g. "kuimba'e oikóva" = "the
    # man who lives".
    if start + 1 < len(tokens):
        head = _best_np([tokens[start]])
        if head is not None and head.noun is not None:
            for cv in _analyze_nominalized_verb(tokens[start + 1], VerbalSuffix.VS_NomVa):
                np = NP(
                    surface=f"{tokens[start]} {tokens[start + 1]}", person=Person.Third,
                    number=Number.Singular, human=head.noun.n_human,
                    coq_term=f"(NP_Rel {head.noun.to_coq()} {cv.to_coq()})",
                )
                results.append(NPParseResult(np=np, confidence="rel_clause", num_consumed=2))

    return results


def _np_span(tokens: list[str], start: int) -> list[NPParseResult]:
    """analyze_np_span() plus the NP_Rel/NP_Comp candidates it can't produce
    (see _rel_comp_np_candidates)."""
    return analyze_np_span(tokens, start) + _rel_comp_np_candidates(tokens, start)


def _strip_adv_enclitic(token: str) -> list[tuple[str, "AdvClauseType", str]]:
    t = _nfc(token)
    out = []
    for surf, ac_type in ADV_ENCLITIC_STRIP_INDEX:
        if t.endswith(surf) and len(t) > len(surf):
            remainder = t[:-len(surf)]
            out.append((remainder, ac_type, surf))
            deaccented = _deaccent(remainder)
            if deaccented != remainder:
                out.append((deaccented, ac_type, surf))
    return out


def _is_known_adv_subordinator(tok: str) -> bool:
    return _nfc(tok) in ADV_SUBORDINATOR_FORM_INDEX or bool(_strip_adv_enclitic(tok))


def _find_adv_boundaries(tokens: list[str]) -> list[tuple[int, int, str, list]]:
    boundaries = []
    n = len(tokens)
    j = 1
    while j < n:
        if j + 1 < n:
            two = f"{_nfc(tokens[j])} {_nfc(tokens[j + 1])}"
            two_types = ADV_SUBORDINATOR_FORM_INDEX.get(two)
            if two_types:
                boundaries.append((j, j + 2, two, two_types))
                j += 2
                continue
        one = _nfc(tokens[j])
        one_types = ADV_SUBORDINATOR_FORM_INDEX.get(one)
        if one_types:
            boundaries.append((j, j + 1, one, one_types))
        j += 1
    return boundaries


def _build_subordinate_sentence(sub_tokens: list[str]) -> Optional[Sentence]:
    if not sub_tokens:
        return None
    verb_parses = analyze(sub_tokens[0])
    if not verb_parses:
        return None
    verb_parses.sort(key=lambda p: 0 if p.confidence == "exact_irreg" else 1)
    cv = verb_parses[0].conj_verb
    arg_tokens = sub_tokens[1:]
    arg = _best_np(arg_tokens) if arg_tokens else None
    has_interrog_arg = arg is not None and arg.interrog_pron is not None
    sent_type, interrog = sentence_type_for(cv, has_interrog_arg=has_interrog_arg)
    transitivity = (
        cv.verb_form.verb.v_transitivity if isinstance(cv.verb_form, VF_Regular) else None
    )
    if arg is not None and transitivity == Transitivity.Intransitive:
        return Sentence(verb=cv, subject=arg, sent_type=sent_type, interrog=interrog)
    return Sentence(verb=cv, direct_obj=arg, sent_type=sent_type, interrog=interrog)


def build_complex_candidates(tokens: list[str]) -> list[AdverbialSentence]:
    candidates: list[AdverbialSentence] = []
    for start, after, surface, ac_types in _find_adv_boundaries(tokens):
        ac = AdvClause(ac_type=ac_types[0], ac_subord=surface)
        splits: list[tuple[list[str], list[str], bool]] = []
        if start >= 1 and tokens[:start - 1]:
            splits.append((tokens[:start - 1], [tokens[start - 1]] + tokens[after:], True))
        if tokens[:start] and tokens[after:]:
            splits.append((tokens[:start], tokens[after:], False))
        for main_tokens, sub_tokens, postposed in splits:
            main = build_sentence(main_tokens)
            if main is None:
                continue
            subord = (
                _build_subordinate_sentence(sub_tokens) if postposed
                else build_sentence(sub_tokens)
            )
            if subord is None:
                continue
            candidates.append(AdverbialSentence(main=main, ac=ac, subord=subord))
    return candidates


def build_enclitic_complex_candidates(tokens: list[str]) -> list[AdverbialSentence]:
    candidates: list[AdverbialSentence] = []
    n = len(tokens)

    def _add(main_tokens: list[str], enclitic_tokens: list[str]) -> None:
        if not main_tokens or not enclitic_tokens:
            return
        for remainder, ac_type, surf in _strip_adv_enclitic(enclitic_tokens[-1]):
            sub_tokens = enclitic_tokens[:-1] + [remainder]
            subord = build_sentence(sub_tokens)
            if subord is None:
                continue
            main = build_sentence(main_tokens)
            if main is None:
                continue
            candidates.append(AdverbialSentence(
                main=main, ac=AdvClause(ac_type=ac_type, ac_subord=surf), subord=subord,
            ))

    for k in range(1, n):
        left, right = tokens[:k], tokens[k:]
        _add(main_tokens=left, enclitic_tokens=right)
        _add(main_tokens=right, enclitic_tokens=left)
    return candidates


def build_coordinated_candidates(tokens: list[str]) -> list[CoordinatedSentence]:
    candidates: list[CoordinatedSentence] = []
    for i, tok in enumerate(tokens):
        if _nfc(tok) != "ha":
            continue
        left_tokens, right_tokens = tokens[:i], tokens[i + 1:]
        if not left_tokens or not right_tokens:
            continue
        s1 = build_sentence(left_tokens)
        s2 = build_sentence(right_tokens)
        if s1 is not None and s2 is not None:
            candidates.append(CoordinatedSentence(s1=s1, s2=s2))
    return candidates


def build_nonverbal_candidates(tokens: list[str]) -> list[NonverbalSentence]:
    candidates: list[NonverbalSentence] = []
    n = len(tokens)
    for pr in _np_span(tokens, 0):
        if pr.num_consumed == n:
            term = pr.np.to_coq()
            candidates.append(NonverbalSentence(coq_term=f"(NVS_Existential {term})"))
            candidates.append(NonverbalSentence(coq_term=f"(NVS_Possessive None {term})"))
    for pr1 in _np_span(tokens, 0):
        if pr1.num_consumed >= n:
            continue
        for pr2 in _np_span(tokens, pr1.num_consumed):
            if pr1.num_consumed + pr2.num_consumed != n:
                continue
            t1, t2 = pr1.np.to_coq(), pr2.np.to_coq()
            candidates.append(NonverbalSentence(coq_term=f"(NVS_Equative {t1} {t2})"))
            candidates.append(NonverbalSentence(coq_term=f"(NVS_Predicative {t1} {t2})"))
            candidates.append(NonverbalSentence(coq_term=f"(NVS_Possessive (Some {t1}) {t2})"))
    return candidates


# ===========================================================================
# Result Dataclasses
# ===========================================================================

@dataclass
class IterationRecord:
    """One pass through the generate-verify-(correct) loop."""
    iteration: int
    guarani_output: str
    parse_error: bool
    wf: Optional[bool]
    failed_predicate: Optional[str]
    feedback: Optional[str]
    coq_term: Optional[str]


@dataclass
class EvalResult:
    """Full result for a single (source_sentence, model) evaluation run."""
    source_sentence: str           # original Spanish
    model_name: str
    initial_output: str            # first Guaraní attempt (before any correction)
    final_output: str              # last Guaraní attempt (may equal initial if accepted)
    accepted: bool                 # True if verifier passed on any iteration
    converged: bool                # True if accepted within max_iterations
    iterations_used: int
    predicate_history: list[Optional[str]]  # failed predicate per iteration (None = passed)
    iteration_records: list[IterationRecord]
    context_mode: str = "none"     # "none" or "coq" — grammar context condition
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ===========================================================================
# Core Evaluation Loop
# ===========================================================================

def run_eval_sentence(
    spanish_sentence: str,
    llm_fn: Callable[[str], str],
    model_name: str,
    verifier: Verifier,
    max_iterations: int = MAX_ITERATIONS,
    context_mode: str = "none",
    coq_context: str = "",
) -> EvalResult:
    """
    Runs the full pipeline for a single Spanish sentence with a single model.
    Lexicons must already be loaded via load_all_lexicons() before calling this.

    If context_mode == "coq", coq_context (loaded once via
    load_coq_context_once()) is prepended to the initial translation prompt
    only — correction prompts are left unchanged, since each llm_fn call is
    stateless and the grammar block's effect on priming vs. feedback is what
    the context-mode ablation is meant to isolate.
    """
    prompt_prefix = (
        CONTEXT_PROMPT_PREFIX_TEMPLATE.format(coq_context=coq_context)
        if context_mode == "coq" else ""
    )
    translation_prompt = prompt_prefix + TRANSLATION_PROMPT_TEMPLATE.format(spanish=spanish_sentence)
    current_output = _sanitize_llm_output(llm_fn(translation_prompt))
    initial_output = current_output

    iteration_records: list[IterationRecord] = []
    predicate_history: list[Optional[str]] = []
    accepted = False

    for iteration in range(max_iterations):
        logger.info("[%s][%d] Checking: %s", model_name, iteration, current_output)

        tokens = tokenize(current_output)
        simple = build_sentence(tokens)
        fronted = build_fronted_object_sentence(tokens)
        candidates = ([simple] if simple is not None else [])
        if fronted is not None:
            candidates.append(fronted)
        candidates += build_complex_candidates(tokens)
        candidates += build_enclitic_complex_candidates(tokens)
        candidates += build_coordinated_candidates(tokens)
        candidates += build_nonverbal_candidates(tokens)

        if not candidates:
            record = IterationRecord(
                iteration=iteration,
                guarani_output=current_output,
                parse_error=True,
                wf=None,
                failed_predicate="PARSE_ERROR",
                feedback="Could not identify a verb in the sentence.",
                coq_term=None,
            )
            iteration_records.append(record)
            predicate_history.append("PARSE_ERROR")

            correction_prompt = (
                f"The Guaraní sentence '{current_output}' could not be parsed. "
                "Please rewrite it as a simple subject-verb-object sentence. "
                "Output only the corrected Guaraní sentence, nothing else."
            )
            current_output = _sanitize_llm_output(llm_fn(correction_prompt))
            continue

        vr: VerifierResult = verifier.verify_candidates(candidates)
        record = IterationRecord(
            iteration=iteration,
            guarani_output=current_output,
            parse_error=False,
            wf=vr.wf,
            failed_predicate=vr.failed_predicate,
            feedback=vr.feedback,
            coq_term=vr.coq_term,
        )
        iteration_records.append(record)
        predicate_history.append(vr.failed_predicate if not vr.wf else None)

        if vr.wf:
            logger.info("[%s][%d] Accepted.", model_name, iteration)
            accepted = True
            break

        logger.info("[%s][%d] Failed predicate: %s", model_name, iteration, vr.failed_predicate)
        correction_prompt = CORRECTION_PROMPT_TEMPLATE.format(
            sentence=current_output,
            feedback=vr.feedback or "Unknown grammatical error.",
        )
        current_output = _sanitize_llm_output(llm_fn(correction_prompt))

    return EvalResult(
        source_sentence=spanish_sentence,
        model_name=model_name,
        initial_output=initial_output,
        final_output=current_output,
        accepted=accepted,
        converged=accepted,
        iterations_used=len(iteration_records),
        predicate_history=predicate_history,
        iteration_records=iteration_records,
        context_mode=context_mode,
    )


# ===========================================================================
# Batch Evaluation Runner
# ===========================================================================

def run_batch_eval(
    spanish_sentences: list[str],
    llm_fns: dict[str, Callable[[str], str]],
    lexicon_csv: str | Path = _DEFAULT_LEXICON,
    coq_lib_dir: Optional[str | Path] = None,
    max_iterations: int = MAX_ITERATIONS,
    output_path: Optional[str | Path] = None,
    max_workers: int = 4,
    rate_limit_delay: float = 0.5,
    context_mode: str = "none",
) -> list[EvalResult]:
    """
    Runs evaluation for every (sentence, model) pair in parallel.

    Args:
        spanish_sentences: list of Spanish source sentences.
        llm_fns: dict mapping model_name -> llm_fn callable.
            Build these with make_deepseek_fn(), make_gemini_fn(), etc.
        lexicon_csv: path to merged.csv lexicon (loaded once).
        coq_lib_dir: path to Coq library directory. Also used as the source
            directory for the "coq" grammar context, when context_mode="coq".
        max_iterations: max correction attempts per sentence.
        output_path: if set, appends each result as JSONL to this file.
        max_workers: number of parallel threads (be mindful of API rate limits).
        rate_limit_delay: seconds to sleep between API calls per worker.
        context_mode: "none" (baseline) or "coq" (inject Coq grammar
            definitions into the translation prompt; loaded once here).

    Returns:
        List of EvalResult, one per (sentence, model) pair.
    """
    load_all_lexicons(lexicon_csv)
    verifier = Verifier(coq_lib_dir=coq_lib_dir)
    coq_context = (
        load_coq_context_once(coq_lib_dir or _DEFAULT_COQ_DIR)
        if context_mode == "coq" else ""
    )

    tasks: list[tuple[str, str, Callable[[str], str]]] = [
        (sentence, model_name, llm_fn)
        for sentence in spanish_sentences
        for model_name, llm_fn in llm_fns.items()
    ]

    results: list[EvalResult] = []

    def _run_task(task: tuple[str, str, Callable[[str], str]]) -> EvalResult:
        sentence, model_name, llm_fn = task
        if rate_limit_delay > 0:
            time.sleep(rate_limit_delay)
        return run_eval_sentence(
            spanish_sentence=sentence,
            llm_fn=llm_fn,
            model_name=model_name,
            verifier=verifier,
            max_iterations=max_iterations,
            context_mode=context_mode,
            coq_context=coq_context,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(_run_task, t): t for t in tasks}
        for future in as_completed(future_to_task):
            try:
                result = future.result()
                results.append(result)
                logger.info(
                    "Done: [%s] '%s' → accepted=%s predicate=%s",
                    result.model_name,
                    result.source_sentence[:40],
                    result.accepted,
                    result.predicate_history,
                )
                if output_path is not None:
                    _append_jsonl(result, output_path)
            except Exception as exc:
                task = future_to_task[future]
                logger.error("Task %s failed: %s", task[:2], exc)

    return results


def _append_jsonl(result: EvalResult, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


# ===========================================================================
# Legacy single-sentence entry point (backwards compatible)
# ===========================================================================

@dataclass
class LoopResult:
    original_sentence: str
    final_sentence: str
    accepted: bool
    iterations: int
    history: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def run_loop(
    llm_fn: Callable[[str], str],
    initial_prompt: str,
    lexicon_csv: str | Path = _DEFAULT_LEXICON,
    coq_lib_dir: Optional[str | Path] = None,
    max_iterations: int = MAX_ITERATIONS,
    log_path: Optional[str | Path] = None,
) -> LoopResult:
    """Original single-sentence loop, kept for backwards compatibility.
    Prefer run_batch_eval() for new code."""
    load_all_lexicons(lexicon_csv)
    verifier = Verifier(coq_lib_dir=coq_lib_dir)

    current_sentence = _sanitize_llm_output(llm_fn(initial_prompt))
    original_sentence = current_sentence
    history: list[dict] = []

    for iteration in range(max_iterations):
        logger.info("[%d] Checking: %s", iteration, current_sentence)
        tokens = tokenize(current_sentence)
        simple = build_sentence(tokens)
        fronted = build_fronted_object_sentence(tokens)
        candidates = ([simple] if simple is not None else [])
        if fronted is not None:
            candidates.append(fronted)
        candidates += build_complex_candidates(tokens)
        candidates += build_enclitic_complex_candidates(tokens)
        candidates += build_coordinated_candidates(tokens)
        candidates += build_nonverbal_candidates(tokens)

        if not candidates:
            history.append({
                "iteration": iteration, "sentence": current_sentence,
                "parse_error": True, "wf": None,
                "feedback": "Could not identify a verb in the sentence.",
            })
            correction_prompt = (
                f"The Guaraní sentence '{current_sentence}' could not be parsed. "
                "Please rewrite it as a simple subject-verb-object sentence. "
                "Output only the corrected Guaraní sentence, nothing else."
            )
            current_sentence = _sanitize_llm_output(llm_fn(correction_prompt))
            continue

        vr: VerifierResult = verifier.verify_candidates(candidates)
        history.append({
            "iteration": iteration, "sentence": current_sentence,
            "parse_error": False, "wf": vr.wf,
            "failed_predicate": vr.failed_predicate,
            "feedback": vr.feedback, "coq_term": vr.coq_term,
        })

        if vr.wf:
            result = LoopResult(
                original_sentence=original_sentence, final_sentence=current_sentence,
                accepted=True, iterations=iteration + 1, history=history,
            )
            _maybe_log(result, log_path)
            return result

        correction_prompt = CORRECTION_PROMPT_TEMPLATE.format(
            sentence=current_sentence,
            feedback=vr.feedback or "Unknown grammatical error.",
        )
        current_sentence = _sanitize_llm_output(llm_fn(correction_prompt))

    result = LoopResult(
        original_sentence=original_sentence, final_sentence=current_sentence,
        accepted=False, iterations=max_iterations, history=history,
    )
    _maybe_log(result, log_path)
    return result


def _maybe_log(result: LoopResult, log_path: Optional[str | Path]) -> None:
    if log_path is None:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(result.to_json() + "\n")