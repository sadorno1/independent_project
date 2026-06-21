"""
enrich_lexicon.py

Input:  raw CSV with columns: word, pos
        where pos is a pipe-separated list of Estigarribia POS tags
        (e.g. "adj.|s.", "v. atr.", "neol.|s.")

Output: enriched CSV ready for use by the morphological analyzer,
        with one row per (word, primary_pos) split, sharing a lemma_id.

Columns added:
  lemma_id        stable ID linking split rows from the same source row
  primary_pos     one of: noun, verb, adj, adv, num, pron, exp, postp, prep,
                  conj, art, dem, suf, pref, other
  verb_class      Areal | Aireal | Chendal | Irregular | ""    (verbs only)
  transitivity    Transitive | Intransitive | ""               (verbs only)
  is_irregular    bool                                          (verbs only)
  root_class      Uniform | Biform | Triform | ""               (nouns only)
  gender          GendMasc | GendFem | GendAmb | GendNone       (nouns only)
  orality         Oral | Nasal                                  (computed)
  human           ""                                            (always blank — manual)
  flags           pipe-separated review flags
  raw_pos         original pos string (preserved for audit)

Flags emitted when manual review is warranted:
  CHECK_CONJUGATED_FORM   verb looks like a conjugated citation form (aha, oho, che-...)
  CHECK_IRREGULAR_MAPPING irregular verb — pick Irreg_Ju / Irreg_Ho / Irreg_E
  CHECK_NASAL_COMPOUND    multi-morpheme word with mixed orality cues
  CHECK_GENDER_AMBIGUOUS  amb. or com. tag — needs disambiguation
  CHECK_VERB_CLASS        v. pr. — verify Areal mapping
  CHECK_TRANSITIVITY      verb with no tr./intr. tag
  CHECK_ROOT_CLASS        noun with no t./bif. tag (defaults to Uniform)
"""

import csv
import sys
import re
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Tag dispatch
# ---------------------------------------------------------------------------

# Tags that determine the primary POS bucket. Multi-POS source rows are split
# into one output row per primary_pos.
PRIMARY_POS_TAGS = {
    "s.": "noun",
    "f.": "noun",
    "m.": "noun",
    "amb.": "noun",
    "com.": "noun",
    "v.": "verb",
    "v. air.": "verb",
    "v. atr.": "verb",
    "v. pr.": "verb",
    "v. irr.": "verb",
    "adj.": "adj",
    "adj. f.": "adj",
    "adj. m.": "adj",
    "adv.": "adv",
    "num.": "num",
    "pron.": "pron",
    "exp.": "exp",
    "p.n.": "postp",
    "p.v.": "postp",
    "prep.": "prep",
    "conj.": "conj",
    "art.": "art",
    "dem.": "dem",
    "suf.": "suf",
    "suf. a.n.": "suf",
    "suf. a.v.": "suf",
    "pref.": "pref",
    "pref. a.n.": "pref",
    "pref. a.v.": "pref",
}

# Modifier tags — refine the row but don't change primary_pos.
# (neol., arc., fig., h., def., imp., aux., prnl., irr., sub., rel., voc.,
#  exclam., int., ind., pers., pos., dem., sing., pl., tón., át., U.t.c.,
#  U.t.c.s., neg., ap., af., inl., excl.)
MODIFIER_TAGS = {
    "neol.", "arc.", "fig.", "h.", "def.", "imp.", "aux.", "prnl.",
    "irr.", "sub.", "rel.", "voc.", "exclam.", "int.", "ind.", "pers.",
    "pos.", "sing.", "pl.", "tón.", "át.", "U.t.c.", "U.t.c.s.", "neg.",
    "ap.", "af.", "inl.", "excl.",
    # accident markers — not standalone POS
    "a.n.", "a.v.",
}

# These tags refine verb/noun properties.
VERB_PROPERTY_TAGS = {"tr.", "intr.", "atr.", "air.", "irr.", "pr."}
NOUN_PROPERTY_TAGS = {"t.", "bif.", "f.", "m.", "amb.", "com."}

# ---------------------------------------------------------------------------
# Orality detection
# ---------------------------------------------------------------------------

NASAL_VOWELS = set("ãẽĩõũỹÃẼĨÕŨỸ")
# Tilde-bearing nasal consonant
NASAL_LETTERS = set("ñÑ")
# Nasal consonant clusters that anchor nasal harmony domains
NASAL_DIGRAPHS = ["mb", "nd", "ng", "nt"]

def detect_orality(word: str) -> tuple[str, bool]:
    """
    Returns (orality, mixed_flag).
    orality is "Nasal" if any nasal cue is found, else "Oral".
    mixed_flag is True if word contains BOTH nasal and clearly oral material
    spanning what looks like a morpheme boundary — heuristically, length > 6
    and a nasal cue separated by 3+ oral chars from word boundaries.
    """
    has_nasal_vowel = any(c in NASAL_VOWELS for c in word)
    has_nasal_letter = any(c in NASAL_LETTERS for c in word)
    has_nasal_digraph = any(d in word.lower() for d in NASAL_DIGRAPHS)

    is_nasal = has_nasal_vowel or has_nasal_letter or has_nasal_digraph

    # Mixed-orality heuristic for compounds: long word, nasal cue not at the
    # word's leading or trailing edge.
    mixed = False
    if is_nasal and len(word) > 6:
        # Find position of first nasal cue
        for i, c in enumerate(word):
            if c in NASAL_VOWELS or c in NASAL_LETTERS:
                if 2 < i < len(word) - 2:
                    mixed = True
                break

    return ("Nasal" if is_nasal else "Oral"), mixed


# ---------------------------------------------------------------------------
# Tag parsing
# ---------------------------------------------------------------------------

# Multi-word tags that must be kept atomic — longest first so we match them
# before they get split into "v." + "air." etc.
ATOMIC_MULTIWORD_TAGS = [
    "pref. a.n.", "pref. a.v.",
    "suf. a.n.", "suf. a.v.",
    "v. air.", "v. atr.", "v. pr.", "v. irr.",
    "adj. f.", "adj. m.",
]

def parse_pos_tags(pos_str: str) -> list[str]:
    """
    Split 'adj.|s.' → ['adj.', 's.']
    Also split space-separated combos: 'v. tr.' → ['v.', 'tr.']
    while preserving atomic multi-word tags like 'v. air.', 'adj. f.'.
    """
    raw_parts = [t.strip() for t in pos_str.split("|") if t.strip()]
    out = []
    for part in raw_parts:
        remaining = part
        while remaining:
            matched = None
            for atom in ATOMIC_MULTIWORD_TAGS:
                if remaining.startswith(atom):
                    matched = atom
                    break
            if matched:
                out.append(matched)
                remaining = remaining[len(matched):].strip()
            else:
                toks = remaining.split(None, 1)
                out.append(toks[0])
                remaining = toks[1].strip() if len(toks) > 1 else ""
    return out


def split_into_primaries(tags: list[str]) -> list[tuple[str, list[str]]]:
    """
    Given the full tag list for one source row, group tags into one bucket
    per primary POS detected. Modifier tags attach to all groups.

    Returns: list of (primary_pos, applicable_tags) tuples.
    """
    primaries = []
    modifiers = []

    for t in tags:
        if t in PRIMARY_POS_TAGS:
            primaries.append(t)
        else:
            modifiers.append(t)

    if not primaries:
        return [("other", tags)]

    # Dedupe at the primary_pos bucket level. `s. f.` has two primary-eligible
    # tags (s. and f.) but they map to the same bucket (noun) — we want one
    # noun row, not two. Keep the *first* establishing tag per bucket; the
    # rest become modifiers attached to that row so gender/etc. still apply.
    seen_buckets = {}
    extra_modifiers_per_bucket = {}
    for p_tag in primaries:
        bucket = PRIMARY_POS_TAGS[p_tag]
        if bucket not in seen_buckets:
            seen_buckets[bucket] = p_tag
            extra_modifiers_per_bucket[bucket] = []
        else:
            extra_modifiers_per_bucket[bucket].append(p_tag)

    result = []
    for bucket, establishing in seen_buckets.items():
        applicable = [establishing] + extra_modifiers_per_bucket[bucket] + modifiers
        result.append((bucket, applicable))
    return result


# ---------------------------------------------------------------------------
# Row enrichment
# ---------------------------------------------------------------------------

def enrich_row(word: str, primary_pos: str, applicable_tags: list[str],
               raw_pos: str, lemma_id: str) -> dict:
    flags = []
    out = {
        "lemma_id": lemma_id,
        "word": word,
        "primary_pos": primary_pos,
        "verb_class": "",
        "transitivity": "",
        "is_irregular": "",
        "irregular_lemma": "",
        "root_class": "",
        "gender": "",
        "orality": "",
        "human": "",
        "flags": "",
        "raw_pos": raw_pos,
    }

    # Orality — always computable
    orality, mixed = detect_orality(word)
    out["orality"] = orality
    if mixed:
        flags.append("CHECK_NASAL_COMPOUND")

    tagset = set(applicable_tags)

    if primary_pos == "verb":
        # First: check if this is actually a conjugated form of an irregular.
        # This overrides whatever the CSV tags say.
        irr = lookup_irregular(word)
        if irr is not None:
            lemma, slot = irr
            out["verb_class"] = "Irregular"
            out["is_irregular"] = "true"
            out["irregular_lemma"] = f"Irreg_{lemma}"
            flags.append(f"CONJUGATED_FORM_OF_{slot}")
            # Transitivity still meaningful: ju/ho intransitive, e transitive-ish
            # Leave for manual review since semantics vary.
            if "tr." in tagset:
                out["transitivity"] = "Transitive"
            elif "intr." in tagset:
                out["transitivity"] = "Intransitive"
        else:
            # Regular verb-class dispatch
            if "v. air." in tagset or "air." in tagset:
                out["verb_class"] = "Aireal"
            elif "v. atr." in tagset or "atr." in tagset:
                out["verb_class"] = "Chendal"
            elif "v. irr." in tagset or "irr." in tagset:
                # CSV claims irregular but didn't match the paradigm table.
                # Flag for manual mapping — could be hareal/haireal that
                # Verb.v doesn't yet handle, or a new irregular.
                out["verb_class"] = "Irregular"
                out["is_irregular"] = "true"
                flags.append("CHECK_IRREGULAR_MAPPING")
            elif "v. pr." in tagset:
                out["verb_class"] = "Areal"
                flags.append("CHECK_VERB_CLASS")
            else:
                out["verb_class"] = "Areal"

            if out["is_irregular"] != "true":
                out["is_irregular"] = "false"

            if "tr." in tagset:
                out["transitivity"] = "Transitive"
            elif "intr." in tagset:
                out["transitivity"] = "Intransitive"
            else:
                flags.append("CHECK_TRANSITIVITY")

    elif primary_pos == "noun":
        # Root class — silent default to Uniform.
        # Triform/Biform are a small closed set; tag explicitly when known.
        if "t." in tagset:
            out["root_class"] = "Triform"
        elif "bif." in tagset:
            out["root_class"] = "Biform"
        else:
            out["root_class"] = "Uniform"

        # Gender
        if "f." in tagset:
            out["gender"] = "GendFem"
        elif "m." in tagset:
            out["gender"] = "GendMasc"
        elif "amb." in tagset or "com." in tagset:
            out["gender"] = "GendAmb"
            flags.append("CHECK_GENDER_AMBIGUOUS")
        else:
            out["gender"] = "GendNone"

    out["flags"] = "|".join(flags)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "lemma_id", "word", "primary_pos",
    "verb_class", "transitivity", "is_irregular", "irregular_lemma",
    "root_class", "gender", "orality", "human",
    "flags", "raw_pos",
]

# ---------------------------------------------------------------------------
# Irregular paradigm lookup
# ---------------------------------------------------------------------------
# Conservative: only the three genuinely-irregular paradigms in Verb.v
# (Irreg_Ju, Irreg_Ho, Irreg_E). Maps any conjugated form found as a dict
# citation form back to its lemma + slot.
#
# Slots: 1sg, 2sg, 3sg, 1pl_incl, 1pl_excl, 2pl, 3pl
# (3pl surface form is identical to 3sg in all three paradigms here;
#  hikuái or -kuéra disambiguates downstream.)

IRREGULAR_PARADIGMS = {
    "Ju": {  # venir
        "ou":   "Ju_3sg",  # also 3pl
        "aju":  "Ju_1sg",
        "reju": "Ju_2sg",
        "jaju": "Ju_1pl_incl",
        "roju": "Ju_1pl_excl",
        "peju": "Ju_2pl",
    },
    "Ho": {  # ir
        "oho":  "Ho_3sg",  # also 3pl
        "aha":  "Ho_1sg",
        "reho": "Ho_2sg",
        "jaha": "Ho_1pl_incl",
        "roho": "Ho_1pl_excl",
        "peho": "Ho_2pl",
    },
    "E": {  # decir
        "he'i": "E_3sg",   # also 3pl
        "ha'e": "E_1sg",
        "ere":  "E_2sg",
        "ja'e": "E_1pl_incl",
        "ro'e": "E_1pl_excl",
        "peje": "E_2pl",
    },
}

# Flat lookup: surface form → (lemma, slot)
IRREGULAR_FORM_INDEX = {}
for lemma, paradigm in IRREGULAR_PARADIGMS.items():
    for form, slot in paradigm.items():
        IRREGULAR_FORM_INDEX[form] = (lemma, slot)


def lookup_irregular(word: str) -> tuple[str, str] | None:
    """Return (lemma, slot) if word matches an irregular paradigm cell."""
    return IRREGULAR_FORM_INDEX.get(word.lower())

def enrich(input_path: Path, output_path: Path) -> dict:
    stats = {
        "rows_in": 0, "rows_out": 0,
        "by_pos": {}, "by_flag": {},
    }

    with input_path.open(encoding="utf-8") as fin, \
         output_path.open("w", encoding="utf-8", newline="") as fout:

        # Auto-detect whether the input has a header row by checking if the
        # first row looks like data (single-letter word with a POS-like tag).
        reader = csv.reader(fin)
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        writer.writeheader()

        first = next(reader, None)
        if first is None:
            return stats

        # Crude header check: if either cell contains a period, it's data.
        is_header = not any("." in c for c in first) and \
                    first[0].lower() in ("word", "lemma", "term")

        rows_iter = iter(reader) if is_header else iter([first] + list(reader))

        for i, row in enumerate(rows_iter):
            if len(row) < 2:
                continue
            word = row[0].strip()
            raw_pos = row[1].strip()
            if not word or not raw_pos:
                continue

            stats["rows_in"] += 1
            lemma_id = f"L{i:06d}"

            tags = parse_pos_tags(raw_pos)
            groups = split_into_primaries(tags)

            for primary_pos, applicable in groups:
                out_row = enrich_row(word, primary_pos, applicable,
                                     raw_pos, lemma_id)
                writer.writerow(out_row)
                stats["rows_out"] += 1
                stats["by_pos"][primary_pos] = \
                    stats["by_pos"].get(primary_pos, 0) + 1
                for f in out_row["flags"].split("|"):
                    if f:
                        stats["by_flag"][f] = stats["by_flag"].get(f, 0) + 1

    return stats


def main():
    if len(sys.argv) < 3:
        print("usage: enrich_lexicon.py INPUT.csv OUTPUT.csv", file=sys.stderr)
        sys.exit(2)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    stats = enrich(in_path, out_path)

    print(f"rows in:  {stats['rows_in']}")
    print(f"rows out: {stats['rows_out']}")
    print()
    print("by primary_pos:")
    for k, v in sorted(stats["by_pos"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:10s} {v}")
    print()
    print("review flags raised:")
    for k, v in sorted(stats["by_flag"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:25s} {v}")


if __name__ == "__main__":
    main()