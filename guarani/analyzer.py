"""
analyzer.py

Morphological analyzer for Guaraní verb forms.

Loads the enriched lexicon CSV and, given a surface verb string,
returns a list of candidate ConjugatedVerb parses. The analysis
logic is the inverse of the prefix/suffix functions in Verb.v —
provably consistent because it uses the same tables.

Pipeline:
    surface string
        → check IRREG_FORM_INDEX (exact match)
        → OR: try each prefix table × person/number slot
              → strip prefix → recursive suffix strip → lexicon lookup
        → return list[ConjugatedVerb]

The caller (verifier.py) runs wf_conjugated_verb on each candidate
and passes passing ones to sentence-level wf checking.
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
)


# ============================================================
#  Lexicon
# ============================================================

@dataclass
class LexEntry:
    """One row from the enriched lexicon CSV (verbs only)."""
    word:         str
    orality:      Orality
    verb_class:   VerbClass
    transitivity: Optional[Transitivity]   # None = unknown
    root_class:   VerbRootClass
    chendal_3sg:  Chendal3sgForm
    is_irregular: bool
    irreg_lemma:  Optional[str]            # "Irreg_Ju" / "Irreg_Ho" / "Irreg_E"
    spanish_gloss: Optional[str]


_LEXICON: dict[str, LexEntry] = {}


def load_lexicon(enriched_csv: str | Path) -> None:
    """
    Load the enriched Guaraní→Spanish CSV into the module-level lexicon.
    Call once at startup. Only rows with primary_pos == 'verb' are loaded
    as verb entries; the full lexicon (including nouns, adverbs, etc.) is
    stored separately for NP analysis.
    """
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
                vc = VerbClass.Areal   # default; flagged for manual review

            tr_str = row.get("transitivity", "")
            if tr_str == "Transitive":
                tr = Transitivity.Transitive
            elif tr_str == "Intransitive":
                tr = Transitivity.Intransitive
            elif tr_str == "Ambitransitive":
                tr = None   # treat as unknown — wf checker is permissive
            else:
                tr = None   # blank = unknown

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
#  Prefix tables (inverse of Verb.v §14)
# ============================================================
#
# Each entry: (prefix_string, person, number, Optional[Inclusivity])
# Sorted longest-first so greedier matches are tried first.
# This prevents "re" matching before "rei" on Aireal verbs.

_AREAL_PREFIXES: list[tuple[str, Person, Number, Optional[Inclusivity]]] = [
    ("ña",  Person.First,  Number.Plural,   Inclusivity.Inclusive),  # nasal 1pl incl
    ("ja",  Person.First,  Number.Plural,   Inclusivity.Inclusive),  # oral 1pl incl
    ("ro",  Person.First,  Number.Plural,   Inclusivity.Exclusive),
    ("pe",  Person.Second, Number.Plural,   None),
    ("re",  Person.Second, Number.Singular, None),
    ("o",   Person.Third,  Number.Singular, None),   # also 3pl
    ("a",   Person.First,  Number.Singular, None),
]

_AIREAL_PREFIXES: list[tuple[str, Person, Number, Optional[Inclusivity]]] = [
    ("ñai", Person.First,  Number.Plural,   Inclusivity.Inclusive),  # nasal
    ("jai", Person.First,  Number.Plural,   Inclusivity.Inclusive),
    ("roi", Person.First,  Number.Plural,   Inclusivity.Exclusive),
    ("pei", Person.Second, Number.Plural,   None),
    ("rei", Person.Second, Number.Singular, None),
    ("oi",  Person.Third,  Number.Singular, None),   # also 3pl
    ("ai",  Person.First,  Number.Singular, None),
]

_CHENDAL_PREFIXES: list[tuple[str, Person, Number, Optional[Inclusivity]]] = [
    ("ñande", Person.First,  Number.Plural,   Inclusivity.Inclusive),  # oral
    ("ñane",  Person.First,  Number.Plural,   Inclusivity.Inclusive),  # nasal
    ("pende", Person.Second, Number.Plural,   None),                   # oral
    ("pene",  Person.Second, Number.Plural,   None),                   # nasal
    ("ore",   Person.First,  Number.Plural,   Inclusivity.Exclusive),
    ("che",   Person.First,  Number.Singular, None),
    ("nde",   Person.Second, Number.Singular, None),                   # oral
    ("ne",    Person.Second, Number.Singular, None),                   # nasal
    # 3sg: hi-/hiñ- (C3sg_Hi), ij- (C3sg_Ij oral), iñ- (nasal), i- (C3sg_I)
    ("hiñ",   Person.Third,  Number.Singular, None),
    ("hi",    Person.Third,  Number.Singular, None),
    ("iñ",    Person.Third,  Number.Singular, None),
    ("ij",    Person.Third,  Number.Singular, None),
    ("i",     Person.Third,  Number.Singular, None),
]

# Map prefix to expected C3sg variant (for Chendal 3rd person only)
_CHENDAL_3SG_PREFIX_TO_FORM: dict[str, Chendal3sgForm] = {
    "hi":  Chendal3sgForm.C3sg_Hi,
    "hiñ": Chendal3sgForm.C3sg_Hi,
    "ij":  Chendal3sgForm.C3sg_Ij,
    "iñ":  Chendal3sgForm.C3sg_I,   # shared by C3sg_I and C3sg_Ij nasal
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
    """
    Recursively strip recognized suffixes from the right of `form`.
    Each time the remainder hits the lexicon, record (remainder, suffixes).
    Accumulates into `results` (a list so callers get all parses).

    Bounded by the 13 slots in Verb.v — no real word has all 13 stacked,
    so recursion depth is negligible in practice.
    """
    # Base case: remainder is in the lexicon
    if form in _LEXICON:
        # Suffixes were accumulated left-to-right but stripped right-to-left,
        # so they're already in the right order (slot ascending).
        results.append((form, list(accumulated)))

    # Recursive case: try stripping each known suffix from the right
    for surface, suffix in SUFFIX_STRIP_INDEX:
        if form.endswith(surface) and len(form) > len(surface):
            remainder = form[: -len(surface)]
            # Don't add this suffix if it's already in accumulated
            # (no duplicate suffixes per Verb.v wf)
            if suffix not in accumulated:
                _strip_suffixes(remainder, [suffix] + accumulated, results)


# ============================================================
#  Core analyzer
# ============================================================

@dataclass
class ParseResult:
    """One candidate parse of a surface verb form."""
    conj_verb:  ConjugatedVerb
    root:       str                    # bare root that hit the lexicon
    confidence: str                    # "exact_irreg" | "prefix_match" | "ambiguous"


def analyze(surface: str) -> list[ParseResult]:
    """
    Given a surface Guaraní verb form, return all candidate parses
    as ConjugatedVerb objects.

    Steps:
    1. Exact match against irregular paradigm table.
    2. Negation circumfix stripping (nd-/n- prefix + neg suffix).
    3. Prefix stripping × suffix stripping × lexicon lookup.

    Returns an empty list if no parse is found.
    """
    surface = surface.strip().lower()
    results: list[ParseResult] = []

    # ----------------------------------------------------------
    # Step 1: Irregulars — exact match, unambiguous
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # Step 2: Negation circumfix detection
    # nd- (oral) or n- (nasal) prefix + euphonic vowel
    # We strip it and mark polarity=Negative, then continue to
    # step 3 on the inner form.
    # ----------------------------------------------------------
    inner = surface
    polarity = Polarity.Positive

    for neg_pfx in ("nd", "n"):
        if surface.startswith(neg_pfx):
            # Strip nd/n + one euphonic vowel (a/e/o)
            after_neg = surface[len(neg_pfx):]
            if after_neg and after_neg[0] in "aeo":
                inner = after_neg[1:]
                polarity = Polarity.Negative
                break

    # ----------------------------------------------------------
    # Step 3: Prefix stripping × suffix stripping × lexicon
    # ----------------------------------------------------------
    for verb_class, prefix_table in _ALL_PREFIX_TABLES:
        for prefix, person, number, incl in prefix_table:
            if not inner.startswith(prefix):
                continue
            after_prefix = inner[len(prefix):]
            if not after_prefix:
                continue

            # Try all suffix combinations from the right
            strip_results: list[tuple[str, list[VerbalSuffix]]] = []
            _strip_suffixes(after_prefix, [], strip_results)

            for root, suffixes in strip_results:
                entry = _LEXICON.get(root)
                if entry is None:
                    continue
                if entry.verb_class != verb_class:
                    continue

                # For Chendal 3sg, verify the prefix allomorph matches
                # the lexicon entry's chendal_3sg field.
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
                        else Transitivity.Intransitive  # permissive: unknown = intrans for wf
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

    # Deduplicate by Coq term string (same parse from different prefix paths)
    seen: set[str] = set()
    deduped: list[ParseResult] = []
    for r in results:
        key = r.conj_verb.to_coq()
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped