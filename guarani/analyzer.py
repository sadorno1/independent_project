"""
analyzer.py

Morphological analyzer for Guaraní verb forms and noun phrases.

Loads the enriched lexicon CSV. For verbs, given a surface string,
returns candidate ConjugatedVerb parses by inverting the prefix/suffix
tables in Verb.v. For NPs, given a surface string, returns candidate
NP parses (subject pronouns from a closed table, or bare nouns from
the lexicon).

The caller (verifier.py) runs wf_conjugated_verb / wf_np on each
candidate and passes passing ones to sentence-level wf checking.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .types import (
    Orality, Person, Number, Inclusivity, VerbClass, Transitivity,
    VerbRootClass, Chendal3sgForm, Voice, Mood, Polarity,
    VerbalSuffix, IrregularVerb, Verb, VerbForm, VF_Regular, VF_Irregular,
    ConjugatedVerb, IRREG_FORM_INDEX, IRREG_PARADIGM, SUFFIX_STRIP_INDEX,
    SubjPronoun, SUBJ_PRONOUN_FORM_INDEX,
    _SUBJ_PRONOUN_PERSON, _SUBJ_PRONOUN_NUMBER,
    Noun, NP, WordEnding, word_ending_of,
)


# ============================================================
#  Verb lexicon
# ============================================================

@dataclass
class LexEntry:
    word:         str
    orality:      Orality
    verb_class:   VerbClass
    transitivity: Optional[Transitivity]
    root_class:   VerbRootClass
    chendal_3sg:  Chendal3sgForm
    is_irregular: bool
    irreg_lemma:  Optional[str]
    spanish_gloss: Optional[str]


_LEXICON: dict[str, LexEntry] = {}


def load_lexicon(enriched_csv: str | Path) -> None:
    global _LEXICON
    _LEXICON = {}
    path = Path(enriched_csv)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("primary_pos") != "verb":
                continue
            word = row["word"].strip()

            orality = Orality(row["orality"]) if row.get("orality") else Orality.Oral

            vc_str = row.get("verb_class", "")
            if vc_str == "Areal":
                vc = VerbClass.Areal
            elif vc_str == "Aireal":
                vc = VerbClass.Aireal
            elif vc_str == "Chendal":
                vc = VerbClass.Chendal
            else:
                vc = VerbClass.Areal

            tr_str = row.get("transitivity", "")
            if tr_str == "Transitive":
                tr = Transitivity.Transitive
            elif tr_str == "Intransitive":
                tr = Transitivity.Intransitive
            elif tr_str == "Ambitransitive":
                tr = None
            else:
                tr = None

            c3_str = row.get("chendal_3sg", "")
            if c3_str == "C3sg_Hi":
                c3 = Chendal3sgForm.C3sg_Hi
            elif c3_str == "C3sg_Ij":
                c3 = Chendal3sgForm.C3sg_Ij
            else:
                c3 = Chendal3sgForm.C3sg_I

            rc_str = row.get("root_class", "")
            rc = (VerbRootClass.VRoot_Relational
                  if rc_str == "VRoot_Relational"
                  else VerbRootClass.VRoot_Plain)

            is_irreg = row.get("is_irregular", "false").lower() == "true"
            irreg_lemma = row.get("irregular_lemma") or None
            gloss = row.get("spanish_sense") or None

            _LEXICON[word] = LexEntry(
                word=word,
                orality=orality,
                verb_class=vc,
                transitivity=tr,
                root_class=rc,
                chendal_3sg=c3,
                is_irregular=is_irreg,
                irreg_lemma=irreg_lemma,
                spanish_gloss=gloss,
            )


def lookup(root: str) -> Optional[LexEntry]:
    return _LEXICON.get(root)


# ============================================================
#  Noun lexicon
# ============================================================

@dataclass
class NounLexEntry:
    word:    str
    orality: Orality
    human:   bool


_NOUN_LEXICON: dict[str, NounLexEntry] = {}


def load_noun_lexicon(enriched_csv: str | Path) -> None:
    global _NOUN_LEXICON
    _NOUN_LEXICON = {}
    path = Path(enriched_csv)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("primary_pos") != "noun":
                continue
            word = row["word"].strip()
            orality = Orality(row["orality"]) if row.get("orality") else Orality.Oral
            human = row.get("human", "").strip().lower() == "true"

            _NOUN_LEXICON[word] = NounLexEntry(
                word=word,
                orality=orality,
                human=human,
            )


def lookup_noun(word: str) -> Optional[NounLexEntry]:
    return _NOUN_LEXICON.get(word)


# ============================================================
#  Prefix tables (inverse of Verb.v §14)
# ============================================================

_AREAL_PREFIXES: list[tuple[str, Person, Number, Optional[Inclusivity]]] = [
    ("ña",  Person.First,  Number.Plural,   Inclusivity.Inclusive),
    ("ja",  Person.First,  Number.Plural,   Inclusivity.Inclusive),
    ("ro",  Person.First,  Number.Plural,   Inclusivity.Exclusive),
    ("pe",  Person.Second, Number.Plural,   None),
    ("re",  Person.Second, Number.Singular, None),
    ("o",   Person.Third,  Number.Singular, None),
    ("a",   Person.First,  Number.Singular, None),
]

_AIREAL_PREFIXES: list[tuple[str, Person, Number, Optional[Inclusivity]]] = [
    ("ñai", Person.First,  Number.Plural,   Inclusivity.Inclusive),
    ("jai", Person.First,  Number.Plural,   Inclusivity.Inclusive),
    ("roi", Person.First,  Number.Plural,   Inclusivity.Exclusive),
    ("pei", Person.Second, Number.Plural,   None),
    ("rei", Person.Second, Number.Singular, None),
    ("oi",  Person.Third,  Number.Singular, None),
    ("ai",  Person.First,  Number.Singular, None),
]

_CHENDAL_PREFIXES: list[tuple[str, Person, Number, Optional[Inclusivity]]] = [
    ("ñande", Person.First,  Number.Plural,   Inclusivity.Inclusive),
    ("ñane",  Person.First,  Number.Plural,   Inclusivity.Inclusive),
    ("pende", Person.Second, Number.Plural,   None),
    ("pene",  Person.Second, Number.Plural,   None),
    ("ore",   Person.First,  Number.Plural,   Inclusivity.Exclusive),
    ("che",   Person.First,  Number.Singular, None),
    ("nde",   Person.Second, Number.Singular, None),
    ("ne",    Person.Second, Number.Singular, None),
    ("hiñ",   Person.Third,  Number.Singular, None),
    ("hi",    Person.Third,  Number.Singular, None),
    ("iñ",    Person.Third,  Number.Singular, None),
    ("ij",    Person.Third,  Number.Singular, None),
    ("i",     Person.Third,  Number.Singular, None),
]

_CHENDAL_3SG_PREFIX_TO_FORM: dict[str, Chendal3sgForm] = {
    "hi":  Chendal3sgForm.C3sg_Hi,
    "hiñ": Chendal3sgForm.C3sg_Hi,
    "ij":  Chendal3sgForm.C3sg_Ij,
    "iñ":  Chendal3sgForm.C3sg_I,
    "i":   Chendal3sgForm.C3sg_I,
}

_ALL_PREFIX_TABLES = [
    (VerbClass.Areal,   _AREAL_PREFIXES),
    (VerbClass.Aireal,  _AIREAL_PREFIXES),
    (VerbClass.Chendal, _CHENDAL_PREFIXES),
]


# ============================================================
#  Suffix stripping (recursive)
# ============================================================

def _strip_suffixes(
    form: str,
    accumulated: list[VerbalSuffix],
    results: list[tuple[str, list[VerbalSuffix]]],
) -> None:
    if form in _LEXICON:
        results.append((form, list(accumulated)))

    for surface, suffix in SUFFIX_STRIP_INDEX:
        if form.endswith(surface) and len(form) > len(surface):
            remainder = form[: -len(surface)]
            if suffix not in accumulated:
                _strip_suffixes(remainder, [suffix] + accumulated, results)


# ============================================================
#  Verb analyzer
# ============================================================

@dataclass
class ParseResult:
    conj_verb:  ConjugatedVerb
    root:       str
    confidence: str


def analyze(surface: str) -> list[ParseResult]:
    surface = surface.strip().lower()
    results: list[ParseResult] = []

    if surface in IRREG_FORM_INDEX:
        irreg_verb, person, number, incl = IRREG_FORM_INDEX[surface]
        cv = ConjugatedVerb(
            verb_form=VF_Irregular(irreg_verb),
            person=person,
            number=number,
            incl=incl,
            mood=Mood.Indicative,
            polarity=Polarity.Positive,
            voice=Voice.Active,
        )
        return [ParseResult(cv, surface, "exact_irreg")]

    inner = surface
    polarity = Polarity.Positive

    for neg_pfx in ("nd", "n"):
        if surface.startswith(neg_pfx):
            after_neg = surface[len(neg_pfx):]
            if after_neg and after_neg[0] in "aeo":
                inner = after_neg[1:]
                polarity = Polarity.Negative
                break

    for verb_class, prefix_table in _ALL_PREFIX_TABLES:
        for prefix, person, number, incl in prefix_table:
            if not inner.startswith(prefix):
                continue
            after_prefix = inner[len(prefix):]
            if not after_prefix:
                continue

            strip_results: list[tuple[str, list[VerbalSuffix]]] = []
            _strip_suffixes(after_prefix, [], strip_results)

            for root, suffixes in strip_results:
                entry = _LEXICON.get(root)
                if entry is None:
                    continue
                if entry.verb_class != verb_class:
                    continue

                if (verb_class == VerbClass.Chendal
                        and person == Person.Third
                        and prefix in _CHENDAL_3SG_PREFIX_TO_FORM):
                    expected_form = _CHENDAL_3SG_PREFIX_TO_FORM[prefix]
                    if expected_form != entry.chendal_3sg:
                        continue

                verb = Verb(
                    v_class=entry.verb_class,
                    v_orality=entry.orality,
                    v_root=root,
                    v_transitivity=(
                        entry.transitivity
                        if entry.transitivity is not None
                        else Transitivity.Intransitive
                    ),
                    v_root_class=entry.root_class,
                    v_chendal_3sg=entry.chendal_3sg,
                )
                cv = ConjugatedVerb(
                    verb_form=VF_Regular(verb),
                    person=person,
                    number=number,
                    incl=incl,
                    mood=Mood.Indicative,
                    polarity=polarity,
                    voice=Voice.Active,
                    suffixes=suffixes,
                )
                confidence = "prefix_match" if len(strip_results) == 1 else "ambiguous"
                results.append(ParseResult(cv, root, confidence))

    seen: set[str] = set()
    deduped: list[ParseResult] = []
    for r in results:
        key = r.conj_verb.to_coq()
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped


# ============================================================
#  NP analyzer
# ============================================================

@dataclass
class NPParseResult:
    np:         NP
    confidence: str


def analyze_np(surface: str) -> list[NPParseResult]:
    surface = surface.strip().lower()
    results: list[NPParseResult] = []

    pronoun = SUBJ_PRONOUN_FORM_INDEX.get(surface)
    if pronoun is not None:
        np = NP(
            surface=surface,
            person=_SUBJ_PRONOUN_PERSON[pronoun],
            number=_SUBJ_PRONOUN_NUMBER[pronoun],
            pronoun=pronoun,
        )
        results.append(NPParseResult(np, "exact_pronoun"))

    entry = _NOUN_LEXICON.get(surface)
    if entry is not None:
        noun = Noun(
            n_root=entry.word,
            n_orality=entry.orality,
            n_ending=word_ending_of(entry.word),
            n_human=entry.human,
        )
        np = NP(
            surface=surface,
            person=Person.Third,
            number=Number.Singular,
            human=entry.human,
            noun=noun,
        )
        results.append(NPParseResult(np, "bare_noun"))

    return results