"""
types.py

Python mirror of the Coq types (Primitives.v, Verb.v, Sentences.v).
Each class has a to_coq() method that produces the exact Coq constructor string.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ========================= Primitives =========================

class Orality(Enum):
    Oral = "Oral"
    Nasal = "Nasal"

    def to_coq(self) -> str:
        return self.value


class Person(Enum):
    First = "First"
    Second = "Second"
    Third = "Third"

    def to_coq(self) -> str:
        return self.value


class WordEnding(Enum):
    EndAEO = "EndAEO"
    EndIUY = "EndIUY"

    def to_coq(self) -> str:
        return self.value


class RootClass(Enum):
    Uniform = "Uniform"
    Triform = "Triform"
    TriformNoT = "TriformNoT"
    Biform = "Biform"
    Quadriform = "Quadriform"

    def to_coq(self) -> str:
        return self.value


def deglottalize(s: str) -> str:
    """Apostrophe-stripped variant of a surface form, so input that lost its
    saltillo (e.g. shell-eaten quotes: mandi'o -> mandio) still matches."""
    return s.replace("'", "")


def word_ending_of(root: str) -> WordEnding:
    if not root:
        return WordEnding.EndAEO
    return WordEnding.EndIUY if root[-1] in "iuyĩũỹ" else WordEnding.EndAEO


@dataclass
class Noun:
    n_root: str
    n_orality: Orality
    n_ending: WordEnding
    n_root_class: RootClass = RootClass.Uniform
    n_human: bool = False

    def to_coq(self) -> str:
        return (
            f"(mkNoun \"{self.n_root}\" {self.n_orality.to_coq()} "
            f"{self.n_ending.to_coq()} {self.n_root_class.to_coq()} "
            f"{'true' if self.n_human else 'false'})"
        )


class Number(Enum):
    Singular = "Singular"
    Plural = "Plural"

    def to_coq(self) -> str:
        return self.value


class Inclusivity(Enum):
    Inclusive = "Inclusive"
    Exclusive = "Exclusive"

    def to_coq(self) -> str:
        return self.value


class PossMarker(Enum):
    Poss1 = "Poss1"
    Poss2 = "Poss2"
    Poss3 = "Poss3"
    Poss1Incl = "Poss1Incl"
    Poss1Excl = "Poss1Excl"
    Poss2Pl = "Poss2Pl"
    Poss3Pl = "Poss3Pl"

    def to_coq(self) -> str:
        return self.value


POSS_MARKER_SURFACE = {
    (PossMarker.Poss1, Orality.Oral): "che",
    (PossMarker.Poss1, Orality.Nasal): "che",
    (PossMarker.Poss2, Orality.Oral): "nde",
    (PossMarker.Poss2, Orality.Nasal): "ne",
    (PossMarker.Poss3, Orality.Oral): "i",
    (PossMarker.Poss3, Orality.Nasal): "iñ",
    (PossMarker.Poss1Incl, Orality.Oral): "ñánde",
    (PossMarker.Poss1Incl, Orality.Nasal): "ñáne",
    (PossMarker.Poss1Excl, Orality.Oral): "ore",
    (PossMarker.Poss1Excl, Orality.Nasal): "ore",
    (PossMarker.Poss2Pl, Orality.Oral): "pénde",
    (PossMarker.Poss2Pl, Orality.Nasal): "péne",
    (PossMarker.Poss3Pl, Orality.Oral): "i",
    (PossMarker.Poss3Pl, Orality.Nasal): "iñ",
}

POSS_MARKER_FORM_INDEX = {}
for (pm, o), surf in POSS_MARKER_SURFACE.items():
    POSS_MARKER_FORM_INDEX.setdefault(surf, []).append((pm, o))

_POSS_MARKER_PERSON = {
    PossMarker.Poss1: Person.First, PossMarker.Poss1Incl: Person.First,
    PossMarker.Poss1Excl: Person.First,
    PossMarker.Poss2: Person.Second, PossMarker.Poss2Pl: Person.Second,
    PossMarker.Poss3: Person.Third, PossMarker.Poss3Pl: Person.Third,
}

_POSS_MARKER_NUMBER = {
    PossMarker.Poss1: Number.Singular, PossMarker.Poss2: Number.Singular,
    PossMarker.Poss3: Number.Singular,
    PossMarker.Poss1Incl: Number.Plural, PossMarker.Poss1Excl: Number.Plural,
    PossMarker.Poss2Pl: Number.Plural, PossMarker.Poss3Pl: Number.Plural,
}

_POSS_MARKER_INCLUSIVITY = {
    PossMarker.Poss1Incl: Inclusivity.Inclusive,
    PossMarker.Poss1Excl: Inclusivity.Exclusive,
    PossMarker.Poss1: None, PossMarker.Poss2: None, PossMarker.Poss3: None,
    PossMarker.Poss2Pl: None, PossMarker.Poss3Pl: None,
}


class SubjPronoun(Enum):
    Subj1SG = "Subj1SG"
    Subj2SG = "Subj2SG"
    Subj3SG = "Subj3SG"
    Subj1PL_INCL = "Subj1PL_INCL"
    Subj1PL_EXCL = "Subj1PL_EXCL"
    Subj2PL = "Subj2PL"
    Subj3PL = "Subj3PL"

    def to_coq(self) -> str:
        return self.value


_SUBJ_PRONOUN_SURFACE = {
    SubjPronoun.Subj1SG: "che",
    SubjPronoun.Subj2SG: "nde",
    SubjPronoun.Subj3SG: "ha'e",
    SubjPronoun.Subj1PL_INCL: "ñande",
    SubjPronoun.Subj1PL_EXCL: "ore",
    SubjPronoun.Subj2PL: "peẽ",
    SubjPronoun.Subj3PL: "ha'ekuéra",
}

_SUBJ_PRONOUN_PERSON = {
    SubjPronoun.Subj1SG: Person.First,
    SubjPronoun.Subj1PL_INCL: Person.First,
    SubjPronoun.Subj1PL_EXCL: Person.First,
    SubjPronoun.Subj2SG: Person.Second,
    SubjPronoun.Subj2PL: Person.Second,
    SubjPronoun.Subj3SG: Person.Third,
    SubjPronoun.Subj3PL: Person.Third,
}

_SUBJ_PRONOUN_NUMBER = {
    SubjPronoun.Subj1SG: Number.Singular,
    SubjPronoun.Subj2SG: Number.Singular,
    SubjPronoun.Subj3SG: Number.Singular,
    SubjPronoun.Subj1PL_INCL: Number.Plural,
    SubjPronoun.Subj1PL_EXCL: Number.Plural,
    SubjPronoun.Subj2PL: Number.Plural,
    SubjPronoun.Subj3PL: Number.Plural,
}

SUBJ_PRONOUN_FORM_INDEX = {surf: p for p, surf in _SUBJ_PRONOUN_SURFACE.items()}
for _p, _surf in _SUBJ_PRONOUN_SURFACE.items():
    SUBJ_PRONOUN_FORM_INDEX.setdefault(deglottalize(_surf), _p)


# §3.5.3 "all require double negation on the verb" — mirrors Coq's neg_pron.
class NegPron(Enum):
    NegPron_Mbaeve = "NegPron_Mbaeve"
    NegPron_Avave = "NegPron_Avave"
    NegPron_NiPetei = "NegPron_NiPetei"
    NegPron_Mamove = "NegPron_Mamove"
    NegPron_Arakeve = "NegPron_Arakeve"
    NegPron_Maramo = "NegPron_Maramo"

    def to_coq(self) -> str:
        return self.value


NEG_PRON_SURFACE = {
    NegPron.NegPron_Mbaeve: "mba'eve",
    NegPron.NegPron_Avave: "avave",
    NegPron.NegPron_NiPetei: "ni peteĩ",
    NegPron.NegPron_Mamove: "mamove",
    NegPron.NegPron_Arakeve: "araka'eve",
    NegPron.NegPron_Maramo: "máramo",
}
NEG_PRON_FORM_INDEX = {surf: np for np, surf in NEG_PRON_SURFACE.items()}
for _np, _surf in NEG_PRON_SURFACE.items():
    NEG_PRON_FORM_INDEX.setdefault(deglottalize(_surf), _np)


@dataclass
class Adjective:
    a_form: str
    a_orality: Orality
    a_root_class: RootClass = RootClass.Uniform

    def to_coq(self) -> str:
        return (
            f"(mkAdj \"{self.a_form}\" {self.a_orality.to_coq()} "
            f"{self.a_root_class.to_coq()})"
        )


# ========================= Verbs =========================

class VerbClass(Enum):
    Areal = "Areal"
    Aireal = "Aireal"
    Chendal = "Chendal"

    def to_coq(self) -> str:
        return self.value


class Transitivity(Enum):
    Intransitive = "Intransitive"
    Transitive = "Transitive"
    Ditransitive = "Ditransitive"
    PostpComplement = "PostpComplement"

    def to_coq(self) -> str:
        return self.value


class VerbRootClass(Enum):
    VRoot_Plain = "VRoot_Plain"
    VRoot_Relational = "VRoot_Relational"

    def to_coq(self) -> str:
        return self.value


class Chendal3sgForm(Enum):
    C3sg_I = "C3sg_I"
    C3sg_Hi = "C3sg_Hi"
    C3sg_Ij = "C3sg_Ij"

    def to_coq(self) -> str:
        return self.value


class Voice(Enum):
    Active = "Active"
    Passive = "Passive"
    Reciprocal = "Reciprocal"
    Coactive = "Coactive"
    Objective = "Objective"
    Obj_Guero = "Obj_Guero"
    Subsuntive = "Subsuntive"

    def to_coq(self) -> str:
        return self.value


class Mood(Enum):
    Indicative = "Indicative"
    Imperative = "Imperative"
    Optative = "Optative"
    Prohibitive = "Prohibitive"

    def to_coq(self) -> str:
        return self.value


class Polarity(Enum):
    Positive = "Positive"
    Negative = "Negative"

    def to_coq(self) -> str:
        return self.value


# §7: evidentiality clitics. Most have free distribution in the clause, so
# (per verb.v's own comment) they're modeled as a single optional field on
# conjugated_verb rather than as a verbal suffix — the one exception, -je
# (hearsay), is an unstressed suffix and lives in VerbalSuffix as VS_HearsayJe.
class EvidentialMarker(Enum):
    Ev_Voi = "Ev_Voi"
    Ev_Niko = "Ev_Niko"
    Ev_Ndaje = "Ev_Ndaje"
    Ev_Jeko = "Ev_Jeko"
    Ev_NandEko = "Ev_NandEko"
    Ev_Kuri = "Ev_Kuri"
    Ev_Rae = "Ev_Rae"
    Ev_Rakae = "Ev_Rakae"
    Ev_MboRae = "Ev_MboRae"
    Ev_Nipo = "Ev_Nipo"
    Ev_Hina = "Ev_Hina"

    def to_coq(self) -> str:
        return self.value


# The four =niko/=ko/=ngo/=ningo surface variants are in free variation
# (§7.1); Coq models them as one constructor (Ev_Niko) with this sub-type
# for rendering.
class NikoVariant(Enum):
    NK_Niko = "NK_Niko"
    NK_Ko = "NK_Ko"
    NK_Ngo = "NK_Ngo"
    NK_Ningo = "NK_Ningo"

    def to_coq(self) -> str:
        return self.value


@dataclass
class Evidential:
    marker: EvidentialMarker
    niko_variant: Optional[NikoVariant] = None

    def to_coq(self) -> str:
        niko_coq = f"(Some {self.niko_variant.to_coq()})" if self.niko_variant else "None"
        return f"(mkEvidential {self.marker.to_coq()} {niko_coq})"


_EVIDENTIAL_SURFACE: dict[tuple[EvidentialMarker, Optional[NikoVariant]], str] = {
    (EvidentialMarker.Ev_Voi, None): "voi",
    (EvidentialMarker.Ev_Niko, NikoVariant.NK_Niko): "niko",
    (EvidentialMarker.Ev_Niko, NikoVariant.NK_Ko): "ko",
    (EvidentialMarker.Ev_Niko, NikoVariant.NK_Ngo): "ngo",
    (EvidentialMarker.Ev_Niko, NikoVariant.NK_Ningo): "ningo",
    (EvidentialMarker.Ev_Ndaje, None): "ndaje",
    (EvidentialMarker.Ev_Jeko, None): "jeko",
    (EvidentialMarker.Ev_NandEko, None): "ñandeko",
    (EvidentialMarker.Ev_Kuri, None): "kuri",
    (EvidentialMarker.Ev_Rae, None): "ra'e",
    (EvidentialMarker.Ev_Rakae, None): "raka'e",
    (EvidentialMarker.Ev_MboRae, None): "mbora'e",
    (EvidentialMarker.Ev_Nipo, None): "nipo",
    (EvidentialMarker.Ev_Hina, None): "hína",
}

# Surface -> Evidential lookup, for parsing a particle token. Note: bare "ko"
# (the niko-variant) is also the demonstrative adjective marker (see
# DEM_ADJ_FORM_INDEX below, e.g. "ko karai" = "this man") — the two can't be
# told apart from the surface form alone, so loop.py's strip_evidential()
# only trusts "ko" as evidential when it's the last token in the sentence (a
# demonstrative is always prenominal, so it can never be sentence-final).
EVIDENTIAL_FORM_INDEX: dict[str, Evidential] = {
    surf: Evidential(marker=m, niko_variant=nv)
    for (m, nv), surf in _EVIDENTIAL_SURFACE.items()
}


class VerbalSuffix(Enum):
    VS_CausUka = "VS_CausUka"
    VS_AbilKuaa = "VS_AbilKuaa"
    VS_TotalPa = "VS_TotalPa"
    VS_ImpForce = "VS_ImpForce"
    VS_ImpRequest = "VS_ImpRequest"
    VS_ImpPlead = "VS_ImpPlead"
    VS_ImpUrge = "VS_ImpUrge"
    VS_Volitive = "VS_Volitive"
    VS_ComparVe = "VS_ComparVe"
    VS_FutTa = "VS_FutTa"
    VS_FutNe = "VS_FutNe"
    VS_FutNegMoa = "VS_FutNegMoa"
    VS_ImmFutPota = "VS_ImmFutPota"
    VS_ObligVaera = "VS_ObligVaera"
    VS_PastVaekue = "VS_PastVaekue"
    VS_NegI = "VS_NegI"
    VS_NegRi = "VS_NegRi"
    VS_NegTei = "VS_NegTei"
    VS_Privative = "VS_Privative"
    VS_Intensifier = "VS_Intensifier"
    VS_NomVa = "VS_NomVa"
    VS_NomHa = "VS_NomHa"
    VS_AspectMa = "VS_AspectMa"
    VS_IterJevy = "VS_IterJevy"
    VS_HabitMi = "VS_HabitMi"
    VS_HabitVa = "VS_HabitVa"
    VS_FrustrRei = "VS_FrustrRei"
    VS_InterrogPa = "VS_InterrogPa"
    VS_Desiderative = "VS_Desiderative"
    VS_Simultaneous = "VS_Simultaneous"
    VS_HearsayJe = "VS_HearsayJe"

    def to_coq(self) -> str:
        return self.value

    @property
    def slot(self) -> int:
        return _SUFFIX_SLOTS[self]

    @property
    def surface(self):
        return _SUFFIX_SURFACES[self]

    def render(self, orality: Orality) -> str:
        s = _SUFFIX_SURFACES[self]
        if isinstance(s, dict):
            return s[orality]
        return s


_SUFFIX_SLOTS = {
    VerbalSuffix.VS_CausUka: 1,
    VerbalSuffix.VS_AbilKuaa: 2,
    VerbalSuffix.VS_TotalPa: 3,
    VerbalSuffix.VS_ImpForce: 4,
    VerbalSuffix.VS_ImpRequest: 4,
    VerbalSuffix.VS_ImpPlead: 4,
    VerbalSuffix.VS_ImpUrge: 4,
    VerbalSuffix.VS_Volitive: 5,
    VerbalSuffix.VS_ComparVe: 6,
    VerbalSuffix.VS_FutTa: 7,
    VerbalSuffix.VS_FutNe: 7,
    VerbalSuffix.VS_FutNegMoa: 7,
    VerbalSuffix.VS_ImmFutPota: 7,
    VerbalSuffix.VS_ObligVaera: 7,
    VerbalSuffix.VS_PastVaekue: 7,
    VerbalSuffix.VS_NegI: 8,
    VerbalSuffix.VS_NegRi: 8,
    VerbalSuffix.VS_NegTei: 8,
    VerbalSuffix.VS_Privative: 8,
    VerbalSuffix.VS_Intensifier: 9,
    VerbalSuffix.VS_NomVa: 10,
    VerbalSuffix.VS_NomHa: 10,
    VerbalSuffix.VS_AspectMa: 11,
    VerbalSuffix.VS_IterJevy: 11,
    VerbalSuffix.VS_HabitMi: 11,
    VerbalSuffix.VS_HabitVa: 11,
    VerbalSuffix.VS_FrustrRei: 11,
    VerbalSuffix.VS_Desiderative: 11,
    VerbalSuffix.VS_Simultaneous: 11,
    VerbalSuffix.VS_InterrogPa: 12,
    VerbalSuffix.VS_HearsayJe: 13,
}

_SUFFIX_SURFACES = {
    VerbalSuffix.VS_CausUka: "uka",
    VerbalSuffix.VS_AbilKuaa: "kuaa",
    VerbalSuffix.VS_TotalPa: {Orality.Oral: "pa", Orality.Nasal: "mba"},
    VerbalSuffix.VS_ImpForce: "ke",
    VerbalSuffix.VS_ImpRequest: "na",
    VerbalSuffix.VS_ImpPlead: "mi",
    VerbalSuffix.VS_ImpUrge: "py",
    VerbalSuffix.VS_Volitive: "se",
    VerbalSuffix.VS_ComparVe: "ve",
    VerbalSuffix.VS_FutTa: "ta",
    VerbalSuffix.VS_FutNe: "ne",
    VerbalSuffix.VS_FutNegMoa: "mo'ã",
    VerbalSuffix.VS_ImmFutPota: {Orality.Oral: "pota", Orality.Nasal: "mbota"},
    VerbalSuffix.VS_ObligVaera: "va'erã",
    VerbalSuffix.VS_PastVaekue: "va'ekue",
    VerbalSuffix.VS_NegI: "i",
    VerbalSuffix.VS_NegRi: "ri",
    VerbalSuffix.VS_NegTei: "tei",
    VerbalSuffix.VS_Privative: "'ỹ",
    VerbalSuffix.VS_Intensifier: {Orality.Oral: "ite", Orality.Nasal: "ete"},
    VerbalSuffix.VS_NomVa: "va",
    VerbalSuffix.VS_NomHa: "ha",
    VerbalSuffix.VS_AspectMa: "ma",
    VerbalSuffix.VS_IterJevy: "jevy",
    VerbalSuffix.VS_HabitMi: "mi",
    VerbalSuffix.VS_HabitVa: "va",
    VerbalSuffix.VS_FrustrRei: "rei",
    VerbalSuffix.VS_InterrogPa: "pa",
    VerbalSuffix.VS_Desiderative: "nga'u",
    VerbalSuffix.VS_Simultaneous: "vo",
    VerbalSuffix.VS_HearsayJe: "je",
}

_SUFFIX_STRIP_PAIRS: set[tuple[str, "VerbalSuffix"]] = set()
for _suf, _surf in _SUFFIX_SURFACES.items():
    for _form in ([_surf] if isinstance(_surf, str) else list(_surf.values())):
        _SUFFIX_STRIP_PAIRS.add((_form, _suf))
        _SUFFIX_STRIP_PAIRS.add((deglottalize(_form), _suf))

SUFFIX_STRIP_INDEX = sorted(_SUFFIX_STRIP_PAIRS, key=lambda t: -len(t[0]))


class IrregularVerb(Enum):
    Irreg_Ju = "Irreg_Ju"
    Irreg_Ho = "Irreg_Ho"
    Irreg_E = "Irreg_E"

    def to_coq(self) -> str:
        return self.value


IRREG_PARADIGM = {
    (IrregularVerb.Irreg_Ju, Person.First, Number.Singular, None): "aju",
    (IrregularVerb.Irreg_Ju, Person.Second, Number.Singular, None): "reju",
    (IrregularVerb.Irreg_Ju, Person.Third, Number.Singular, None): "ou",
    (IrregularVerb.Irreg_Ju, Person.Third, Number.Plural, None): "ou",
    (IrregularVerb.Irreg_Ju, Person.First, Number.Plural, Inclusivity.Inclusive): "jaju",
    (IrregularVerb.Irreg_Ju, Person.First, Number.Plural, Inclusivity.Exclusive): "roju",
    (IrregularVerb.Irreg_Ju, Person.Second, Number.Plural, None): "peju",

    (IrregularVerb.Irreg_Ho, Person.First, Number.Singular, None): "aha",
    (IrregularVerb.Irreg_Ho, Person.Second, Number.Singular, None): "reho",
    (IrregularVerb.Irreg_Ho, Person.Third, Number.Singular, None): "oho",
    (IrregularVerb.Irreg_Ho, Person.Third, Number.Plural, None): "oho",
    (IrregularVerb.Irreg_Ho, Person.First, Number.Plural, Inclusivity.Inclusive): "jaha",
    (IrregularVerb.Irreg_Ho, Person.First, Number.Plural, Inclusivity.Exclusive): "roho",
    (IrregularVerb.Irreg_Ho, Person.Second, Number.Plural, None): "peho",

    (IrregularVerb.Irreg_E, Person.First, Number.Singular, None): "ha'e",
    (IrregularVerb.Irreg_E, Person.Second, Number.Singular, None): "ere",
    (IrregularVerb.Irreg_E, Person.Third, Number.Singular, None): "he'i",
    (IrregularVerb.Irreg_E, Person.Third, Number.Plural, None): "he'i",
    (IrregularVerb.Irreg_E, Person.First, Number.Plural, Inclusivity.Inclusive): "ja'e",
    (IrregularVerb.Irreg_E, Person.First, Number.Plural, Inclusivity.Exclusive): "ro'e",
    (IrregularVerb.Irreg_E, Person.Second, Number.Plural, None): "peje",
}

# Third person doesn't distinguish number on the irregular verbs
# themselves (oho/ou/he'i each serve both 3sg and 3pl; plurality is marked
# separately via hikuái), so a surface can map to more than one paradigm
# cell and every reading must be kept, not just the last one inserted.
IRREG_FORM_INDEX: dict[str, list[tuple]] = {}
for _key, _surface in IRREG_PARADIGM.items():
    IRREG_FORM_INDEX.setdefault(_surface, []).append(_key)
for _key, _surface in IRREG_PARADIGM.items():
    _dg = deglottalize(_surface)
    if _dg != _surface:
        bucket = IRREG_FORM_INDEX.setdefault(_dg, [])
        if _key not in bucket:
            bucket.append(_key)


@dataclass
class Verb:
    v_class: VerbClass
    v_orality: Orality
    v_root: str
    v_transitivity: Transitivity
    v_root_class: VerbRootClass = VerbRootClass.VRoot_Plain
    v_chendal_3sg: Chendal3sgForm = Chendal3sgForm.C3sg_I

    def to_coq(self) -> str:
        return (
            f"(mkVerb {self.v_class.to_coq()} {self.v_orality.to_coq()} "
            f'"{self.v_root}" {self.v_transitivity.to_coq()} '
            f"{self.v_root_class.to_coq()} {self.v_chendal_3sg.to_coq()})"
        )


class VerbForm:
    def to_coq(self) -> str:
        raise NotImplementedError


@dataclass
class VF_Regular(VerbForm):
    verb: Verb

    def to_coq(self) -> str:
        return f"(VF_Regular {self.verb.to_coq()})"


@dataclass
class VF_Irregular(VerbForm):
    irreg: IrregularVerb

    def to_coq(self) -> str:
        return f"(VF_Irregular {self.irreg.to_coq()})"


@dataclass
class ConjugatedVerb:
    verb_form: VerbForm
    person: Person
    number: Number
    incl: Optional[Inclusivity] = None
    mood: Mood = Mood.Indicative
    polarity: Polarity = Polarity.Positive
    voice: Voice = Voice.Active
    suffixes: list[VerbalSuffix] = field(default_factory=list)
    evidential: Optional[Evidential] = None

    @property
    def orality(self) -> Orality:
        if isinstance(self.verb_form, VF_Regular):
            return self.verb_form.verb.v_orality
        return Orality.Oral

    def to_coq(self) -> str:
        incl_coq = f"(Some {self.incl.to_coq()})" if self.incl else "None"
        suffixes_coq = (
            "[" + "; ".join(s.to_coq() for s in self.suffixes) + "]"
            if self.suffixes else "nil"
        )
        evidential_coq = f"(Some {self.evidential.to_coq()})" if self.evidential else "None"
        return (
            f"(mkConjVerb {self.verb_form.to_coq()} "
            f"{self.person.to_coq()} {self.number.to_coq()} "
            f"{incl_coq} {self.mood.to_coq()} {self.polarity.to_coq()} "
            f"{self.voice.to_coq()} {suffixes_coq} {evidential_coq})"
        )


# ========================= Noun Phrases =========================

# §3.1.1/§3.2.1.1/§3.2.2/§3.2.3/§3.4.3/§3.7: suffixes attaching to any
# noun-headed guarani_np (NP_Suf single, NP_Suf2 ordered pair).
class NominalSuffix(Enum):
    NS_Plural = "NS_Plural"
    NS_Multitude = "NS_Multitude"
    NS_Collective = "NS_Collective"
    NS_PastKue = "NS_PastKue"
    NS_FutureRa = "NS_FutureRa"
    NS_ComparVe = "NS_ComparVe"
    NS_Super = "NS_Super"
    NS_Privative = "NS_Privative"
    NS_Diminutive = "NS_Diminutive"
    NS_Attenuative = "NS_Attenuative"
    NS_NomHA = "NS_NomHA"
    NS_NomVA = "NS_NomVA"
    NS_NomPY = "NS_NomPY"
    NS_NomKue = "NS_NomKue"
    NS_OrdinalHA = "NS_OrdinalHA"

    def to_coq(self) -> str:
        return self.value


_NOM_SUFFIX_SURFACES: dict[NominalSuffix, "str | dict[Orality, str]"] = {
    NominalSuffix.NS_Plural: {Orality.Oral: "kuéra", Orality.Nasal: "nguéra"},
    NominalSuffix.NS_Multitude: "eta",
    NominalSuffix.NS_Collective: {Orality.Oral: "ty", Orality.Nasal: "ndy"},
    NominalSuffix.NS_PastKue: {Orality.Oral: "kue", Orality.Nasal: "ngue"},
    NominalSuffix.NS_FutureRa: "rã",
    NominalSuffix.NS_ComparVe: "ve",
    NominalSuffix.NS_Super: {Orality.Oral: "ite", Orality.Nasal: "ete"},
    NominalSuffix.NS_Privative: "'ỹ",
    NominalSuffix.NS_Diminutive: "'i",
    NominalSuffix.NS_Attenuative: {Orality.Oral: "vy", Orality.Nasal: "ngy"},
    NominalSuffix.NS_NomHA: "ha",
    NominalSuffix.NS_NomVA: "va",
    NominalSuffix.NS_NomPY: {Orality.Oral: "py", Orality.Nasal: "mby"},
    NominalSuffix.NS_NomKue: {Orality.Oral: "kue", Orality.Nasal: "ngue"},
    NominalSuffix.NS_OrdinalHA: "ha",
}

# §3.7: which (s1, s2) pairs suffix_pair_ok accepts for NP_Suf2 inner s1 s2
# (s1 attaches first/closest to the noun, s2 is outermost/final).
NOM_SUFFIX_PAIR_OK: set[tuple[NominalSuffix, NominalSuffix]] = {
    (NominalSuffix.NS_FutureRa, NominalSuffix.NS_PastKue),
    (NominalSuffix.NS_NomPY, NominalSuffix.NS_FutureRa),
    (NominalSuffix.NS_NomPY, NominalSuffix.NS_PastKue),
    (NominalSuffix.NS_NomHA, NominalSuffix.NS_PastKue),
    (NominalSuffix.NS_NomHA, NominalSuffix.NS_FutureRa),
}

_NOM_SUFFIX_STRIP_PAIRS: set[tuple[str, NominalSuffix]] = set()
for _nsuf, _nsurf in _NOM_SUFFIX_SURFACES.items():
    for _nform in ([_nsurf] if isinstance(_nsurf, str) else list(_nsurf.values())):
        _NOM_SUFFIX_STRIP_PAIRS.add((_nform, _nsuf))
        _NOM_SUFFIX_STRIP_PAIRS.add((deglottalize(_nform), _nsuf))

NOM_SUFFIX_STRIP_INDEX = sorted(_NOM_SUFFIX_STRIP_PAIRS, key=lambda t: -len(t[0]))


# §3.5.3: indefinite pronouns (standalone NP_PronIndef, distinct from the
# demonstrative-adjective "ko + noun" pattern and from NP_PronNeg).
class IndefPron(Enum):
    Indef_Maymava = "Indef_Maymava"
    Indef_Opava = "Indef_Opava"
    Indef_Avave = "Indef_Avave"
    Indef_Mbaeve = "Indef_Mbaeve"
    Indef_Oimeraeva = "Indef_Oimeraeva"
    Indef_Mokoive = "Indef_Mokoive"
    Indef_Ambueva = "Indef_Ambueva"
    Indef_PeteiMbae = "Indef_PeteiMbae"

    def to_coq(self) -> str:
        return self.value


INDEF_PRON_SURFACE = {
    IndefPron.Indef_Maymava: "maymáva",
    IndefPron.Indef_Opava: "opáva",
    IndefPron.Indef_Avave: "avave",
    IndefPron.Indef_Mbaeve: "mba'eve",
    IndefPron.Indef_Oimeraeva: "oimeraẽva",
    IndefPron.Indef_Mokoive: "mokõive",
    IndefPron.Indef_Ambueva: "ambuéva",
    IndefPron.Indef_PeteiMbae: "peteĩ mba'e",
}

# number_of_indef: Avave/Mbaeve/PeteiMbae are Singular, everything else Plural.
_INDEF_PRON_SINGULAR = {IndefPron.Indef_Avave, IndefPron.Indef_Mbaeve, IndefPron.Indef_PeteiMbae}

# np_is_human's NP_PronIndef case.
INDEF_PRON_HUMAN = {IndefPron.Indef_Avave, IndefPron.Indef_Maymava, IndefPron.Indef_Opava}


def indef_pron_number(i: IndefPron) -> Number:
    return Number.Singular if i in _INDEF_PRON_SINGULAR else Number.Plural


# Avave/Mbaeve are already reachable (with identical surface and semantics —
# is_negative_np covers both NP_PronNeg and NP_PronIndef paths) via the
# existing NegPron/NEG_PRON_FORM_INDEX route in analyzer.py, so they're
# excluded here to avoid generating redundant duplicate candidates for the
# exact same surface form.
INDEF_PRON_FORM_INDEX: dict[str, IndefPron] = {}
for _ip, _surf in INDEF_PRON_SURFACE.items():
    if _ip in (IndefPron.Indef_Avave, IndefPron.Indef_Mbaeve):
        continue
    INDEF_PRON_FORM_INDEX[_surf] = _ip
    _dg = deglottalize(_surf)
    if _dg != _surf:
        INDEF_PRON_FORM_INDEX.setdefault(_dg, _ip)


# §3.5.2: interrogative pronouns (standalone NP_PronInterrog).
class InterrogPron(Enum):
    Interrog_Mbae = "Interrog_Mbae"
    Interrog_Mava = "Interrog_Mava"
    Interrog_Mbaeicha = "Interrog_Mbaeicha"
    Interrog_Mamo = "Interrog_Mamo"
    Interrog_Arakae = "Interrog_Arakae"
    Interrog_Mbaera = "Interrog_Mbaera"
    Interrog_Mbaere = "Interrog_Mbaere"
    Interrog_Mbaegui = "Interrog_Mbaegui"
    Interrog_Mbovy = "Interrog_Mbovy"
    Interrog_Avambae = "Interrog_Avambae"

    def to_coq(self) -> str:
        return self.value


INTERROG_PRON_SURFACE = {
    InterrogPron.Interrog_Mbae: "mba'e",
    InterrogPron.Interrog_Mava: "máva",
    InterrogPron.Interrog_Mbaeicha: "mba'éicha",
    InterrogPron.Interrog_Mamo: "moõ",
    InterrogPron.Interrog_Arakae: "araka'e",
    InterrogPron.Interrog_Mbaera: "mba'erã",
    InterrogPron.Interrog_Mbaere: "mba'ére",
    InterrogPron.Interrog_Mbaegui: "mba'égui",
    InterrogPron.Interrog_Mbovy: "mbovy",
    InterrogPron.Interrog_Avambae: "avamba'e",
}

# np_is_human's NP_PronInterrog case.
INTERROG_PRON_HUMAN = {InterrogPron.Interrog_Mava, InterrogPron.Interrog_Avambae}

INTERROG_PRON_FORM_INDEX: dict[str, InterrogPron] = {}
for _itp, _surf in INTERROG_PRON_SURFACE.items():
    INTERROG_PRON_FORM_INDEX[_surf] = _itp
    _dg = deglottalize(_surf)
    if _dg != _surf:
        INTERROG_PRON_FORM_INDEX.setdefault(_dg, _itp)


@dataclass
class NP:
    surface: str
    person: Person = Person.Third
    number: Number = Number.Singular
    human: bool = False

    pronoun: Optional[SubjPronoun] = None
    noun: Optional[Noun] = None
    possessor: Optional[PossMarker] = None
    demonstrative: Optional[DemProximity] = None
    adjective: Optional[Adjective] = None
    numeral_coq: Optional[str] = None
    neg_pron: Optional[NegPron] = None
    suffixes: list[NominalSuffix] = field(default_factory=list)
    dem_pronoun: Optional[DemProximity] = None
    indef_pron: Optional[IndefPron] = None
    interrog_pron: Optional[InterrogPron] = None
    gen_possessor: Optional["NP"] = None

    coq_term: Optional[str] = None

    def to_coq(self) -> str:
        if self.coq_term:
            return self.coq_term
        if self.neg_pron is not None:
            base = f"(NP_PronNeg {self.neg_pron.to_coq()})"
        elif self.pronoun is not None:
            base = f"(NP_PronSubj {self.pronoun.to_coq()})"
        elif self.dem_pronoun is not None:
            base = f"(NP_PronDem {self.dem_pronoun.to_coq()} {self.number.to_coq()})"
        elif self.indef_pron is not None:
            base = f"(NP_PronIndef {self.indef_pron.to_coq()})"
        elif self.interrog_pron is not None:
            base = f"(NP_PronInterrog {self.interrog_pron.to_coq()})"
        elif self.noun is not None:
            if self.gen_possessor is not None:
                base = f"(NP_Gen {self.gen_possessor.to_coq()} {self.noun.to_coq()})"
            elif self.possessor is not None:
                base = f"(NP_Poss {self.possessor.to_coq()} {self.noun.to_coq()})"
            elif self.demonstrative is not None:
                base = (
                    f"(NP_Dem {self.demonstrative.to_coq()} "
                    f"{self.number.to_coq()} {self.noun.to_coq()})"
                )
            elif self.adjective is not None:
                base = f"(NP_Adj {self.noun.to_coq()} {self.adjective.to_coq()})"
            elif self.numeral_coq is not None:
                base = f"(NP_Num {self.numeral_coq} {self.noun.to_coq()})"
            else:
                base = f"(NP_Bare {self.noun.to_coq()})"
        else:
            raise ValueError(f"NP for '{self.surface}' has no valid Coq representation yet")

        if len(self.suffixes) == 1:
            return f"(NP_Suf {base} {self.suffixes[0].to_coq()})"
        if len(self.suffixes) == 2:
            return f"(NP_Suf2 {base} {self.suffixes[0].to_coq()} {self.suffixes[1].to_coq()})"
        return base


# ========================= Sentences =========================

class WordOrder(Enum):
    WO_SVO = "WO_SVO"
    WO_SOV = "WO_SOV"
    WO_VSO = "WO_VSO"
    WO_VOS = "WO_VOS"
    WO_OVS = "WO_OVS"
    WO_OSV = "WO_OSV"

    def to_coq(self) -> str:
        return self.value


class DemProximity(Enum):
    DemProxSpeaker = "DemProxSpeaker"
    DemProxHearer = "DemProxHearer"
    DemDistal = "DemDistal"
    DemSharedPerson = "DemSharedPerson"
    DemSharedEvent = "DemSharedEvent"
    DemHearsay = "DemHearsay"

    def to_coq(self) -> str:
        return self.value


DEM_ADJ_SURFACE = {
    (DemProximity.DemProxSpeaker, Number.Singular): "ko",
    (DemProximity.DemProxSpeaker, Number.Plural): "ko'ã",
    (DemProximity.DemProxHearer, Number.Singular): "pe",
    (DemProximity.DemProxHearer, Number.Plural): "umi",
    (DemProximity.DemDistal, Number.Singular): "amo",
    (DemProximity.DemDistal, Number.Plural): "umi",
    (DemProximity.DemSharedPerson, Number.Singular): "ku",
    (DemProximity.DemSharedPerson, Number.Plural): "umi",
    (DemProximity.DemSharedEvent, Number.Singular): "ako",
    (DemProximity.DemSharedEvent, Number.Plural): "umi",
    (DemProximity.DemHearsay, Number.Singular): "aipo",
    (DemProximity.DemHearsay, Number.Plural): "umi",
}

DEM_ADJ_FORM_INDEX = {}
for (dp, n), surf in DEM_ADJ_SURFACE.items():
    DEM_ADJ_FORM_INDEX.setdefault(surf, []).append((dp, n))
for _surf in list(DEM_ADJ_FORM_INDEX):
    _plain = deglottalize(_surf)
    if _plain != _surf and _plain not in DEM_ADJ_FORM_INDEX:
        DEM_ADJ_FORM_INDEX[_plain] = DEM_ADJ_FORM_INDEX[_surf]


# §3.5.4/§3.2.1.1.3: dem_pron_form — the "-va"-nominalized standalone
# demonstrative PRONOUN (NP_PronDem), distinct from DEM_ADJ_SURFACE's
# adjectival "ko + noun" pattern above. Several cells collapse to the same
# surface (all plurals but DemProxSpeaker's render "umíva"; DemSharedPerson/
# DemSharedEvent singular don't nominalize at all and coincide with their
# own DEM_ADJ_SURFACE forms "ku"/"ako") — harmless, since np_meta_of for
# NP_PronDem only depends on number, not proximity, so which candidate wins
# never affects well-formedness or agreement.
DEM_PRON_SURFACE = {
    (DemProximity.DemProxSpeaker, Number.Singular): "kóva",
    (DemProximity.DemProxSpeaker, Number.Plural): "ko'ãva",
    (DemProximity.DemProxHearer, Number.Singular): "péva",
    (DemProximity.DemProxHearer, Number.Plural): "umíva",
    (DemProximity.DemDistal, Number.Singular): "amóva",
    (DemProximity.DemDistal, Number.Plural): "umíva",
    (DemProximity.DemSharedPerson, Number.Singular): "ku",
    (DemProximity.DemSharedPerson, Number.Plural): "umíva",
    (DemProximity.DemSharedEvent, Number.Singular): "ako",
    (DemProximity.DemSharedEvent, Number.Plural): "umíva",
    (DemProximity.DemHearsay, Number.Singular): "aipóva",
    (DemProximity.DemHearsay, Number.Plural): "umíva",
}

DEM_PRON_FORM_INDEX = {}
for (dp, n), surf in DEM_PRON_SURFACE.items():
    DEM_PRON_FORM_INDEX.setdefault(surf, []).append((dp, n))
for _surf in list(DEM_PRON_FORM_INDEX):
    _plain = deglottalize(_surf)
    if _plain != _surf and _plain not in DEM_PRON_FORM_INDEX:
        DEM_PRON_FORM_INDEX[_plain] = DEM_PRON_FORM_INDEX[_surf]


class Postposition(Enum):
    Post_Pe = "Post_Pe"
    Post_Gui = "Post_Gui"
    Post_Gua = "Post_Gua"
    Post_Rehe = "Post_Rehe"
    Post_Ndive = "Post_Ndive"
    Post_Guive = "Post_Guive"
    Post_Peve = "Post_Peve"
    Post_Rupi = "Post_Rupi"
    Post_Ari = "Post_Ari"
    Post_Guy = "Post_Guy"
    Post_Guara = "Post_Guara"
    Post_Hagua = "Post_Hagua"
    Post_Kue = "Post_Kue"

    def to_coq(self) -> str:
        return self.value


POSTPOSITION_SURFACE = {
    (Postposition.Post_Pe, Orality.Oral): "pe",
    (Postposition.Post_Pe, Orality.Nasal): "me",
    (Postposition.Post_Gui, Orality.Oral): "gui",
    (Postposition.Post_Gui, Orality.Nasal): "gui",
    (Postposition.Post_Gua, Orality.Oral): "gua",
    (Postposition.Post_Gua, Orality.Nasal): "gua",
    (Postposition.Post_Rehe, Orality.Oral): "rehe",
    (Postposition.Post_Rehe, Orality.Nasal): "rehe",
    (Postposition.Post_Ndive, Orality.Oral): "ndive",
    (Postposition.Post_Ndive, Orality.Nasal): "ndie",
    (Postposition.Post_Guive, Orality.Oral): "guive",
    (Postposition.Post_Guive, Orality.Nasal): "guive",
    (Postposition.Post_Peve, Orality.Oral): "peve",
    (Postposition.Post_Peve, Orality.Nasal): "peve",
    (Postposition.Post_Rupi, Orality.Oral): "rupi",
    (Postposition.Post_Rupi, Orality.Nasal): "rupi",
    (Postposition.Post_Ari, Orality.Oral): "'ári",
    (Postposition.Post_Ari, Orality.Nasal): "'ári",
    (Postposition.Post_Guy, Orality.Oral): "guy",
    (Postposition.Post_Guy, Orality.Nasal): "guy",
    (Postposition.Post_Guara, Orality.Oral): "guarã",
    (Postposition.Post_Guara, Orality.Nasal): "guarã",
    (Postposition.Post_Hagua, Orality.Oral): "haguã",
    (Postposition.Post_Hagua, Orality.Nasal): "haguã",
    (Postposition.Post_Kue, Orality.Oral): "kue",
    (Postposition.Post_Kue, Orality.Nasal): "ngue",
}

POSTPOSITION_STRIP_INDEX = sorted(
    {(surf, pp, o) for (pp, o), surf in POSTPOSITION_SURFACE.items()}
    | {(deglottalize(surf), pp, o) for (pp, o), surf in POSTPOSITION_SURFACE.items()},
    key=lambda t: -len(t[0])
)

# Standalone postposition tokens (e.g. "ka'aguy pe") → possible postpositions
POSTPOSITION_FORM_INDEX: dict[str, list[Postposition]] = {}
for (_pp, _o), _surf in POSTPOSITION_SURFACE.items():
    for _form in (_surf, deglottalize(_surf)):
        _lst = POSTPOSITION_FORM_INDEX.setdefault(_form, [])
        if _pp not in _lst:
            _lst.append(_pp)


class SentenceType(Enum):
    ST_Declarative = "ST_Declarative"
    ST_Interrog_YN = "ST_Interrog_YN"
    ST_Interrog_Content = "ST_Interrog_Content"
    ST_Imperative = "ST_Imperative"
    ST_Prohibitive = "ST_Prohibitive"

    def to_coq(self) -> str:
        return self.value


class InterrogParticle(Enum):
    IntP_Pa = "IntP_Pa"
    IntP_Piko = "IntP_Piko"

    def to_coq(self) -> str:
        return self.value


@dataclass
class Sentence:
    verb: ConjugatedVerb
    subject: Optional[NP] = None
    direct_obj: Optional[NP] = None
    indirect_obj: Optional[NP] = None
    postp_comp: Optional[tuple[NP, "Postposition"]] = None
    word_order: WordOrder = WordOrder.WO_SVO
    sent_type: SentenceType = SentenceType.ST_Declarative
    interrog: Optional[InterrogParticle] = None
    hikuai: bool = False

    def _opt_np(self, np: Optional[NP]) -> str:
        return f"(Some {np.to_coq()})" if np else "None"

    def _opt_postp(self, postp: Optional[tuple[NP, "Postposition"]]) -> str:
        if postp is None:
            return "None"
        np, pp = postp
        return f"(Some ({np.to_coq()}, {pp.to_coq()}))"

    def _opt_interrog(self, ip: Optional[InterrogParticle]) -> str:
        return f"(Some {ip.to_coq()})" if ip else "None"

    def to_coq(self) -> str:
        return (
            f"(mkSentence\n"
            f"  {self._opt_np(self.subject)}\n"
            f"  {self.verb.to_coq()}\n"
            f"  {self._opt_np(self.direct_obj)}\n"
            f"  {self._opt_np(self.indirect_obj)}\n"
            f"  {self._opt_postp(self.postp_comp)}\n"
            f"  {self.word_order.to_coq()}\n"
            f"  {self.sent_type.to_coq()}\n"
            f"  {self._opt_interrog(self.interrog)}\n"
            f"  {'true' if self.hikuai else 'false'})"
        )

    def to_coq_compute(self) -> str:
        return f"Compute wf_sentence {self.to_coq()}."


# ===================== Complex / adverbial sentences (§12) =====================
# Mirrors sentence.v's adv_clause_type / adv_morpheme_ok / adv_clause / CS_Adverbial.

class AdvClauseType(Enum):
    AC_Purposive = "AC_Purposive"                # haguã
    AC_PurpNeg = "AC_PurpNeg"                     # ani haguã
    AC_PurpSimult = "AC_PurpSimult"               # -vo
    AC_Concessive = "AC_Concessive"               # ramo jepe
    AC_ConcessPotential = "AC_ConcessPotential"   # jepe (+ optative)
    AC_Causal_Gui = "AC_Causal_Gui"               # =gui
    AC_Causal_Rehe = "AC_Causal_Rehe"             # =rehe / =re
    AC_Causal_Rupi = "AC_Causal_Rupi"             # =rupi
    AC_Causal_Porque = "AC_Causal_Porque"         # porque
    AC_Cond_Hyp = "AC_Cond_Hyp"                   # =rõ / =ramo
    AC_Cond_Counter = "AC_Cond_Counter"           # =rire (on subord)
    AC_Manner = "AC_Manner"                       # -ha-icha / -hague-icha
    AC_Temp_Simult = "AC_Temp_Simult"             # =ramo/=rõ/-vo/aja/jave
    AC_Temp_Ant = "AC_Temp_Ant"                   # mboyve
    AC_Temp_Post = "AC_Temp_Post"                 # rire / vove
    AC_Locative = "AC_Locative"                   # -ha + postposition

    def to_coq(self) -> str:
        return self.value


# Mirrors adv_morpheme_ok exactly. AC_Locative is a "starts with ha" structural
# rule in Coq, not a fixed surface set, so it has no entry here.
ADV_MORPHEME_TABLE: dict[AdvClauseType, tuple[str, ...]] = {
    AdvClauseType.AC_Purposive: ("haguã",),
    AdvClauseType.AC_PurpNeg: ("ani haguã",),
    AdvClauseType.AC_PurpSimult: ("vo",),
    AdvClauseType.AC_Concessive: ("ramo jepe",),
    AdvClauseType.AC_ConcessPotential: ("jepe",),
    AdvClauseType.AC_Causal_Gui: ("gui",),
    AdvClauseType.AC_Causal_Rehe: ("rehe", "re"),
    AdvClauseType.AC_Causal_Rupi: ("rupi",),
    AdvClauseType.AC_Causal_Porque: ("porque",),
    AdvClauseType.AC_Cond_Hyp: ("rõ", "ramo"),
    AdvClauseType.AC_Cond_Counter: ("rire",),
    AdvClauseType.AC_Manner: ("ha-icha", "hague-icha"),
    AdvClauseType.AC_Temp_Simult: ("ramo", "rõ", "vo", "aja", "jave"),
    AdvClauseType.AC_Temp_Ant: ("mboyve",),
    AdvClauseType.AC_Temp_Post: ("rire", "vove"),
}

# Every subordinator morpheme in ADV_MORPHEME_TABLE is registered as BOTH a
# free-standing token (ADV_SUBORDINATOR_FORM_INDEX) and a fusable suffix
# (ADV_ENCLITIC_STRIP_INDEX). Originally only "haguã, ani haguã, ramo jepe,
# jepe, porque, mboyve, aja, jave" were treated as free tokens on the theory
# that the rest (=gui, =rehe, =rupi, =rõ, =ramo, =rire, vove, -vo) only ever
# fuse onto the verb per the "=" notation in the §-comments above each
# constructor. Real test sentences disproved that split both ways: "oguata
# oky ramo" and "oñe'ẽ oho rire" write ramo/rire as separate tokens, while
# "aha rejúrõ" (reju + rõ) fuses rõ onto the verb in the same breath — so
# modern orthography clearly allows either for the same morpheme, and only
# AC_Locative/AC_Manner are excluded (see below), not by attachment style.
#
# Whole-token lookup on a short, common string carries some inherent
# collision risk (the same failure mode fixed for avave in analyze()), but
# it's bounded here the same way postposition stripping already is
# elsewhere: a coincidental match only produces a candidate if the adjacent
# span independently reparses as a real, dictionary-verified clause.
#
# Two entries are excluded outright, not just unimplemented:
#   - AC_Locative: adv_morpheme_ok accepts ANY string starting with "ha", not
#     a fixed morpheme. Indexing that would misfire on huge numbers of
#     ordinary words and manufacture false well-formed readings — the avave
#     failure mode, but systematic instead of a one-off.
#   - AC_Manner (ha-icha / hague-icha): the Coq strings contain literal
#     hyphens, which don't occur inside fused Guaraní words in normal prose.
#     Without a confirmed real orthographic form for this suffix, encoding a
#     guessed spelling risks either matching nothing or matching the wrong
#     thing — skipped rather than guessed.
_EXCLUDED_ADV_TYPES = {AdvClauseType.AC_Locative}
_EXCLUDED_ADV_MORPHEMES = {"ha-icha", "hague-icha"}

_ADV_INDEXABLE = [
    (_m, _ac_type)
    for _ac_type, _morphemes in ADV_MORPHEME_TABLE.items()
    if _ac_type not in _EXCLUDED_ADV_TYPES
    for _m in _morphemes
    if _m not in _EXCLUDED_ADV_MORPHEMES
]

ADV_SUBORDINATOR_FORM_INDEX: dict[str, list[AdvClauseType]] = {}
for _m, _ac_type in _ADV_INDEXABLE:
    ADV_SUBORDINATOR_FORM_INDEX.setdefault(_m, []).append(_ac_type)

ADV_ENCLITIC_STRIP_INDEX: list[tuple[str, AdvClauseType]] = sorted(
    set(_ADV_INDEXABLE), key=lambda t: -len(t[0])
)


@dataclass
class AdvClause:
    ac_type: AdvClauseType
    ac_subord: str

    def to_coq(self) -> str:
        return f'(mkAdvClause {self.ac_type.to_coq()} "{self.ac_subord}")'


@dataclass
class AdverbialSentence:
    """Python mirror of `CS_Adverbial main ac subord`."""
    main: Sentence
    ac: AdvClause
    subord: Sentence

    def to_coq_compute(self) -> str:
        return (
            f"Compute wf_complex (CS_Adverbial\n"
            f"  {self.main.to_coq()}\n"
            f"  {self.ac.to_coq()}\n"
            f"  {self.subord.to_coq()}).\n"
        )


@dataclass
class CoordinatedSentence:
    """Python mirror of `CS_Coordinated s1 s2` — two full clauses joined by
    a free-standing "ha" ("and"), e.g. "ajogua ha aheja" = "I buy and sell"
    (scope.md test #50). wf_complex just requires both clauses wf_sentence;
    there's no separate conjunction-well-formedness check the way
    wf_adv_clause has for CS_Adverbial."""
    s1: Sentence
    s2: Sentence

    def to_coq_compute(self) -> str:
        return (
            f"Compute wf_complex (CS_Coordinated\n"
            f"  {self.s1.to_coq()}\n"
            f"  {self.s2.to_coq()}).\n"
        )


@dataclass
class NonverbalSentence:
    """Python mirror of `nonverbal_sentence` (NVS_Equative/NVS_Predicative/
    NVS_Existential/NVS_Possessive) — Guaraní has zero copula, so these are
    plain NP (or NP + NP) utterances with no verb pivot at all: "Ha'e Maria"
    ("She is Maria", equative), "ka'aguy" standing alone ("[there's a]
    forest", existential). All four constructors share the exact same
    wf_nonverbal shape (wf_np on each argument, nothing else — no cross-
    constructor agreement or morpheme check the way ss_type_ok or
    wf_adv_clause have), so `coq_term` just carries whichever NVS_* term the
    builder already assembled rather than this class owning separate
    fields per constructor."""
    coq_term: str

    def to_coq_compute(self) -> str:
        return f"Compute wf_nonverbal {self.coq_term}.\n"