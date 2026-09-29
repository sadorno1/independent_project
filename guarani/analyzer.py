"""
analyzer.py

Morphological analyzer for Guaraní verb forms and noun phrase layouts. Inverts 
affix rules and queries the dictionary to return valid structural parses.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional

from .types import (
    Orality, Person, Number, Inclusivity, VerbClass, Transitivity,
    VerbRootClass, Chendal3sgForm, Voice, Mood, Polarity,
    VerbalSuffix, Verb, VF_Regular, VF_Irregular, ConjugatedVerb,
    IRREG_FORM_INDEX, SUFFIX_STRIP_INDEX, SUBJ_PRONOUN_FORM_INDEX,
    _SUBJ_PRONOUN_PERSON, _SUBJ_PRONOUN_NUMBER, Noun, NP, RootClass,
    word_ending_of, Adjective, Postposition, POSS_MARKER_FORM_INDEX,
    DEM_ADJ_FORM_INDEX, POSTPOSITION_STRIP_INDEX, POSTPOSITION_FORM_INDEX,
    NegPron, NEG_PRON_FORM_INDEX, NominalSuffix, NOM_SUFFIX_STRIP_INDEX,
    NOM_SUFFIX_PAIR_OK, DEM_PRON_FORM_INDEX, IndefPron, INDEF_PRON_FORM_INDEX,
    INDEF_PRON_HUMAN, indef_pron_number, INTERROG_PRON_FORM_INDEX,
    INTERROG_PRON_HUMAN,
)

# ===========================================================================
# Lexicon Entry Dataclasses
# ===========================================================================

@dataclass
class LexEntry:
    word: str
    orality: Orality
    verb_class: VerbClass
    transitivity: Optional[Transitivity]
    root_class: VerbRootClass
    chendal_3sg: Chendal3sgForm
    is_irregular: bool
    irreg_lemma: Optional[str]
    spanish_gloss: Optional[str]

@dataclass
class NounLexEntry:
    word: str
    orality: Orality
    root_class: RootClass
    human: bool

@dataclass
class AdjLexEntry:
    word: str
    orality: Orality

_LEXICON: dict[str, LexEntry] = {}
_NOUN_LEXICON: dict[str, NounLexEntry] = {}
_ADJ_LEXICON: dict[str, AdjLexEntry] = {}
_NEG_PRON_LEXICON: dict[str, NegPron] = {}

# ===========================================================================
# Data Loaders
# ===========================================================================

def load_lexicon(enriched_csv: str | Path) -> None:
    global _LEXICON
    _LEXICON = {}
    with Path(enriched_csv).open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pos = row.get("primary_pos")
            if pos == "adj":
                # Guaraní adjectives predicate directly with Chendal person
                # markers (che-kane'o, i-porã), so every adjective is also a
                # Chendal intransitive root. An explicit verb row wins.
                word = _nfc(row["word"])
                _LEXICON.setdefault(word, LexEntry(
                    word=word,
                    orality=Orality(row["orality"]) if row.get("orality") else Orality.Oral,
                    verb_class=VerbClass.Chendal, transitivity=Transitivity.Intransitive,
                    root_class=VerbRootClass.VRoot_Plain, chendal_3sg=Chendal3sgForm.C3sg_I,
                    is_irregular=False, irreg_lemma=None, spanish_gloss=row.get("spanish_gloss") or None,
                ))
                continue
            if pos != "verb":
                continue
            word = _nfc(row["word"])
            orality = Orality(row["orality"]) if row.get("orality") else Orality.Oral

            vc_str = row.get("verb_class", "")
            if vc_str == "Areal": vc = VerbClass.Areal
            elif vc_str == "Aireal": vc = VerbClass.Aireal
            elif vc_str == "Chendal": vc = VerbClass.Chendal
            else: vc = VerbClass.Areal

            tr_str = row.get("transitivity", "")
            if tr_str == "Transitive": tr = Transitivity.Transitive
            elif tr_str == "Intransitive": tr = Transitivity.Intransitive
            elif tr_str == "Ditransitive": tr = Transitivity.Ditransitive
            elif tr_str == "PostpComplement": tr = Transitivity.PostpComplement
            elif tr_str == "Ambitransitive": tr = Transitivity.Transitive
            else: tr = None

            c3_str = row.get("chendal_3sg", "")
            if c3_str == "C3sg_Hi": c3 = Chendal3sgForm.C3sg_Hi
            elif c3_str == "C3sg_Ij": c3 = Chendal3sgForm.C3sg_Ij
            else: c3 = Chendal3sgForm.C3sg_I

            rc_str = row.get("root_class", "")
            rc = VerbRootClass.VRoot_Relational if rc_str == "VRoot_Relational" else VerbRootClass.VRoot_Plain

            _LEXICON[word] = LexEntry(
                word=word, orality=orality, verb_class=vc, transitivity=tr, root_class=rc, chendal_3sg=c3,
                is_irregular=row.get("is_irregular", "false").lower() == "true",
                irreg_lemma=row.get("irregular_lemma") or None, spanish_gloss=row.get("spanish_sense") or None,
            )
    _add_deglottalized_aliases(_LEXICON)

def load_noun_lexicon(enriched_csv: str | Path) -> None:
    global _NOUN_LEXICON
    _NOUN_LEXICON = {}
    with Path(enriched_csv).open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("primary_pos") != "noun":
                continue
            word = _nfc(row["word"])
            # Dictionary homographs: personal pronouns (che, nde, ha'e, ...)
            # must parse as pronouns, never as third-person bare nouns.
            if word in SUBJ_PRONOUN_FORM_INDEX:
                continue
            rc_str = row.get("root_class", "")
            try:
                root_class = RootClass(rc_str) if rc_str else RootClass.Uniform
            except ValueError:
                root_class = RootClass.Uniform

            _NOUN_LEXICON[word] = NounLexEntry(
                word=word, orality=Orality(row["orality"]) if row.get("orality") else Orality.Oral,
                root_class=root_class, human=row.get("human", "").strip().lower() == "true",
            )
    _add_deglottalized_aliases(_NOUN_LEXICON)

def load_adj_lexicon(enriched_csv: str | Path) -> None:
    global _ADJ_LEXICON
    _ADJ_LEXICON = {}
    with Path(enriched_csv).open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("primary_pos") != "adj":
                continue
            word = _nfc(row["word"])
            _ADJ_LEXICON[word] = AdjLexEntry(
                word=word, orality=Orality(row["orality"]) if row.get("orality") else Orality.Oral
            )
    _add_deglottalized_aliases(_ADJ_LEXICON)

def load_neg_pron_lexicon(enriched_csv: str | Path) -> None:
    """Loads dictionary rows tagged neg_pron (§3.5.3 double-negation triggers:
    mba'eve, avave, ...) into the closed NegPron table from types.py."""
    global _NEG_PRON_LEXICON
    _NEG_PRON_LEXICON = {}
    with Path(enriched_csv).open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("primary_pos") != "neg_pron":
                continue
            word = _nfc(row["word"])
            neg_pron = NEG_PRON_FORM_INDEX.get(word)
            if neg_pron is not None:
                _NEG_PRON_LEXICON[word] = neg_pron
    _add_deglottalized_aliases(_NEG_PRON_LEXICON)

# Typographic apostrophe variants → ASCII saltillo
_APOSTROPHE_VARIANTS = str.maketrans({
    "’": "'", "‘": "'", "ʼ": "'", "ʻ": "'", "´": "'", "`": "'",
    "᾿": "'", "῾": "'",
})

def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip().lower()).translate(_APOSTROPHE_VARIANTS)


_DETILDE = str.maketrans("ãẽĩõũỹ", "aeiouy")


def _detilde(s: str) -> str:
    return s.translate(_DETILDE)


def _add_deglottalized_aliases(lexicon: dict) -> None:
    """Index normalized spellings (apostrophe-stripped and/or nasal-tilde-
    stripped: mandi'o -> mandio, porã -> pora) so degraded input still
    resolves; exact spellings always win."""
    for word in list(lexicon):
        plain = word.replace("'", "")
        for alias in (plain, _detilde(word), _detilde(plain)):
            if alias and alias != word and alias not in lexicon:
                lexicon[alias] = lexicon[word]


def _lex_get(root: str) -> Optional[LexEntry]:
    """Verb lookup tolerant of extra nasal tildes in the query (kane'õ finds
    a dictionary entry spelled kane'o)."""
    return _LEXICON.get(root) or _LEXICON.get(_detilde(root))


def _noun_get(word: str) -> Optional[NounLexEntry]:
    return _NOUN_LEXICON.get(word) or _NOUN_LEXICON.get(_detilde(word))


def _strip_nominal_suffixes(form: str) -> list[tuple[str, list[NominalSuffix]]]:
    """Inverts NP_Suf/NP_Suf2's render_np (render_np inner ++ render suf...):
    a suffix fuses directly onto the END of whatever the inner NP's surface
    is, so stripping works right-to-left — the first suffix stripped is the
    outermost (s2 of NP_Suf2 inner s1 s2), and a second strip attempt is
    only made where suffix_pair_ok(s1, s2) actually allows a pair. Returns
    (remainder, suffixes) with suffixes in [s1, s2] / [suf] order, ready to
    hand straight to NP.suffixes."""
    results: list[tuple[str, list[NominalSuffix]]] = []
    for surf2, suf2 in NOM_SUFFIX_STRIP_INDEX:
        if form.endswith(surf2) and len(form) > len(surf2):
            rem2 = form[:-len(surf2)]
            results.append((rem2, [suf2]))
            for surf1, suf1 in NOM_SUFFIX_STRIP_INDEX:
                if (suf1, suf2) not in NOM_SUFFIX_PAIR_OK:
                    continue
                if rem2.endswith(surf1) and len(rem2) > len(surf1):
                    results.append((rem2[:-len(surf1)], [suf1, suf2]))
    return results


def _noun_readings(tok: str) -> list[tuple[NounLexEntry, list[NominalSuffix]]]:
    """Every way `tok` can be read as a lexicon noun: the bare exact match
    (suffixes=[]) plus every nominal-suffix-stripped reading whose
    remainder is itself a known noun. Suffix-stripped readings are skipped
    when `tok` is itself a recognized closed-class pronoun (neg/subj/
    indef/interrog/dem) — e.g. "avave" is NegPron_Avave, not "ava" (a real
    noun, "person") + NS_ComparVe ("-ve"). Without this guard that spurious
    decomposition carries no negative-pronoun marking at all, so it
    bypasses ss_neg_concord_ok entirely and lets e.g. "avave oguata"
    ("nobody walks", positive polarity — should fail) verify as
    well-formed via the "ava-ve" misreading even though the correct
    NP_PronNeg reading (rightly) fails."""
    readings: list[tuple[NounLexEntry, list[NominalSuffix]]] = []
    exact = _noun_get(tok)
    if exact is not None:
        readings.append((exact, []))
    is_closed_class_pronoun = (
        _neg_pron_get(tok) is not None or tok in SUBJ_PRONOUN_FORM_INDEX
        or tok in INDEF_PRON_FORM_INDEX or tok in INTERROG_PRON_FORM_INDEX
        or tok in DEM_PRON_FORM_INDEX
    )
    if not is_closed_class_pronoun:
        for remainder, suffixes in _strip_nominal_suffixes(tok):
            entry = _noun_get(remainder)
            if entry is not None:
                readings.append((entry, suffixes))
    return readings


def _adj_get(word: str) -> Optional[AdjLexEntry]:
    return _ADJ_LEXICON.get(word) or _ADJ_LEXICON.get(_detilde(word))


def _adj_readings(tok: str) -> list[tuple[AdjLexEntry, list[NominalSuffix]]]:
    """_noun_readings' counterpart for adjectives: every way `tok` can be
    read as a lexicon adjective, bare or nominal-suffix-stripped. Needed
    because NP_Adj's rendering is "noun ++ ' ' ++ adj" — the ADJECTIVE, not
    the noun, is the final/suffix-bearing token (e.g. "kavaju guasuete" =
    "a very big horse", NS_Super on the adjective)."""
    readings: list[tuple[AdjLexEntry, list[NominalSuffix]]] = []
    exact = _adj_get(tok)
    if exact is not None:
        readings.append((exact, []))
    for remainder, suffixes in _strip_nominal_suffixes(tok):
        entry = _adj_get(remainder)
        if entry is not None:
            readings.append((entry, suffixes))
    return readings


def _neg_pron_get(word: str) -> Optional[NegPron]:
    return _NEG_PRON_LEXICON.get(word) or _NEG_PRON_LEXICON.get(_detilde(word))

_STRIP_ACUTE = str.maketrans("áéíóúý", "aeiouy")

def _strip_neg_accent(s: str) -> str:
    """Remove stress (acute) accents inside a nd-...-í circumfix.
    Only called after the nd- prefix is confirmed, so ñ/ã/ẽ etc. are untouched."""
    return s.translate(_STRIP_ACUTE)

_NASAL_VOWELS = "ãẽĩõũỹ"


def surface_orality(word: str) -> Orality:
    """Computes nasality from the surface form: nasal vowels, ñ, or a plain
    m/n make a root nasal; mb/nd/ng/nt are oral prenasalized digraphs."""
    w = _nfc(word)
    for i, c in enumerate(w):
        if c in _NASAL_VOWELS or c == "ñ":
            return Orality.Nasal
        if c == "m" and (i + 1 >= len(w) or w[i + 1] != "b"):
            return Orality.Nasal
        if c == "n" and (i + 1 >= len(w) or w[i + 1] not in "dgt"):
            return Orality.Nasal
    return Orality.Oral


def lookup(root: str) -> Optional[LexEntry]: return _lex_get(_nfc(root))
def lookup_noun(word: str) -> Optional[NounLexEntry]: return _noun_get(_nfc(word))
def lookup_adj(word: str) -> Optional[AdjLexEntry]: return _adj_get(_nfc(word))

# Dative/allative pronouns → equivalent SubjPronoun for NP building
_DATIVE_PRONOUN_INDEX: dict[str, "SubjPronoun"] = {}

def _build_dative_index() -> None:
    from .types import SubjPronoun
    global _DATIVE_PRONOUN_INDEX
    _DATIVE_PRONOUN_INDEX = {
        _nfc(k): v for k, v in {
            "chupe": SubjPronoun.Subj3SG, "chúpe": SubjPronoun.Subj3SG,
            "ichupe": SubjPronoun.Subj3SG, "ichupekuéra": SubjPronoun.Subj3PL,
            "chépe": SubjPronoun.Subj1SG, "chepe": SubjPronoun.Subj1SG,
            "ndéve": SubjPronoun.Subj2SG, "ndeve": SubjPronoun.Subj2SG,
            "ñandéve": SubjPronoun.Subj1PL_INCL, "ñandeve": SubjPronoun.Subj1PL_INCL,
            "oréve": SubjPronoun.Subj1PL_EXCL, "oreve": SubjPronoun.Subj1PL_EXCL,
            "péve": SubjPronoun.Subj2PL, "peve": SubjPronoun.Subj2PL,
        }.items()
    }

_build_dative_index()

# ===========================================================================
# Morphological Paradigms & Prefix Tables
# ===========================================================================

_AREAL_PREFIXES = [
    ("ña", Person.First, Number.Plural, Inclusivity.Inclusive),
    ("ja", Person.First, Number.Plural, Inclusivity.Inclusive),
    ("ro", Person.First, Number.Plural, Inclusivity.Exclusive),
    ("pe", Person.Second, Number.Plural, None),
    ("re", Person.Second, Number.Singular, None),
    ("o", Person.Third, Number.Singular, None),
    ("a", Person.First, Number.Singular, None),
]

_AIREAL_PREFIXES = [
    ("ñai", Person.First, Number.Plural, Inclusivity.Inclusive),
    ("jai", Person.First, Number.Plural, Inclusivity.Inclusive),
    ("roi", Person.First, Number.Plural, Inclusivity.Exclusive),
    ("pei", Person.Second, Number.Plural, None),
    ("rei", Person.Second, Number.Singular, None),
    ("oi", Person.Third, Number.Singular, None),
    ("ai", Person.First, Number.Singular, None),
]

_CHENDAL_PREFIXES = [
    ("ñande", Person.First, Number.Plural, Inclusivity.Inclusive),
    ("ñane", Person.First, Number.Plural, Inclusivity.Inclusive),
    ("pende", Person.Second, Number.Plural, None),
    ("pene", Person.Second, Number.Plural, None),
    ("ore", Person.First, Number.Plural, Inclusivity.Exclusive),
    ("che", Person.First, Number.Singular, None),
    ("nde", Person.Second, Number.Singular, None),
    ("ne", Person.Second, Number.Singular, None),
    ("hiñ", Person.Third, Number.Singular, None),
    ("hi", Person.Third, Number.Singular, None),
    ("iñ", Person.Third, Number.Singular, None),
    ("ij", Person.Third, Number.Singular, None),
    ("i", Person.Third, Number.Singular, None),
]

# h-initial irregular paradigm of 'u "eat/drink" (positive forms only; the
# h drops under negation, so nda'ui / ndo'úi already parse via the regular
# prefix path). Maps conjugated-prefix surface -> (root, person, number, incl).
_HFORM_PARADIGM: dict[str, tuple[str, Person, Number, Optional[Inclusivity]]] = {
    "ha'u": ("'u", Person.First, Number.Singular, None),
    "re'u": ("'u", Person.Second, Number.Singular, None),
    "ho'u": ("'u", Person.Third, Number.Singular, None),
    "ja'u": ("'u", Person.First, Number.Plural, Inclusivity.Inclusive),
    "ña'u": ("'u", Person.First, Number.Plural, Inclusivity.Inclusive),
    "ro'u": ("'u", Person.First, Number.Plural, Inclusivity.Exclusive),
    "pe'u": ("'u", Person.Second, Number.Plural, None),
}
for _k, _v in list(_HFORM_PARADIGM.items()):
    _HFORM_PARADIGM.setdefault(_k.replace("'", ""), _v)

_CHENDAL_3SG_PREFIX_TO_FORM = {
    "hi": Chendal3sgForm.C3sg_Hi, "hiñ": Chendal3sgForm.C3sg_Hi,
    "ij": Chendal3sgForm.C3sg_Ij, "iñ": Chendal3sgForm.C3sg_I, "i": Chendal3sgForm.C3sg_I,
}

# Orality-paired person prefixes: the oral series goes with oral roots, the
# nasal series with nasal roots. a-/re-/o-/che-/ore-/pe- etc. are neutral.
_PREFIX_ORALITY = {
    "nde": Orality.Oral, "ñande": Orality.Oral, "pende": Orality.Oral,
    "ne": Orality.Nasal, "ñane": Orality.Nasal, "pene": Orality.Nasal,
    "ja": Orality.Oral, "ña": Orality.Nasal,
    "jai": Orality.Oral, "ñai": Orality.Nasal,
}

_ALL_PREFIX_TABLES = [
    (VerbClass.Areal, _AREAL_PREFIXES),
    (VerbClass.Aireal, _AIREAL_PREFIXES),
    (VerbClass.Chendal, _CHENDAL_PREFIXES),
]

# ===========================================================================
# Segment Stripping Engines
# ===========================================================================

def _strip_postposition(token: str) -> list[tuple[str, Postposition]]:
    results: list[tuple[str, Postposition]] = []
    for surf, pp, _o in POSTPOSITION_STRIP_INDEX:
        if token.endswith(surf) and len(token) > len(surf):
            results.append((token[:-len(surf)], pp))
    return results


def _strip_suffixes(form: str, accumulated: list[VerbalSuffix], results: list[tuple[str, list[VerbalSuffix]]]) -> None:
    if form in _LEXICON or _detilde(form) in _LEXICON:
        results.append((form, list(accumulated)))

    for surface, suffix in SUFFIX_STRIP_INDEX:
        if form.endswith(surface) and len(form) > len(surface):
            remainder = form[:-len(surface)]
            # Allow one repeat of the same suffix so malformed doublings
            # (e.g. nd-...-i-vé-i) still parse and get diagnosed by the
            # Coq predicates instead of dead-ending here.
            if accumulated.count(suffix) < 2:
                _strip_suffixes(remainder, [suffix] + accumulated, results)


def _strip_suffixes_irreg(form: str, accumulated: list[VerbalSuffix], results: list[tuple[str, list[VerbalSuffix]]]) -> None:
    """Like _strip_suffixes, but for irregular verb forms (aha/oho/ha'e and
    their paradigm): the stopping condition is IRREG_FORM_INDEX membership
    (a small closed paradigm) rather than the open regular-verb lexicon.
    render_verb in verb.v does append cv_suffixes to an irregular form's
    rendering (render_verb's VF_Irregular branch), so e.g. "ahaje" (aha +
    hearsay -je) is a real, well-formable string — analyze() just never
    tried stripping suffixes off an irregular form before this. Also tries
    the accent-stripped form of each candidate stem (via _STRIP_ACUTE),
    since e.g. "aha" (unaccented, stress falls on the final syllable by
    default) + "-vo" surfaces as "ahávo" — the stress mark shifts onto the
    new penultimate syllable, so the bare stem needs its accent restored-to-
    none to match the IRREG_FORM_INDEX key "aha"."""
    if form in IRREG_FORM_INDEX:
        results.append((form, list(accumulated)))
    deaccented = form.translate(_STRIP_ACUTE)
    if deaccented != form and deaccented in IRREG_FORM_INDEX:
        results.append((deaccented, list(accumulated)))

    for surface, suffix in SUFFIX_STRIP_INDEX:
        if form.endswith(surface) and len(form) > len(surface):
            remainder = form[:-len(surface)]
            if accumulated.count(suffix) < 2:
                _strip_suffixes_irreg(remainder, [suffix] + accumulated, results)

# ===========================================================================
# Verb Analyzer Engine
# ===========================================================================

@dataclass
class ParseResult:
    conj_verb: ConjugatedVerb
    root: str
    confidence: str


_IMP_MODALIZER_SUFFIXES = {
    VerbalSuffix.VS_ImpForce, VerbalSuffix.VS_ImpRequest,
    VerbalSuffix.VS_ImpPlead, VerbalSuffix.VS_ImpUrge,
}


def _mood_for(suffixes: list[VerbalSuffix]) -> Mood:
    """cv_modalizer_ok requires Imperative or Optative mood whenever an
    imperative modalizer suffix (-ke, -na, -mi, -py) is present. analyze()
    has no surface signal distinguishing Imperative from Optative (Optative
    uses a wholly different prefix set not yet recognized here), so a bare
    modalizer suffix is read as Imperative."""
    if any(s in _IMP_MODALIZER_SUFFIXES for s in suffixes):
        return Mood.Imperative
    return Mood.Indicative


# §6: voice prefixes sit between the person/agreement prefix and the root
# (render_regular_verb: agr_pfx ++ vce_pfx ++ rel_pfx ++ root), so they're
# tried by stripping from the front of after_prefix — the same position
# nd-/n-/ani- are tried by stripping from the front of the whole surface.
# Passive/Reciprocal/Coactive select their surface allomorph the same way
# person prefixes do (root orality, not independently chosen — voice_prefix
# in verb.v is always called with the verb's own orality), so those three
# carry the orality they require; Objective/Obj_Guero/Subsuntive are
# orality-invariant. Sorted longest-first so "guero" is tried before a
# shorter prefix could ever coincidentally match part of it.
_VOICE_PREFIXES: list[tuple[str, Voice, Optional[Orality]]] = sorted([
    ("je", Voice.Passive, Orality.Oral),
    ("ñe", Voice.Passive, Orality.Nasal),
    ("jo", Voice.Reciprocal, Orality.Oral),
    ("ño", Voice.Reciprocal, Orality.Nasal),
    ("mbo", Voice.Coactive, Orality.Oral),
    ("mo", Voice.Coactive, Orality.Nasal),
    ("ro", Voice.Objective, None),
    ("guero", Voice.Obj_Guero, None),
    ("poro", Voice.Subsuntive, None),
], key=lambda t: -len(t[0]))


def _voice_attempts(after_prefix: str) -> list[tuple[Voice, Optional[Orality], str]]:
    """All (voice, required_orality, remainder) readings of the string
    following the person prefix: Active (nothing stripped, no orality
    requirement) plus one per voice prefix that matches. A wrong guess is
    filtered downstream when the remainder fails suffix-stripping + lexicon
    lookup (or the orality check), the same way wrong nd-/n-/ani- guesses
    already are."""
    attempts: list[tuple[Voice, Optional[Orality], str]] = [(Voice.Active, None, after_prefix)]
    for vpfx, voice, o in _VOICE_PREFIXES:
        if after_prefix.startswith(vpfx) and len(after_prefix) > len(vpfx):
            attempts.append((voice, o, after_prefix[len(vpfx):]))
    return attempts


def analyze(surface: str, enforce_orality: bool = True) -> list[ParseResult]:
    surface = _nfc(surface)
    results: list[ParseResult] = []

    # Negative pronouns (avave, mba'eve, ...) are a closed class disjoint from
    # verbs; without this guard, some of them accidentally decompose into a
    # spurious person-prefix + root + suffix reading (e.g. avave = a- + va +
    # -ve), which lets a sentence dodge double-negation concord checking by
    # reparsing the pronoun as the verb.
    if _neg_pron_get(surface) is not None:
        return []

    if surface in IRREG_FORM_INDEX:
        parses = []
        for irreg_verb, person, number, incl in IRREG_FORM_INDEX[surface]:
            cv = ConjugatedVerb(
                verb_form=VF_Irregular(irreg_verb), person=person, number=number,
                incl=incl, mood=Mood.Indicative, polarity=Polarity.Positive, voice=Voice.Active,
            )
            parses.append(ParseResult(cv, surface, "exact_irreg"))
        return parses

    irreg_strip_results: list[tuple[str, list[VerbalSuffix]]] = []
    _strip_suffixes_irreg(surface, [], irreg_strip_results)
    if irreg_strip_results:
        parses = []
        for stem, suffixes in irreg_strip_results:
            for irreg_verb, person, number, incl in IRREG_FORM_INDEX[stem]:
                cv = ConjugatedVerb(
                    verb_form=VF_Irregular(irreg_verb), person=person, number=number,
                    incl=incl, mood=_mood_for(suffixes), polarity=Polarity.Positive,
                    voice=Voice.Active, suffixes=suffixes,
                )
                parses.append(ParseResult(cv, stem, "irreg_suffixed"))
        if parses:
            return parses

    for hform, (hroot, person, number, incl) in _HFORM_PARADIGM.items():
        if not surface.startswith(hform):
            continue
        entry = _LEXICON.get(hroot)
        if entry is None:
            continue
        strip_results: list[tuple[str, list[VerbalSuffix]]] = []
        _strip_suffixes(hroot + surface[len(hform):], [], strip_results)
        for root, suffixes in strip_results:
            if root != hroot:
                continue
            verb = Verb(
                v_class=entry.verb_class, v_orality=entry.orality, v_root=entry.word,
                v_transitivity=entry.transitivity if entry.transitivity is not None else Transitivity.Intransitive,
                v_root_class=entry.root_class, v_chendal_3sg=entry.chendal_3sg,
            )
            cv = ConjugatedVerb(
                verb_form=VF_Regular(verb), person=person, number=number, incl=incl,
                mood=_mood_for(suffixes), polarity=Polarity.Positive, voice=Voice.Active, suffixes=suffixes,
            )
            results.append(ParseResult(cv, entry.word, "exact_hform"))

    # A surface starting nd-/n- + vowel is ambiguous between a negation
    # circumfix (nd-oikuaa-i) and a positive form whose prefix happens to
    # start with n (nde-kane'o), so both readings are attempted.
    attempts: list[tuple[str, Polarity]] = [(surface, Polarity.Positive)]
    for neg_pfx in ("nd", "n"):
        if surface.startswith(neg_pfx):
            after_neg = surface[len(neg_pfx):]
            if after_neg and after_neg[0] in "aeo":
                attempts.append((_strip_neg_accent(after_neg), Polarity.Negative))
                break

    for inner, polarity in attempts:
        for verb_class, prefix_table in _ALL_PREFIX_TABLES:
            for prefix, person, number, incl in prefix_table:
                if not inner.startswith(prefix):
                    continue
                after_prefix = inner[len(prefix):]
                if not after_prefix:
                    continue

                for voice, voice_orality, after_voice in _voice_attempts(after_prefix):
                    strip_results: list[tuple[str, list[VerbalSuffix]]] = []
                    _strip_suffixes(after_voice, [], strip_results)

                    for root, suffixes in strip_results:
                        entry = _lex_get(root)
                        if entry is None or entry.verb_class != verb_class:
                            continue

                        if enforce_orality:
                            required = _PREFIX_ORALITY.get(prefix)
                            if required is not None and surface_orality(entry.word) != required:
                                continue
                            if voice_orality is not None and surface_orality(entry.word) != voice_orality:
                                continue

                        if verb_class == VerbClass.Chendal and person == Person.Third:
                            # r/h-alternating roots form their 3sg as h- (hesarái),
                            # never with an i-/hi- prefix.
                            if entry.root_class == VerbRootClass.VRoot_Relational:
                                continue
                            if prefix in _CHENDAL_3SG_PREFIX_TO_FORM and _CHENDAL_3SG_PREFIX_TO_FORM[prefix] != entry.chendal_3sg:
                                continue

                        verb = Verb(
                            v_class=entry.verb_class, v_orality=entry.orality, v_root=entry.word,
                            v_transitivity=entry.transitivity if entry.transitivity is not None else Transitivity.Intransitive,
                            v_root_class=entry.root_class, v_chendal_3sg=entry.chendal_3sg,
                        )
                        cv = ConjugatedVerb(
                            verb_form=VF_Regular(verb), person=person, number=number, incl=incl,
                            mood=_mood_for(suffixes), polarity=polarity, voice=voice, suffixes=suffixes,
                        )
                        confidence = "prefix_match" if len(strip_results) == 1 else "ambiguous"
                        results.append(ParseResult(cv, root, confidence))

        # Chendal 3sg of r/h-alternating relational roots: the initial r-
        # of the root surfaces as h- (hesarái = 3rd person of resarái).
        if inner.startswith("h") and len(inner) > 1:
            h_strip_results: list[tuple[str, list[VerbalSuffix]]] = []
            _strip_suffixes("r" + inner[1:], [], h_strip_results)
            for root, suffixes in h_strip_results:
                entry = _lex_get(root)
                if (entry is None or entry.verb_class != VerbClass.Chendal
                        or entry.root_class != VerbRootClass.VRoot_Relational):
                    continue
                verb = Verb(
                    v_class=entry.verb_class, v_orality=entry.orality, v_root=entry.word,
                    v_transitivity=entry.transitivity if entry.transitivity is not None else Transitivity.Intransitive,
                    v_root_class=entry.root_class, v_chendal_3sg=entry.chendal_3sg,
                )
                cv = ConjugatedVerb(
                    verb_form=VF_Regular(verb), person=Person.Third, number=Number.Singular, incl=None,
                    mood=_mood_for(suffixes), polarity=polarity, voice=Voice.Active, suffixes=suffixes,
                )
                results.append(ParseResult(cv, entry.word, "chendal_h3"))

        # Chendal 3sg of r/h-alternating relational roots with a voice
        # prefix intervening (e.g. Passive "ijerresarái" = i- + je- +
        # r-resarái, verified against coqc's own render_verb). The h-/r-
        # contraction above only fires when the person prefix sits
        # directly adjacent to the root's r- (Active, no voice prefix in
        # between); once a voice prefix intervenes there's no attested
        # contraction, so the compositional form is the only valid
        # spelling — and unlike the contracted case, that spelling still
        # carries rel_pfx's own leading "r" on top of the lexicon's stored
        # root spelling (verified: the one real VRoot_Relational entry,
        # "resarái", already stores its r- as part of the word itself).
        for c3_prefix, c3_form in _CHENDAL_3SG_PREFIX_TO_FORM.items():
            if not inner.startswith(c3_prefix):
                continue
            after_c3_prefix = inner[len(c3_prefix):]
            for voice, voice_orality, after_voice in _voice_attempts(after_c3_prefix):
                if voice == Voice.Active or not after_voice.startswith("r") or len(after_voice) <= 1:
                    continue
                v_strip_results: list[tuple[str, list[VerbalSuffix]]] = []
                _strip_suffixes(after_voice[1:], [], v_strip_results)
                for root, suffixes in v_strip_results:
                    entry = _lex_get(root)
                    if (entry is None or entry.verb_class != VerbClass.Chendal
                            or entry.root_class != VerbRootClass.VRoot_Relational
                            or entry.chendal_3sg != c3_form):
                        continue
                    if enforce_orality and voice_orality is not None and surface_orality(entry.word) != voice_orality:
                        continue
                    verb = Verb(
                        v_class=entry.verb_class, v_orality=entry.orality, v_root=entry.word,
                        v_transitivity=entry.transitivity if entry.transitivity is not None else Transitivity.Intransitive,
                        v_root_class=entry.root_class, v_chendal_3sg=entry.chendal_3sg,
                    )
                    cv = ConjugatedVerb(
                        verb_form=VF_Regular(verb), person=Person.Third, number=Number.Singular, incl=None,
                        mood=_mood_for(suffixes), polarity=polarity, voice=voice, suffixes=suffixes,
                    )
                    results.append(ParseResult(cv, entry.word, "chendal_h3_voiced"))

    seen: set[str] = set()
    deduped: list[ParseResult] = []
    for r in results:
        key = r.conj_verb.to_coq()
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped

def _strip_suffixes_all(form: str, accumulated: list[VerbalSuffix], results: list[tuple[str, list[VerbalSuffix]]]) -> None:
    """Like _strip_suffixes, but records every intermediate form whether or
    not it is a known root — used for diagnosis, not parsing."""
    results.append((form, list(accumulated)))
    for surface, suffix in SUFFIX_STRIP_INDEX:
        if form.endswith(surface) and len(form) > len(surface):
            if accumulated.count(suffix) < 2:
                _strip_suffixes_all(form[:-len(surface)], [suffix] + accumulated, results)


def _is_known_non_verb(surface: str) -> bool:
    """True if the token has a role other than verb (noun, adjective, pronoun,
    marker, postposition, a noun with an encliticized postposition, or a
    noun/adjective carrying a nominal suffix)."""
    if (_noun_get(surface) is not None or _adj_get(surface) is not None
            or surface in SUBJ_PRONOUN_FORM_INDEX or surface in _DATIVE_PRONOUN_INDEX
            or surface in POSS_MARKER_FORM_INDEX or surface in DEM_ADJ_FORM_INDEX
            or surface in POSTPOSITION_FORM_INDEX or _neg_pron_get(surface) is not None
            or surface in DEM_PRON_FORM_INDEX or surface in INDEF_PRON_FORM_INDEX
            or surface in INTERROG_PRON_FORM_INDEX or surface == "peteĩ"):
        return True
    if any(_noun_get(rem) is not None for rem, _pp in _strip_postposition(surface)):
        return True
    return bool(_noun_readings(surface)) or bool(_adj_readings(surface))


def is_unknown_token(surface: str) -> bool:
    """True when a token matches nothing in the system: not a verb form, not a
    known non-verb word, and carrying no recognizable person prefix."""
    surface = _nfc(surface)
    if analyze(surface) or _is_known_non_verb(surface):
        return False
    for _vc, table in _ALL_PREFIX_TABLES:
        for prefix, *_rest in table:
            if surface.startswith(prefix) and len(surface) > len(prefix):
                return False
    return True


def diagnose_verb_token(surface: str) -> list[str]:
    """Explains why a token failed verb analysis, most specific reason first.
    Returns [] when the token parses as a verb or is a known non-verb word."""
    surface = _nfc(surface)
    if analyze(surface):
        return []
    # Tokens with a known non-verb role (pronouns, nouns, markers, ...) don't
    # need to be verbs; separate-marker mistakes are diagnose_chendal_pair's job.
    if _is_known_non_verb(surface):
        return []

    diags: list[tuple[int, str]] = []
    class_tables = dict(_ALL_PREFIX_TABLES)

    # Wrong oral/nasal prefix series?
    for r in analyze(surface, enforce_orality=False):
        vf = r.conj_verb.verb_form
        if isinstance(vf, VF_Regular):
            root = vf.verb.v_root
            if surface_orality(root) == Orality.Nasal:
                msg = (f"'{surface}': '{root}' is a Nasal root, so it takes the nasal "
                       f"prefix series (ña-, ñai-, ne-, ñane-, pene-).")
            else:
                msg = (f"'{surface}': '{root}' is an Oral root, so it takes the oral "
                       f"prefix series (ja-, jai-, nde-, ñande-, pende-).")
            diags.append((0, msg))

    attempts = [surface]
    for neg_pfx in ("nd", "n"):
        if surface.startswith(neg_pfx):
            after_neg = surface[len(neg_pfx):]
            if after_neg and after_neg[0] in "aeo":
                attempts.append(_strip_neg_accent(after_neg))
                break

    prefix_matched = False
    noun_only_roots: list[str] = []
    unknown_roots: list[str] = []

    for inner in attempts:
        for verb_class, prefix_table in _ALL_PREFIX_TABLES:
            for prefix, person, number, incl in prefix_table:
                if not inner.startswith(prefix):
                    continue
                after_prefix = inner[len(prefix):]
                if not after_prefix:
                    continue
                prefix_matched = True

                strip_results: list[tuple[str, list[VerbalSuffix]]] = []
                _strip_suffixes_all(after_prefix, [], strip_results)
                for root, _suffixes in strip_results:
                    entry = _lex_get(root)
                    if entry is not None and entry.verb_class != verb_class:
                        correct = next(
                            (p for p, per, num, inc in class_tables[entry.verb_class]
                             if per == person and num == number and inc == incl),
                            None,
                        )
                        sugg = f" — did you mean '{correct}{after_prefix}'?" if correct else "."
                        art = "an" if entry.verb_class.value[0] in "AEIOU" else "a"
                        diags.append((1,
                            f"'{surface}': '{entry.word}' is {art} {entry.verb_class.value} verb, "
                            f"but the {prefix}- prefix belongs to the {verb_class.value} class{sugg}"))
                    elif entry is None:
                        if _noun_get(root) is not None or _adj_get(root) is not None:
                            noun_only_roots.append(root)
                        else:
                            unknown_roots.append(root)

    if not diags and noun_only_roots:
        root = max(noun_only_roots, key=len)
        diags.append((2,
            f"'{surface}': the root '{root}' is in the dictionary only as a "
            f"noun/adjective, not as a verb."))
    if not diags and prefix_matched:
        root = max(unknown_roots, key=len) if unknown_roots else surface
        diags.append((3,
            f"'{surface}': a person prefix was recognized, but no dictionary verb "
            f"matches the remaining root (closest attempt: '{root}')."))
    if not diags and not prefix_matched and not _is_known_non_verb(surface):
        diags.append((4, f"'{surface}' is not in the dictionary."))

    diags.sort(key=lambda d: d[0])
    seen: set[str] = set()
    out: list[str] = []
    for _prio, msg in diags:
        if msg not in seen:
            seen.add(msg)
            out.append(msg)
    return out


_CHENDAL_MARKER_SURFACES = {prefix for prefix, _p, _n, _i in _CHENDAL_PREFIXES}


_CHENDAL_MARKER_COUNTERPART = {
    "nde": "ne", "ne": "nde", "ñande": "ñane",
    "ñane": "ñande", "pende": "pene", "pene": "pende",
}


def diagnose_chendal_pair(marker: str, root_tok: str) -> list[str]:
    """Explains a separate-word Chendal marker that fails only because it is
    the wrong oral/nasal series (e.g. 'nde kane'o' for nasal kane'o)."""
    marker, root_tok = _nfc(marker), _nfc(root_tok)
    if analyze_chendal_pair(marker, root_tok):
        return []
    notes: list[str] = []
    for r in analyze_chendal_pair(marker, root_tok, enforce_orality=False):
        vf = r.conj_verb.verb_form
        if isinstance(vf, VF_Regular):
            root = vf.verb.v_root
            o = surface_orality(root).value
            counterpart = _CHENDAL_MARKER_COUNTERPART.get(marker)
            sugg = f" — use '{counterpart} {root_tok}'" if counterpart else ""
            msg = (f"'{marker} {root_tok}': '{root}' is a {o} root, but '{marker}' "
                   f"is the {'Oral' if o == 'Nasal' else 'Nasal'}-series marker{sugg}.")
            if msg not in notes:
                notes.append(msg)
    return notes


def analyze_chendal_pair(marker: str, root_tok: str, enforce_orality: bool = True) -> list[ParseResult]:
    """Parses a Chendal person marker written as a separate word from its
    predicate root (e.g. "che kane'o" = "chekane'o" = 'I am tired')."""
    marker = _nfc(marker)
    if marker not in _CHENDAL_MARKER_SURFACES:
        return []
    return [
        r for r in analyze(marker + _nfc(root_tok), enforce_orality=enforce_orality)
        if isinstance(r.conj_verb.verb_form, VF_Regular)
        and r.conj_verb.verb_form.verb.v_class == VerbClass.Chendal
    ]


def analyze_prohibitive_pair(marker: str, verb_tok: str, enforce_orality: bool = True) -> list[ParseResult]:
    """Parses the prohibitive construction: the free-standing negative-
    imperative particle 'ani' immediately preceding a verb (e.g. "ani reho"
    = "don't go", §4.10.3.1.3). Unlike regular negation, prohibitive doesn't
    use the nd-...-i circumfix — the verb keeps its ordinary agreement
    prefix, and mood/polarity are carried by 'ani' alone, so this reuses the
    verb's Positive-polarity parse and overrides mood/polarity on top of it."""
    if _nfc(marker) != "ani":
        return []
    results: list[ParseResult] = []
    for r in analyze(verb_tok, enforce_orality=enforce_orality):
        if r.conj_verb.polarity != Polarity.Positive:
            continue
        cv = replace(r.conj_verb, mood=Mood.Prohibitive, polarity=Polarity.Negative)
        results.append(ParseResult(cv, r.root, r.confidence))
    return results


# ===========================================================================
# Numeral Analyzer (Numbers.v: Digit/Mult/Teen/Sub100/Sub1000/Sub1000Su/
# GuaraniNum, inverted to build NP_Num)
#
# The Coq render_* family builds a numeral surface by string concatenation:
# a multiplier's rendering (which may itself be multiple space-separated
# tokens, e.g. "sa peteĩ" = 101) gets a suffix ("pa"/"sa"/"su"/"sua") fused
# directly onto its LAST token with no space, and a following remainder (if
# any) is then space-separated after that. Parsing inverts this bottom-up:
# each _parse_subN function tries, at token index i, (a) a fused
# "<multiplier><suffix>" token followed optionally by the next layer down
# (its "tail"), or (b) falling through to the layer below with no
# multiplier. Multi-token multipliers (e.g. "121 thousand") are out of
# scope — real test sentences don't need them, and the grammar itself
# doesn't need it above what covers 1..999,999 plus round thousands/
# hundred-thousands/millions.
# ===========================================================================

_DIGIT_SURFACE = {
    "peteĩ": "Peteĩ", "mokõi": "Mokõi", "mbohapy": "Mbohapy", "irundy": "Irundy",
    "po": "Po", "poteĩ": "Poteĩ", "pokõi": "Pokõi", "poapy": "Poapy", "porundy": "Porundy",
}
_MULT_SURFACE = {
    "mokõi": "MokõiM", "mbohapy": "MbohapyM", "irundy": "IrundyM", "po": "PoM",
    "poteĩ": "PoteĩM", "pokõi": "PokõiM", "poapy": "PoapyM", "porundy": "PorundyM",
}
_TEEN_SURFACE = {
    "pateĩ": "Pateĩ", "pakõi": "Pakõi", "pa'apy": "Pa'apy", "parundy": "Parundy",
    "papo": "Papo", "papoteĩ": "Papoteĩ", "papokõi": "Papokõi", "papoapy": "Papoapy",
    "paporundy": "Paporundy",
}


def _parse_sub100(tokens: list[str], i: int) -> Optional[tuple[str, int]]:
    if i >= len(tokens):
        return None
    tok = tokens[i]
    if tok in _TEEN_SURFACE:
        return f"(S100_Teen {_TEEN_SURFACE[tok]})", i + 1
    if tok == "pa":
        return "S100_Pa", i + 1
    d = _DIGIT_SURFACE.get(tok)
    if d:
        return f"(S100_Digit {d})", i + 1
    if tok.endswith("pa") and len(tok) > 2:
        m = _MULT_SURFACE.get(tok[:-2])
        if m:
            if i + 1 < len(tokens):
                d2 = _DIGIT_SURFACE.get(tokens[i + 1])
                if d2:
                    return f"(S100_MultPaDigit {m} {d2})", i + 2
            return f"(S100_MultPa {m})", i + 1
    return None


def _parse_sub1000(tokens: list[str], i: int) -> Optional[tuple[str, int]]:
    if i >= len(tokens):
        return None
    tok = tokens[i]
    if tok == "sa":
        rest = _parse_sub100(tokens, i + 1)
        if rest:
            s_coq, next_i = rest
            return f"(S1000_SaTail {s_coq})", next_i
        return "S1000_Sa", i + 1
    if tok.endswith("sa") and len(tok) > 2:
        m = _MULT_SURFACE.get(tok[:-2])
        if m:
            rest = _parse_sub100(tokens, i + 1)
            if rest:
                s_coq, next_i = rest
                return f"(S1000_MultSaTail {m} {s_coq})", next_i
            return f"(S1000_MultSa {m})", i + 1
    rest = _parse_sub100(tokens, i)
    if rest:
        s_coq, next_i = rest
        return f"(S1000_Small {s_coq})", next_i
    return None


def _find_fused_multiplier(
    tokens: list[str], start: int, suffix: str,
    sub_parser: "Callable[[list[str], int], Optional[tuple[str, int]]]",
) -> Optional[tuple[str, int]]:
    """S1000Su_MultSu/GN_MultSua's multiplier (Sub1000 / Sub1000Su
    respectively) can itself span multiple tokens — render_sub1000su/
    render_num fuse "su"/"sua" directly onto the LAST token of whatever the
    multiplier renders as (e.g. 121,000 = "sa mokõipa peteĩsu", multiplier
    "sa mokõipa peteĩ" = 121 with "su" fused onto its last token "peteĩ"),
    not just a single-token multiplier. Tries every span starting at
    `start` whose last token ends with `suffix`, parses that span (with
    `suffix` stripped from its last token) via `sub_parser`, and requires
    it to consume the whole (modified) span — i.e. the multiplier is
    exactly this span, nothing more, nothing left over. Returns
    (multiplier_coq, index_after_the_original_span) for the first span
    length that works, or None."""
    n = len(tokens)
    for span_len in range(1, n - start + 1):
        last_idx = start + span_len - 1
        last_tok = tokens[last_idx]
        if not (last_tok.endswith(suffix) and len(last_tok) > len(suffix)):
            continue
        candidate = tokens[start:last_idx] + [last_tok[:-len(suffix)]]
        parsed = sub_parser(candidate, 0)
        if parsed is None:
            continue
        m_coq, m_next = parsed
        if m_next != len(candidate):
            continue
        return m_coq, last_idx + 1
    return None


def _parse_sub1000su(tokens: list[str], i: int) -> Optional[tuple[str, int]]:
    if i >= len(tokens):
        return None
    tok = tokens[i]
    if tok == "su":
        rest = _parse_sub1000(tokens, i + 1)
        if rest:
            s_coq, next_i = rest
            return f"(S1000Su_SuTail {s_coq})", next_i
        return "S1000Su_Su", i + 1
    found = _find_fused_multiplier(tokens, i, "su", _parse_sub1000)
    if found is not None:
        m_coq, after_m = found
        rest = _parse_sub1000(tokens, after_m)
        if rest:
            s_coq, next_i = rest
            return f"(S1000Su_MultSuTail {m_coq} {s_coq})", next_i
        return f"(S1000Su_MultSu {m_coq})", after_m
    rest = _parse_sub1000(tokens, i)
    if rest:
        s_coq, next_i = rest
        return f"(S1000Su_Small {s_coq})", next_i
    return None


def parse_guarani_num(tokens: list[str], i: int = 0) -> Optional[tuple[str, int]]:
    """Parses a GuaraniNum out of tokens starting at i. Returns
    (coq_term, next_index) for the longest reading found, or None if
    tokens[i] doesn't start a recognizable numeral."""
    if i >= len(tokens):
        return None
    norm = [_nfc(t) for t in tokens]
    tok = norm[i]
    if tok == "sua":
        rest = _parse_sub1000su(norm, i + 1)
        if rest:
            s_coq, next_i = rest
            return f"(GN_SuaTail {s_coq})", next_i
        return "GN_Sua", i + 1
    found = _find_fused_multiplier(norm, i, "sua", _parse_sub1000su)
    if found is not None:
        m_coq, after_m = found
        rest = _parse_sub1000su(norm, after_m)
        if rest:
            s_coq, next_i = rest
            return f"(GN_MultSuaTail {m_coq} {s_coq})", next_i
        return f"(GN_MultSua {m_coq})", after_m
    rest = _parse_sub1000su(norm, i)
    if rest:
        s_coq, next_i = rest
        return f"(GN_Small {s_coq})", next_i
    return None


_ONE_GN = parse_guarani_num(["peteĩ"], 0)[0]


def _is_one_num(numeral_coq: str) -> bool:
    return numeral_coq == _ONE_GN


# ===========================================================================
# Noun Phrase (NP) Analyzer Engine
# ===========================================================================

@dataclass
class NPParseResult:
    np: NP
    confidence: str
    num_consumed: int


def analyze_np_span(tokens: list[str], start: int) -> list[NPParseResult]:
    """Generates structural NP parse evaluations across single or multi-token spans."""
    if start >= len(tokens):
        return []

    results: list[NPParseResult] = []
    tok0 = _nfc(tokens[start])

    # Base Cases: Pronoun, dative pronoun, and Bare Noun checks
    pronoun = SUBJ_PRONOUN_FORM_INDEX.get(tok0)
    if pronoun is not None:
        results.append(NPParseResult(
            np=NP(surface=tok0, person=_SUBJ_PRONOUN_PERSON[pronoun], number=_SUBJ_PRONOUN_NUMBER[pronoun], pronoun=pronoun),
            confidence="exact_pronoun", num_consumed=1,
        ))

    dative_pron = _DATIVE_PRONOUN_INDEX.get(tok0)
    if dative_pron is not None and pronoun is None:
        results.append(NPParseResult(
            np=NP(surface=tok0, person=_SUBJ_PRONOUN_PERSON[dative_pron], number=_SUBJ_PRONOUN_NUMBER[dative_pron], pronoun=dative_pron),
            confidence="exact_pronoun", num_consumed=1,
        ))

    entry = _noun_get(tok0)
    for noun_entry_suf, suffixes in _noun_readings(tok0):
        noun = Noun(n_root=noun_entry_suf.word, n_orality=noun_entry_suf.orality, n_ending=word_ending_of(noun_entry_suf.word), n_root_class=noun_entry_suf.root_class, n_human=noun_entry_suf.human)
        is_plural = bool(suffixes) and suffixes[-1] in (NominalSuffix.NS_Plural, NominalSuffix.NS_Multitude)
        results.append(NPParseResult(
            np=NP(surface=tok0, person=Person.Third, number=Number.Plural if is_plural else Number.Singular, human=noun_entry_suf.human, noun=noun, suffixes=suffixes),
            confidence="bare_noun" if not suffixes else "suffixed_noun", num_consumed=1,
        ))

    neg_pron = _neg_pron_get(tok0)
    if neg_pron is not None:
        results.append(NPParseResult(
            np=NP(surface=tok0, person=Person.Third, number=Number.Singular, neg_pron=neg_pron),
            confidence="neg_pron", num_consumed=1,
        ))

    # NP_PronDem: standalone "-va"-nominalized demonstrative pronoun
    # ("kóva" = "this one"), distinct from the DEM_ADJ "ko + noun" pattern.
    for dp, dem_num in DEM_PRON_FORM_INDEX.get(tok0, []):
        results.append(NPParseResult(
            np=NP(surface=tok0, person=Person.Third, number=dem_num, dem_pronoun=dp),
            confidence="dem_pronoun", num_consumed=1,
        ))

    # NP_PronIndef: standalone indefinite pronoun (maymáva, opáva, ...).
    indef = INDEF_PRON_FORM_INDEX.get(tok0)
    if indef is not None:
        results.append(NPParseResult(
            np=NP(surface=tok0, person=Person.Third, number=indef_pron_number(indef),
                  human=indef in INDEF_PRON_HUMAN, indef_pron=indef),
            confidence="indef_pron", num_consumed=1,
        ))

    # NP_PronInterrog: standalone interrogative pronoun (mba'e, máva, ...).
    interrog = INTERROG_PRON_FORM_INDEX.get(tok0)
    if interrog is not None:
        results.append(NPParseResult(
            np=NP(surface=tok0, person=Person.Third, number=Number.Singular,
                  human=interrog in INTERROG_PRON_HUMAN, interrog_pron=interrog),
            confidence="interrog_pron", num_consumed=1,
        ))

    # Indef_PeteiMbae ("peteĩ mba'e") is the one indefinite pronoun whose
    # surface is two words, so it needs its own span check.
    if start + 1 < len(tokens) and tok0 == "peteĩ" and _nfc(tokens[start + 1]) == "mba'e":
        results.append(NPParseResult(
            np=NP(surface="peteĩ mba'e", person=Person.Third, number=Number.Singular,
                  indef_pron=IndefPron.Indef_PeteiMbae),
            confidence="indef_pron", num_consumed=2,
        ))

    # NP_Comp: a complement clause is just a verb carrying the -ha
    # nominalizer (VS_NomHa), e.g. "oguatáha" = "the act of walking".
    # is_comp_clause only checks for the suffix, so every verb parse of
    # tok0 that happens to carry VS_NomHa qualifies.
    for comp_pr in analyze(tokens[start]):
        if VerbalSuffix.VS_NomHa in comp_pr.conj_verb.suffixes:
            results.append(NPParseResult(
                np=NP(
                    surface=tok0, person=Person.Third, number=Number.Singular, human=False,
                    coq_term=f"(NP_Comp {comp_pr.conj_verb.to_coq()})",
                ),
                confidence="comp_clause", num_consumed=1,
            ))

    # NP_Rel: a relative clause is a head noun followed by a verb carrying
    # the -va nominalizer (VS_NomVa), e.g. "kuñataĩ oguatáva" = "the girl
    # who walks". is_rel_clause only checks for the suffix. NP_Rel's first
    # argument is a raw `noun` record, not a guarani_np, so (unlike every
    # other noun-headed construction here) it structurally cannot carry a
    # nominal suffix — only the bare exact match applies.
    if start + 1 < len(tokens) and entry is not None:
        rel_noun = Noun(n_root=entry.word, n_orality=entry.orality, n_ending=word_ending_of(entry.word), n_root_class=entry.root_class, n_human=entry.human)
        for rel_pr in analyze(tokens[start + 1]):
            if VerbalSuffix.VS_NomVa in rel_pr.conj_verb.suffixes:
                results.append(NPParseResult(
                    np=NP(
                        surface=f"{tok0} {tokens[start + 1]}", person=Person.Third, number=Number.Singular,
                        human=entry.human,
                        coq_term=f"(NP_Rel {rel_noun.to_coq()} {rel_pr.conj_verb.to_coq()})",
                    ),
                    confidence="rel_clause", num_consumed=2,
                ))

    # Binary Spans: Multi-token evaluations
    if start + 1 < len(tokens):
        tok1 = _nfc(tokens[start + 1])
        # A nominal suffix fuses onto the LAST token of the inner NP's own
        # rendering; for NP_Poss/NP_Dem that's the noun (tok1) since both
        # render as "marker noun", so every suffixed reading of tok1 is
        # tried too (e.g. "che mitãnguéra" = "my children").
        noun_readings_2 = _noun_readings(tok1)

        # NP_Poss Assignment
        if tok0 in POSS_MARKER_FORM_INDEX:
            for pm, _o in POSS_MARKER_FORM_INDEX[tok0]:
                for noun_entry_2r, suffixes in noun_readings_2:
                    noun = Noun(n_root=noun_entry_2r.word, n_orality=noun_entry_2r.orality, n_ending=word_ending_of(noun_entry_2r.word), n_root_class=noun_entry_2r.root_class, n_human=noun_entry_2r.human)
                    is_plural = bool(suffixes) and suffixes[-1] in (NominalSuffix.NS_Plural, NominalSuffix.NS_Multitude)
                    results.append(NPParseResult(
                        np=NP(surface=f"{tok0} {tok1}", person=Person.Third, number=Number.Plural if is_plural else Number.Singular, human=noun_entry_2r.human, noun=noun, possessor=pm, suffixes=suffixes),
                        confidence="poss_noun", num_consumed=2,
                    ))

        # NP_Dem Assignment
        if tok0 in DEM_ADJ_FORM_INDEX:
            for dp, dem_num in DEM_ADJ_FORM_INDEX[tok0]:
                for noun_entry_2r, suffixes in noun_readings_2:
                    noun = Noun(n_root=noun_entry_2r.word, n_orality=noun_entry_2r.orality, n_ending=word_ending_of(noun_entry_2r.word), n_root_class=noun_entry_2r.root_class, n_human=noun_entry_2r.human)
                    results.append(NPParseResult(
                        np=NP(surface=f"{tok0} {tok1}", person=Person.Third, number=dem_num, human=noun_entry_2r.human, noun=noun, demonstrative=dp, suffixes=suffixes),
                        confidence="dem_noun", num_consumed=2,
                    ))

        # NP_Adj Assignment. render_np(NP_Adj) = noun ++ " " ++ adj, so
        # unlike NP_Poss/NP_Dem/NP_Num a nominal suffix fuses onto the
        # ADJECTIVE (tok1), not the noun — _adj_readings tries both the
        # bare adjective and every suffix-stripped reading of it.
        if entry is not None:
            for adj_entry, adj_suffixes in _adj_readings(tok1):
                noun = Noun(n_root=entry.word, n_orality=entry.orality, n_ending=word_ending_of(entry.word), n_root_class=entry.root_class, n_human=entry.human)
                adj = Adjective(a_form=adj_entry.word, a_orality=adj_entry.orality, a_root_class=RootClass.Uniform)
                results.append(NPParseResult(
                    np=NP(surface=f"{tok0} {tok1}", person=Person.Third, number=Number.Singular, human=entry.human, noun=noun, adjective=adj, suffixes=adj_suffixes),
                    confidence="noun_adj" if not adj_suffixes else "noun_adj_suffixed", num_consumed=2,
                ))

    # Ternary Spans: possessor + noun + adjective ("che jagua michi" = "my
    # little dog"). guarani_np has no constructor combining NP_Poss and
    # NP_Adj on one noun, but none of the well-formedness predicates inspect
    # an NP's adjective (only person/number/orality/human), so this still
    # renders to Coq as plain NP_Poss (dropping the adjective, exactly as if
    # it weren't there) while keeping person/number agreement correct and
    # the adjective in the surface/display data.
    if start + 2 < len(tokens):
        tok1 = _nfc(tokens[start + 1])
        tok2 = _nfc(tokens[start + 2])
        noun_entry_2 = _noun_get(tok1)
        adj_entry_2 = _adj_get(tok2)
        if tok0 in POSS_MARKER_FORM_INDEX and noun_entry_2 is not None and adj_entry_2 is not None:
            for pm, _o in POSS_MARKER_FORM_INDEX[tok0]:
                noun = Noun(n_root=noun_entry_2.word, n_orality=noun_entry_2.orality, n_ending=word_ending_of(noun_entry_2.word), n_root_class=noun_entry_2.root_class, n_human=noun_entry_2.human)
                adj = Adjective(a_form=adj_entry_2.word, a_orality=adj_entry_2.orality, a_root_class=RootClass.Uniform)
                results.append(NPParseResult(
                    np=NP(surface=f"{tok0} {tok1} {tok2}", person=Person.Third, number=Number.Singular, human=noun_entry_2.human, noun=noun, possessor=pm, adjective=adj),
                    confidence="poss_noun_adj", num_consumed=3,
                ))

    # Numeral Span: cardinal number (1+ tokens) + noun ("mokõi kavaju" =
    # "two horses"). Variable-width, so unlike the fixed binary/ternary
    # spans above this uses parse_guarani_num's own token count.
    num_result = parse_guarani_num(tokens, start)
    if num_result is not None:
        numeral_coq, noun_idx = num_result
        if noun_idx < len(tokens):
            for noun_entry_num, suffixes in _noun_readings(_nfc(tokens[noun_idx])):
                noun = Noun(n_root=noun_entry_num.word, n_orality=noun_entry_num.orality, n_ending=word_ending_of(noun_entry_num.word), n_root_class=noun_entry_num.root_class, n_human=noun_entry_num.human)
                number = Number.Singular if _is_one_num(numeral_coq) else Number.Plural
                results.append(NPParseResult(
                    np=NP(
                        surface=" ".join(tokens[start:noun_idx + 1]), person=Person.Third, number=number,
                        human=noun_entry_num.human, noun=noun, numeral_coq=numeral_coq, suffixes=suffixes,
                    ),
                    confidence="numeral_noun", num_consumed=noun_idx + 1 - start,
                ))

    # NP_Gen: a full NP as possessor, immediately followed by the possessed
    # noun ("Maria ajaka" = "Maria's basket"), as opposed to NP_Poss's
    # closed che/nde/i/... marker set. Any NP already found to start at
    # `start` (pronoun, bare/suffixed noun, numeral+noun, poss+noun, ...) is
    # a valid possessor per wf_np's `NP_Gen poss _ => wf_np poss`. Snapshot
    # `results` BEFORE this block runs (not a fresh recursive
    # analyze_np_span call) so this can't recurse into itself.
    for poss_result in list(results):
        noun_idx = start + poss_result.num_consumed
        if noun_idx >= len(tokens):
            continue
        for noun_entry_gen, suffixes in _noun_readings(_nfc(tokens[noun_idx])):
            noun = Noun(n_root=noun_entry_gen.word, n_orality=noun_entry_gen.orality, n_ending=word_ending_of(noun_entry_gen.word), n_root_class=noun_entry_gen.root_class, n_human=noun_entry_gen.human)
            is_plural = bool(suffixes) and suffixes[-1] in (NominalSuffix.NS_Plural, NominalSuffix.NS_Multitude)
            results.append(NPParseResult(
                np=NP(
                    surface=f"{poss_result.np.surface} {tokens[noun_idx]}", person=Person.Third,
                    number=Number.Plural if is_plural else Number.Singular, human=noun_entry_gen.human,
                    noun=noun, gen_possessor=poss_result.np, suffixes=suffixes,
                ),
                confidence="gen_noun", num_consumed=poss_result.num_consumed + 1,
            ))

    # NP_CoordHa/NP_CoordTera: "X ha Y" ("X and Y") / "X térã Y" ("X or Y")
    # joining two full NPs. The left side reuses the `results` snapshot (as
    # NP_Gen does, to avoid recursing analyze_np_span into itself at the
    # same start); the right side is a fresh analyze_np_span call at a
    # strictly later index, so it terminates and — as a side effect —
    # naturally handles chained coordination ("X ha Y ha Z") right-
    # recursively without extra code.
    _COORD_CTOR = {"ha": "NP_CoordHa", "térã": "NP_CoordTera"}
    for left_pr in list(results):
        coord_idx = start + left_pr.num_consumed
        if coord_idx >= len(tokens):
            continue
        ctor = _COORD_CTOR.get(_nfc(tokens[coord_idx]))
        if ctor is None:
            continue
        right_start = coord_idx + 1
        for right_pr in analyze_np_span(tokens, right_start):
            number = Number.Plural if ctor == "NP_CoordHa" else right_pr.np.number
            results.append(NPParseResult(
                np=NP(
                    surface=f"{left_pr.np.surface} {tokens[coord_idx]} {right_pr.np.surface}",
                    person=Person.Third, number=number,
                    coq_term=f"({ctor} {left_pr.np.to_coq()} {right_pr.np.to_coq()})",
                ),
                confidence="np_coord", num_consumed=left_pr.num_consumed + 1 + right_pr.num_consumed,
            ))

    return results


def analyze_np(surface: str) -> list[NPParseResult]:
    return analyze_np_span([surface], 0)