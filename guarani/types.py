"""
types.py

Python mirror of the Coq types in Primitives.v and Verb.v.
Every class has a to_coq() method that produces the exact Coq constructor
string used in `Compute wf_sentence (mkSentence ...)` calls.

Naming convention: Python class names match Coq inductive/record names.
Enum member names match Coq constructor names exactly.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================
#  Primitives (mirror Primitives.v)
# ============================================================

class Orality(Enum):
    Oral  = "Oral"
    Nasal = "Nasal"

    def to_coq(self) -> str:
        return self.value


class Person(Enum):
    First  = "First"
    Second = "Second"
    Third  = "Third"

    def to_coq(self) -> str:
        return self.value


class WordEnding(Enum):
    EndAEO = "EndAEO"
    EndIUY = "EndIUY"

    def to_coq(self) -> str:
        return self.value

class RootClass(Enum):
    Uniform    = "Uniform"
    Triform    = "Triform"
    TriformNoT = "TriformNoT"
    Biform     = "Biform"
    Quadriform = "Quadriform"

    def to_coq(self) -> str:
        return self.value


def word_ending_of(root: str) -> WordEnding:
    if not root:
        return WordEnding.EndAEO
    return WordEnding.EndIUY if root[-1] in "iuyĩũỹ" else WordEnding.EndAEO


@dataclass
class Noun:
    n_root:       str
    n_orality:    Orality
    n_ending:     WordEnding
    n_root_class: RootClass = RootClass.Uniform
    n_human:      bool      = False

    def to_coq(self) -> str:
        return (
            f"(mkNoun \"{self.n_root}\" {self.n_orality.to_coq()} "
            f"{self.n_ending.to_coq()} {self.n_root_class.to_coq()} "
            f"{'true' if self.n_human else 'false'})"
        )


class Number(Enum):
    Singular = "Singular"
    Plural   = "Plural"

    def to_coq(self) -> str:
        return self.value


class Inclusivity(Enum):
    Inclusive = "Inclusive"
    Exclusive = "Exclusive"

    def to_coq(self) -> str:
        return self.value
    
class PossMarker(Enum):
    Poss1     = "Poss1"
    Poss2     = "Poss2"
    Poss3     = "Poss3"
    Poss1Incl = "Poss1Incl"
    Poss1Excl = "Poss1Excl"
    Poss2Pl   = "Poss2Pl"
    Poss3Pl   = "Poss3Pl"

    def to_coq(self) -> str:
        return self.value


# Surface forms keyed by (PossMarker, Orality). Mirrors poss_marker_form in Syntax.v.
POSS_MARKER_SURFACE: dict[tuple[PossMarker, Orality], str] = {
    (PossMarker.Poss1,     Orality.Oral):  "che",
    (PossMarker.Poss1,     Orality.Nasal): "che",
    (PossMarker.Poss2,     Orality.Oral):  "nde",
    (PossMarker.Poss2,     Orality.Nasal): "ne",
    (PossMarker.Poss3,     Orality.Oral):  "i",
    (PossMarker.Poss3,     Orality.Nasal): "iñ",
    (PossMarker.Poss1Incl, Orality.Oral):  "ñánde",
    (PossMarker.Poss1Incl, Orality.Nasal): "ñáne",
    (PossMarker.Poss1Excl, Orality.Oral):  "ore",
    (PossMarker.Poss1Excl, Orality.Nasal): "ore",
    (PossMarker.Poss2Pl,   Orality.Oral):  "pénde",
    (PossMarker.Poss2Pl,   Orality.Nasal): "péne",
    (PossMarker.Poss3Pl,   Orality.Oral):  "i",
    (PossMarker.Poss3Pl,   Orality.Nasal): "iñ",
}

# Reverse index: surface → list of (PossMarker, Orality) candidates
POSS_MARKER_FORM_INDEX: dict[str, list[tuple[PossMarker, Orality]]] = {}
for (pm, o), surf in POSS_MARKER_SURFACE.items():
    POSS_MARKER_FORM_INDEX.setdefault(surf, []).append((pm, o))


_POSS_MARKER_PERSON: dict[PossMarker, Person] = {
    PossMarker.Poss1: Person.First,  PossMarker.Poss1Incl: Person.First,
    PossMarker.Poss1Excl: Person.First,
    PossMarker.Poss2: Person.Second, PossMarker.Poss2Pl: Person.Second,
    PossMarker.Poss3: Person.Third,  PossMarker.Poss3Pl: Person.Third,
}

_POSS_MARKER_NUMBER: dict[PossMarker, Number] = {
    PossMarker.Poss1: Number.Singular, PossMarker.Poss2: Number.Singular,
    PossMarker.Poss3: Number.Singular,
    PossMarker.Poss1Incl: Number.Plural, PossMarker.Poss1Excl: Number.Plural,
    PossMarker.Poss2Pl: Number.Plural, PossMarker.Poss3Pl: Number.Plural,
}

_POSS_MARKER_INCLUSIVITY: dict[PossMarker, Optional[Inclusivity]] = {
    PossMarker.Poss1Incl: Inclusivity.Inclusive,
    PossMarker.Poss1Excl: Inclusivity.Exclusive,
    PossMarker.Poss1: None, PossMarker.Poss2: None, PossMarker.Poss3: None,
    PossMarker.Poss2Pl: None, PossMarker.Poss3Pl: None,
}
class SubjPronoun(Enum):
    Subj1SG      = "Subj1SG"
    Subj2SG      = "Subj2SG"
    Subj3SG      = "Subj3SG"
    Subj1PL_INCL = "Subj1PL_INCL"
    Subj1PL_EXCL = "Subj1PL_EXCL"
    Subj2PL      = "Subj2PL"
    Subj3PL      = "Subj3PL"

    def to_coq(self) -> str:
        return self.value


_SUBJ_PRONOUN_SURFACE: dict[SubjPronoun, str] = {
    SubjPronoun.Subj1SG:      "che",
    SubjPronoun.Subj2SG:      "nde",
    SubjPronoun.Subj3SG:      "ha'e",
    SubjPronoun.Subj1PL_INCL: "ñande",
    SubjPronoun.Subj1PL_EXCL: "ore",
    SubjPronoun.Subj2PL:      "peẽ",
    SubjPronoun.Subj3PL:      "ha'ekuéra",
}

_SUBJ_PRONOUN_PERSON: dict[SubjPronoun, Person] = {
    SubjPronoun.Subj1SG: Person.First,
    SubjPronoun.Subj1PL_INCL: Person.First,
    SubjPronoun.Subj1PL_EXCL: Person.First,
    SubjPronoun.Subj2SG: Person.Second,
    SubjPronoun.Subj2PL: Person.Second,
    SubjPronoun.Subj3SG: Person.Third,
    SubjPronoun.Subj3PL: Person.Third,
}

_SUBJ_PRONOUN_NUMBER: dict[SubjPronoun, Number] = {
    SubjPronoun.Subj1SG: Number.Singular,
    SubjPronoun.Subj2SG: Number.Singular,
    SubjPronoun.Subj3SG: Number.Singular,
    SubjPronoun.Subj1PL_INCL: Number.Plural,
    SubjPronoun.Subj1PL_EXCL: Number.Plural,
    SubjPronoun.Subj2PL: Number.Plural,
    SubjPronoun.Subj3PL: Number.Plural,
}

SUBJ_PRONOUN_FORM_INDEX: dict[str, SubjPronoun] = {
    surf: p for p, surf in _SUBJ_PRONOUN_SURFACE.items()
}

#  Adjective

@dataclass
class Adjective:
    a_form:       str
    a_orality:    Orality
    a_root_class: RootClass = RootClass.Uniform

    def to_coq(self) -> str:
        return (
            f"(mkAdj \"{self.a_form}\" {self.a_orality.to_coq()} "
            f"{self.a_root_class.to_coq()})"
        )
    
# ============================================================
#  Verb classification (§1 Verb.v)
# ============================================================

class VerbClass(Enum):
    Areal   = "Areal"
    Aireal  = "Aireal"
    Chendal = "Chendal"

    def to_coq(self) -> str:
        return self.value


# ============================================================
#  Transitivity (§2 Verb.v)
# ============================================================

class Transitivity(Enum):
    Intransitive      = "Intransitive"
    Transitive        = "Transitive"
    Ditransitive      = "Ditransitive"
    PostpComplement   = "PostpComplement"

    def to_coq(self) -> str:
        return self.value


# ============================================================
#  Root class (§3 Verb.v)
# ============================================================

class VerbRootClass(Enum):
    VRoot_Plain      = "VRoot_Plain"
    VRoot_Relational = "VRoot_Relational"

    def to_coq(self) -> str:
        return self.value


# ============================================================
#  Chendal 3sg allomorph (§4 Verb.v)
# ============================================================

class Chendal3sgForm(Enum):
    C3sg_I  = "C3sg_I"   # i-/iñ-
    C3sg_Hi = "C3sg_Hi"  # hi-/hiñ- (most common)
    C3sg_Ij = "C3sg_Ij"  # ij-/iñ- (before vowel-initial roots)

    def to_coq(self) -> str:
        return self.value


# ============================================================
#  Voice (§5 Verb.v)
# ============================================================

class Voice(Enum):
    Active     = "Active"
    Passive    = "Passive"
    Reciprocal = "Reciprocal"
    Coactive   = "Coactive"
    Objective  = "Objective"
    Obj_Guero  = "Obj_Guero"
    Subsuntive = "Subsuntive"

    def to_coq(self) -> str:
        return self.value


# ============================================================
#  Mood (§6 Verb.v)
# ============================================================

class Mood(Enum):
    Indicative  = "Indicative"
    Imperative  = "Imperative"
    Optative    = "Optative"
    Prohibitive = "Prohibitive"

    def to_coq(self) -> str:
        return self.value


# ============================================================
#  Polarity (§7 Verb.v)
# ============================================================

class Polarity(Enum):
    Positive = "Positive"
    Negative = "Negative"

    def to_coq(self) -> str:
        return self.value



# ============================================================
#  Evidential markers (§8 Verb.v)
# ============================================================

class NikoVariant(Enum):
    NK_Niko  = "NK_Niko"
    NK_Ko    = "NK_Ko"
    NK_Ngo   = "NK_Ngo"
    NK_Ningo = "NK_Ningo"

    def to_coq(self) -> str:
        return self.value


class EvidentialMarker(Enum):
    Ev_Voi     = "Ev_Voi"
    Ev_Niko    = "Ev_Niko"
    Ev_Ndaje   = "Ev_Ndaje"
    Ev_Jeko    = "Ev_Jeko"
    Ev_NandEko = "Ev_NandEko"
    Ev_Kuri    = "Ev_Kuri"
    Ev_Rae     = "Ev_Rae"
    Ev_Rakae   = "Ev_Rakae"
    Ev_MboRae  = "Ev_MboRae"
    Ev_Nipo    = "Ev_Nipo"
    Ev_Hina    = "Ev_Hina"

    def to_coq(self) -> str:
        return self.value


@dataclass
class Evidential:
    marker:     EvidentialMarker
    niko_v:     Optional[NikoVariant] = None   # only for Ev_Niko

    def to_coq(self) -> str:
        nv = f"(Some {self.niko_v.to_coq()})" if self.niko_v else "None"
        return f"(mkEvidential {self.marker.to_coq()} {nv})"


# ============================================================
#  Verbal suffixes (§9 Verb.v) — 31 constructors + 2 new
# ============================================================

class VerbalSuffix(Enum):
    VS_CausUka      = "VS_CausUka"
    VS_AbilKuaa     = "VS_AbilKuaa"
    VS_TotalPa      = "VS_TotalPa"
    VS_ImpForce     = "VS_ImpForce"
    VS_ImpRequest   = "VS_ImpRequest"
    VS_ImpPlead     = "VS_ImpPlead"
    VS_ImpUrge      = "VS_ImpUrge"
    VS_Volitive     = "VS_Volitive"
    VS_ComparVe     = "VS_ComparVe"
    VS_FutTa        = "VS_FutTa"
    VS_FutNe        = "VS_FutNe"
    VS_FutNegMoa    = "VS_FutNegMoa"
    VS_ImmFutPota   = "VS_ImmFutPota"
    VS_ObligVaera   = "VS_ObligVaera"
    VS_PastVaekue   = "VS_PastVaekue"
    VS_NegI         = "VS_NegI"
    VS_NegRi        = "VS_NegRi"
    VS_NegTei       = "VS_NegTei"
    VS_Privative    = "VS_Privative"
    VS_Intensifier  = "VS_Intensifier"
    VS_NomVa        = "VS_NomVa"
    VS_NomHa        = "VS_NomHa"
    VS_AspectMa     = "VS_AspectMa"
    VS_IterJevy     = "VS_IterJevy"
    VS_HabitMi      = "VS_HabitMi"
    VS_HabitVa      = "VS_HabitVa"
    VS_FrustrRei    = "VS_FrustrRei"
    VS_InterrogPa   = "VS_InterrogPa"
    VS_Desiderative = "VS_Desiderative"
    VS_Simultaneous = "VS_Simultaneous"   # -vo, slot 11
    VS_HearsayJe    = "VS_HearsayJe"      # -je, slot 13

    def to_coq(self) -> str:
        return self.value

    @property
    def slot(self) -> int:
        """Slot number per §10 Verb.v suffix_slot."""
        return _SUFFIX_SLOTS[self]

    @property
    def surface(self) -> dict:
        """Surface string(s) — keyed by Orality or single string if invariant."""
        return _SUFFIX_SURFACES[self]

    def render(self, orality: Orality) -> str:
        s = _SUFFIX_SURFACES[self]
        if isinstance(s, dict):
            return s[orality]
        return s


# Slot assignments (mirror suffix_slot in Verb.v §10)
_SUFFIX_SLOTS: dict[VerbalSuffix, int] = {
    VerbalSuffix.VS_CausUka:      1,
    VerbalSuffix.VS_AbilKuaa:     2,
    VerbalSuffix.VS_TotalPa:      3,
    VerbalSuffix.VS_ImpForce:     4,
    VerbalSuffix.VS_ImpRequest:   4,
    VerbalSuffix.VS_ImpPlead:     4,
    VerbalSuffix.VS_ImpUrge:      4,
    VerbalSuffix.VS_Volitive:     5,
    VerbalSuffix.VS_ComparVe:     6,
    VerbalSuffix.VS_FutTa:        7,
    VerbalSuffix.VS_FutNe:        7,
    VerbalSuffix.VS_FutNegMoa:    7,
    VerbalSuffix.VS_ImmFutPota:   7,
    VerbalSuffix.VS_ObligVaera:   7,
    VerbalSuffix.VS_PastVaekue:   7,
    VerbalSuffix.VS_NegI:         8,
    VerbalSuffix.VS_NegRi:        8,
    VerbalSuffix.VS_NegTei:       8,
    VerbalSuffix.VS_Privative:    8,
    VerbalSuffix.VS_Intensifier:  9,
    VerbalSuffix.VS_NomVa:        10,
    VerbalSuffix.VS_NomHa:        10,
    VerbalSuffix.VS_AspectMa:     11,
    VerbalSuffix.VS_IterJevy:     11,
    VerbalSuffix.VS_HabitMi:      11,
    VerbalSuffix.VS_HabitVa:      11,
    VerbalSuffix.VS_FrustrRei:    11,
    VerbalSuffix.VS_Desiderative: 11,
    VerbalSuffix.VS_Simultaneous: 11,
    VerbalSuffix.VS_InterrogPa:   12,
    VerbalSuffix.VS_HearsayJe:    13,
}

# Surface strings (mirror render_verbal_suffix in Verb.v §9b)
# dict value = {Orality.Oral: str, Orality.Nasal: str} when orality-sensitive
_SUFFIX_SURFACES: dict[VerbalSuffix, str | dict] = {
    VerbalSuffix.VS_CausUka:      "uka",
    VerbalSuffix.VS_AbilKuaa:     "kuaa",
    VerbalSuffix.VS_TotalPa:      {Orality.Oral: "pa",   Orality.Nasal: "mba"},
    VerbalSuffix.VS_ImpForce:     "ke",
    VerbalSuffix.VS_ImpRequest:   "na",
    VerbalSuffix.VS_ImpPlead:     "mi",
    VerbalSuffix.VS_ImpUrge:      "py",
    VerbalSuffix.VS_Volitive:     "se",
    VerbalSuffix.VS_ComparVe:     "ve",
    VerbalSuffix.VS_FutTa:        "ta",
    VerbalSuffix.VS_FutNe:        "ne",
    VerbalSuffix.VS_FutNegMoa:    "mo'ã",
    VerbalSuffix.VS_ImmFutPota:   {Orality.Oral: "pota",  Orality.Nasal: "mbota"},
    VerbalSuffix.VS_ObligVaera:   "va'erã",
    VerbalSuffix.VS_PastVaekue:   "va'ekue",
    VerbalSuffix.VS_NegI:         "i",
    VerbalSuffix.VS_NegRi:        "ri",
    VerbalSuffix.VS_NegTei:       "tei",
    VerbalSuffix.VS_Privative:    "'ỹ",
    VerbalSuffix.VS_Intensifier:  {Orality.Oral: "ite",   Orality.Nasal: "ete"},
    VerbalSuffix.VS_NomVa:        "va",
    VerbalSuffix.VS_NomHa:        "ha",
    VerbalSuffix.VS_AspectMa:     "ma",
    VerbalSuffix.VS_IterJevy:     "jevy",
    VerbalSuffix.VS_HabitMi:      "mi",
    VerbalSuffix.VS_HabitVa:      "va",
    VerbalSuffix.VS_FrustrRei:    "rei",
    VerbalSuffix.VS_InterrogPa:   "pa",
    VerbalSuffix.VS_Desiderative: "nga'u",
    VerbalSuffix.VS_Simultaneous: "vo",
    VerbalSuffix.VS_HearsayJe:    "je",
}

# Suffix stripper index: surface string → list of matching suffixes
# (one surface can match multiple — e.g. "mi" = VS_ImpPlead or VS_HabitMi)
# Sorted longest-first so greedier matches win.
SUFFIX_STRIP_INDEX: list[tuple[str, VerbalSuffix]] = sorted(
    [
        (surf if isinstance(surf, str) else surf[Orality.Oral], suf)
        for suf, surf in _SUFFIX_SURFACES.items()
    ]
    + [
        (surf[Orality.Nasal], suf)
        for suf, surf in _SUFFIX_SURFACES.items()
        if isinstance(surf, dict)
    ],
    key=lambda t: -len(t[0])
)


# ============================================================
#  Irregular verbs (§16 Verb.v)
# ============================================================

class IrregularVerb(Enum):
    Irreg_Ju = "Irreg_Ju"
    Irreg_Ho = "Irreg_Ho"
    Irreg_E  = "Irreg_E"

    def to_coq(self) -> str:
        return self.value


# Paradigm table: (IrregularVerb, Person, Number, Optional[Inclusivity]) → surface
# Mirrors irreg_form in §16 Verb.v exactly.
IRREG_PARADIGM: dict[tuple, str] = {
    (IrregularVerb.Irreg_Ju, Person.First,  Number.Singular, None):                    "aju",
    (IrregularVerb.Irreg_Ju, Person.Second, Number.Singular, None):                    "reju",
    (IrregularVerb.Irreg_Ju, Person.Third,  Number.Singular, None):                    "ou",
    (IrregularVerb.Irreg_Ju, Person.Third,  Number.Plural,   None):                    "ou",
    (IrregularVerb.Irreg_Ju, Person.First,  Number.Plural,   Inclusivity.Inclusive):   "jaju",
    (IrregularVerb.Irreg_Ju, Person.First,  Number.Plural,   Inclusivity.Exclusive):   "roju",
    (IrregularVerb.Irreg_Ju, Person.Second, Number.Plural,   None):                    "peju",

    (IrregularVerb.Irreg_Ho, Person.First,  Number.Singular, None):                    "aha",
    (IrregularVerb.Irreg_Ho, Person.Second, Number.Singular, None):                    "reho",
    (IrregularVerb.Irreg_Ho, Person.Third,  Number.Singular, None):                    "oho",
    (IrregularVerb.Irreg_Ho, Person.Third,  Number.Plural,   None):                    "oho",
    (IrregularVerb.Irreg_Ho, Person.First,  Number.Plural,   Inclusivity.Inclusive):   "jaha",
    (IrregularVerb.Irreg_Ho, Person.First,  Number.Plural,   Inclusivity.Exclusive):   "roho",
    (IrregularVerb.Irreg_Ho, Person.Second, Number.Plural,   None):                    "peho",

    (IrregularVerb.Irreg_E,  Person.First,  Number.Singular, None):                    "ha'e",
    (IrregularVerb.Irreg_E,  Person.Second, Number.Singular, None):                    "ere",
    (IrregularVerb.Irreg_E,  Person.Third,  Number.Singular, None):                    "he'i",
    (IrregularVerb.Irreg_E,  Person.Third,  Number.Plural,   None):                    "he'i",
    (IrregularVerb.Irreg_E,  Person.First,  Number.Plural,   Inclusivity.Inclusive):   "ja'e",
    (IrregularVerb.Irreg_E,  Person.First,  Number.Plural,   Inclusivity.Exclusive):   "ro'e",
    (IrregularVerb.Irreg_E,  Person.Second, Number.Plural,   None):                    "peje",
}

# Reverse index: surface form → (IrregularVerb, Person, Number, Optional[Inclusivity])
# Used by the analyzer to detect irregular citation forms.
IRREG_FORM_INDEX: dict[str, tuple] = {
    surface: key for key, surface in IRREG_PARADIGM.items()
}


# ============================================================
#  Verb record (§13 Verb.v)
# ============================================================

@dataclass
class Verb:
    v_class:        VerbClass
    v_orality:      Orality
    v_root:         str
    v_transitivity: Transitivity
    v_root_class:   VerbRootClass      = VerbRootClass.VRoot_Plain
    v_chendal_3sg:  Chendal3sgForm     = Chendal3sgForm.C3sg_I

    def to_coq(self) -> str:
        return (
            f"(mkVerb {self.v_class.to_coq()} {self.v_orality.to_coq()} "
            f'"{self.v_root}" {self.v_transitivity.to_coq()} '
            f"{self.v_root_class.to_coq()} {self.v_chendal_3sg.to_coq()})"
        )


# ============================================================
#  VerbForm (§13 Verb.v)
# ============================================================

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


# ============================================================
#  ConjugatedVerb (§17 Verb.v)
# ============================================================

@dataclass
class ConjugatedVerb:
    verb_form:  VerbForm
    person:     Person
    number:     Number
    incl:       Optional[Inclusivity]      = None
    mood:       Mood                       = Mood.Indicative
    polarity:   Polarity                   = Polarity.Positive
    voice:      Voice                      = Voice.Active
    suffixes:   list[VerbalSuffix]         = field(default_factory=list)
    evidential: Optional[Evidential]       = None

    @property
    def orality(self) -> Orality:
        if isinstance(self.verb_form, VF_Regular):
            return self.verb_form.verb.v_orality
        return Orality.Oral   # irregulars are all oral

    def to_coq(self) -> str:
        incl_coq = (
            f"(Some {self.incl.to_coq()})" if self.incl else "None"
        )
        suffixes_coq = (
            "[" + "; ".join(s.to_coq() for s in self.suffixes) + "]"
            if self.suffixes else "nil"
        )
        ev_coq = (
            f"(Some {self.evidential.to_coq()})" if self.evidential else "None"
        )
        return (
            f"(mkConjVerb {self.verb_form.to_coq()} "
            f"{self.person.to_coq()} {self.number.to_coq()} "
            f"{incl_coq} {self.mood.to_coq()} {self.polarity.to_coq()} "
            f"{self.voice.to_coq()} {suffixes_coq} {ev_coq})"
        )


# ============================================================
#  Lightweight NP (v1: just enough for agreement checking)
# ============================================================

@dataclass
class NP:
    surface:      str
    person:       Person       = Person.Third
    number:       Number       = Number.Singular
    human:        bool         = False

    # Exactly one of these constructor groups is populated:
    pronoun:      Optional[SubjPronoun]  = None       # NP_PronSubj
    noun:         Optional[Noun]         = None       # NP_Bare or head of compound
    possessor:    Optional[PossMarker]   = None       # NP_Poss   (with noun)
    demonstrative: Optional[DemProximity] = None      # NP_Dem    (with noun, number)
    adjective:    Optional[Adjective]    = None       # NP_Adj    (with noun)
    numeral_coq:  Optional[str]          = None       # NP_Num    (with noun), built Coq term

    coq_term:     Optional[str]          = None       # full override

    def to_coq(self) -> str:
        if self.coq_term:
            return self.coq_term
        if self.pronoun is not None:
            return f"(NP_PronSubj {self.pronoun.to_coq()})"
        if self.noun is not None:
            if self.possessor is not None:
                return f"(NP_Poss {self.possessor.to_coq()} {self.noun.to_coq()})"
            if self.demonstrative is not None:
                return (
                    f"(NP_Dem {self.demonstrative.to_coq()} "
                    f"{self.number.to_coq()} {self.noun.to_coq()})"
                )
            if self.adjective is not None:
                return f"(NP_Adj {self.noun.to_coq()} {self.adjective.to_coq()})"
            if self.numeral_coq is not None:
                return f"(NP_Num {self.numeral_coq} {self.noun.to_coq()})"
            return f"(NP_Bare {self.noun.to_coq()})"
        raise ValueError(f"NP for '{self.surface}' has no valid Coq representation yet")

# ============================================================
#  Sentence (mirror simple_sentence in Sentences.v)
# ============================================================

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
    DemProxSpeaker  = "DemProxSpeaker"
    DemProxHearer   = "DemProxHearer"
    DemDistal       = "DemDistal"
    DemSharedPerson = "DemSharedPerson"
    DemSharedEvent  = "DemSharedEvent"
    DemHearsay      = "DemHearsay"

    def to_coq(self) -> str:
        return self.value


# Adjectival demonstrative surface (used before head noun). Mirrors
# dem_adj_form in noun_phrases.v.
DEM_ADJ_SURFACE: dict[tuple[DemProximity, Number], str] = {
    (DemProximity.DemProxSpeaker,  Number.Singular): "ko",
    (DemProximity.DemProxSpeaker,  Number.Plural):   "ko'ã",
    (DemProximity.DemProxHearer,   Number.Singular): "pe",
    (DemProximity.DemProxHearer,   Number.Plural):   "umi",
    (DemProximity.DemDistal,       Number.Singular): "amo",
    (DemProximity.DemDistal,       Number.Plural):   "umi",
    (DemProximity.DemSharedPerson, Number.Singular): "ku",
    (DemProximity.DemSharedPerson, Number.Plural):   "umi",
    (DemProximity.DemSharedEvent,  Number.Singular): "ako",
    (DemProximity.DemSharedEvent,  Number.Plural):   "umi",
    (DemProximity.DemHearsay,      Number.Singular): "aipo",
    (DemProximity.DemHearsay,      Number.Plural):   "umi",
}

DEM_ADJ_FORM_INDEX: dict[str, list[tuple[DemProximity, Number]]] = {}
for (dp, n), surf in DEM_ADJ_SURFACE.items():
    DEM_ADJ_FORM_INDEX.setdefault(surf, []).append((dp, n))


class Postposition(Enum):
    Post_Pe    = "Post_Pe"
    Post_Gui   = "Post_Gui"
    Post_Gua   = "Post_Gua"
    Post_Rehe  = "Post_Rehe"
    Post_Ndive = "Post_Ndive"
    Post_Guive = "Post_Guive"
    Post_Peve  = "Post_Peve"
    Post_Rupi  = "Post_Rupi"
    Post_Ari   = "Post_Ari"
    Post_Guy   = "Post_Guy"
    Post_Guara = "Post_Guara"
    Post_Hagua = "Post_Hagua"

    def to_coq(self) -> str:
        return self.value


# Surface forms by orality. Mirrors postposition_form in noun_phrases.v.
# Most postpositions are orality-invariant.
POSTPOSITION_SURFACE: dict[tuple[Postposition, Orality], str] = {
    (Postposition.Post_Pe,    Orality.Oral):  "pe",
    (Postposition.Post_Pe,    Orality.Nasal): "me",
    (Postposition.Post_Gui,   Orality.Oral):  "gui",
    (Postposition.Post_Gui,   Orality.Nasal): "gui",
    (Postposition.Post_Gua,   Orality.Oral):  "gua",
    (Postposition.Post_Gua,   Orality.Nasal): "gua",
    (Postposition.Post_Rehe,  Orality.Oral):  "rehe",
    (Postposition.Post_Rehe,  Orality.Nasal): "rehe",
    (Postposition.Post_Ndive, Orality.Oral):  "ndive",
    (Postposition.Post_Ndive, Orality.Nasal): "ndie",
    (Postposition.Post_Guive, Orality.Oral):  "guive",
    (Postposition.Post_Guive, Orality.Nasal): "guive",
    (Postposition.Post_Peve,  Orality.Oral):  "peve",
    (Postposition.Post_Peve,  Orality.Nasal): "peve",
    (Postposition.Post_Rupi,  Orality.Oral):  "rupi",
    (Postposition.Post_Rupi,  Orality.Nasal): "rupi",
    (Postposition.Post_Ari,   Orality.Oral):  "'ári",
    (Postposition.Post_Ari,   Orality.Nasal): "'ári",
    (Postposition.Post_Guy,   Orality.Oral):  "guy",
    (Postposition.Post_Guy,   Orality.Nasal): "guy",
    (Postposition.Post_Guara, Orality.Oral):  "guarã",
    (Postposition.Post_Guara, Orality.Nasal): "guarã",
    (Postposition.Post_Hagua, Orality.Oral):  "haguã",
    (Postposition.Post_Hagua, Orality.Nasal): "haguã",
}

# Reverse: surface suffix (longest-first) → list of (Postposition, Orality)
# Used by the analyzer to strip postpositions from compound surface forms
# like "sype" = "sy" + "pe".
POSTPOSITION_STRIP_INDEX: list[tuple[str, Postposition, Orality]] = sorted(
    [(surf, pp, o) for (pp, o), surf in POSTPOSITION_SURFACE.items()],
    key=lambda t: -len(t[0])
)


class SentenceType(Enum):
    ST_Declarative   = "ST_Declarative"
    ST_Interrogative = "ST_Interrogative"
    ST_Exclamative   = "ST_Exclamative"

    def to_coq(self) -> str:
        return self.value


@dataclass
class Sentence:
    verb:         ConjugatedVerb
    subject:      Optional[NP]           = None
    direct_obj:   Optional[NP]           = None
    indirect_obj: Optional[NP]           = None
    postp_comp:   Optional[NP]           = None
    word_order:   WordOrder              = WordOrder.WO_SVO
    sent_type:    SentenceType           = SentenceType.ST_Declarative
    interrog:     Optional[str]          = None   # interrogative particle
    hikuai:       bool                   = False

    def _opt_np(self, np: Optional[NP]) -> str:
        return f"(Some {np.to_coq()})" if np else "None"

    def _opt_str(self, s: Optional[str]) -> str:
        return f'(Some "{s}")' if s else "None"

    def to_coq(self) -> str:
        return (
            f"(mkSentence\n"
            f"  {self._opt_np(self.subject)}\n"
            f"  {self.verb.to_coq()}\n"
            f"  {self._opt_np(self.direct_obj)}\n"
            f"  {self._opt_np(self.indirect_obj)}\n"
            f"  {self._opt_np(self.postp_comp)}\n"
            f"  {self.word_order.to_coq()}\n"
            f"  {self.sent_type.to_coq()}\n"
            f"  {self._opt_str(self.interrog)}\n"
            f"  {'true' if self.hikuai else 'false'})"
        )

    def to_coq_compute(self) -> str:
        """Full `Compute wf_sentence <term>.` string for coqc."""
        return f"Compute wf_sentence {self.to_coq()}."