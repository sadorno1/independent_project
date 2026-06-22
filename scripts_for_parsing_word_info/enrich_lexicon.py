"""
enrich_lexicon.py

Processes a raw CSV (word, pos) of Estigarribia POS tags into an enriched CSV 
with split multi-POS rows linked by a stable lemma_id, formatted for 
the morphological analyzer.
"""

import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Tag dispatch mappings
# ---------------------------------------------------------------------------

PRIMARY_POS_TAGS = {
    "s.": "noun", "f.": "noun", "m.": "noun", "amb.": "noun", "com.": "noun",
    "v.": "verb", "v. air.": "verb", "v. atr.": "verb", "v. pr.": "verb", "v. irr.": "verb",
    "adj.": "adj", "adj. f.": "adj", "adj. m.": "adj",
    "adv.": "adv", "num.": "num", "pron.": "pron", "exp.": "exp",
    "p.n.": "postp", "p.v.": "postp", "prep.": "prep", "conj.": "conj",
    "art.": "art", "dem.": "dem", "suf.": "suf", "suf. a.n.": "suf",
    "suf. a.v.": "suf", "pref.": "pref", "pref. a.n.": "pref", "pref. a.v.": "pref",
}

MODIFIER_TAGS = {
    "neol.", "arc.", "fig.", "h.", "def.", "imp.", "aux.", "prnl.",
    "irr.", "sub.", "rel.", "voc.", "exclam.", "int.", "ind.", "pers.",
    "pos.", "sing.", "pl.", "tón.", "át.", "U.t.c.", "U.t.c.s.", "neg.",
    "ap.", "af.", "inl.", "excl.", "a.n.", "a.v.",
}

VERB_PROPERTY_TAGS = {"tr.", "intr.", "atr.", "air.", "irr.", "pr."}
NOUN_PROPERTY_TAGS = {"t.", "bif.", "f.", "m.", "amb.", "com."}

# ---------------------------------------------------------------------------
# Orality detection
# ---------------------------------------------------------------------------

NASAL_VOWELS = set("ãẽĩõũỹÃẼĨÕŨỸ")
NASAL_LETTERS = set("ñÑ")
NASAL_DIGRAPHS = ["mb", "nd", "ng", "nt"]

def detect_orality(word: str) -> tuple[str, bool]:
    """Returns (orality, mixed_flag) based on nasal vowels, letters, and digraphs."""
    has_nasal_vowel = any(c in NASAL_VOWELS for c in word)
    has_nasal_letter = any(c in NASAL_LETTERS for c in word)
    has_nasal_digraph = any(d in word.lower() for d in NASAL_DIGRAPHS)

    is_nasal = has_nasal_vowel or has_nasal_letter or has_nasal_digraph

    mixed = False
    if is_nasal and len(word) > 6:
        for i, c in enumerate(word):
            if c in NASAL_VOWELS or c in NASAL_LETTERS:
                if 2 < i < len(word) - 2:
                    mixed = True
                break

    return ("Nasal" if is_nasal else "Oral"), mixed


# ---------------------------------------------------------------------------
# Tag parsing
# ---------------------------------------------------------------------------

# Multi-word tags sorted by length to ensure proper eager matching
ATOMIC_MULTIWORD_TAGS = [
    "pref. a.n.", "pref. a.v.", "suf. a.n.", "suf. a.v.",
    "v. air.", "v. atr.", "v. pr.", "v. irr.", "adj. f.", "adj. m.",
]

def parse_pos_tags(pos_str: str) -> list[str]:
    """Splits pipe and space-separated tags while preserving atomic multi-word tags."""
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
    """Groups tags by primary POS. Deduplicates multiple primary tags of the same category."""
    primaries = []
    modifiers = []

    for t in tags:
        if t in PRIMARY_POS_TAGS:
            primaries.append(t)
        else:
            modifiers.append(t)

    if not primaries:
        return [("other", tags)]

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
        "lemma_id": lemma_id, "word": word, "primary_pos": primary_pos,
        "verb_class": "", "transitivity": "", "is_irregular": "", "irregular_lemma": "",
        "root_class": "", "gender": "", "orality": "", "human": "", "flags": "", "raw_pos": raw_pos,
    }

    orality, mixed = detect_orality(word)
    out["orality"] = orality
    if mixed:
        flags.append("CHECK_NASAL_COMPOUND")

    tagset = set(applicable_tags)

    if primary_pos == "verb":
        irr = lookup_irregular(word)
        if irr is not None:
            # Overrides tags if explicitly matched to an irregular conjugated form
            lemma, slot = irr
            out["verb_class"] = "Irregular"
            out["is_irregular"] = "true"
            out["irregular_lemma"] = f"Irreg_{lemma}"
            flags.append(f"CONJUGATED_FORM_OF_{slot}")
            if "tr." in tagset:
                out["transitivity"] = "Transitive"
            elif "intr." in tagset:
                out["transitivity"] = "Intransitive"
        else:
            if "v. air." in tagset or "air." in tagset:
                out["verb_class"] = "Aireal"
            elif "v. atr." in tagset or "atr." in tagset:
                out["verb_class"] = "Chendal"
            elif "v. irr." in tagset or "irr." in tagset:
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
        if "t." in tagset:
            out["root_class"] = "Triform"
        elif "bif." in tagset:
            out["root_class"] = "Biform"
        else:
            out["root_class"] = "Uniform"

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
# Irregular paradigm lookup
# ---------------------------------------------------------------------------

IRREGULAR_PARADIGMS = {
    "Ju": {  # venir
        "ou": "Ju_3sg", "aju": "Ju_1sg", "reju": "Ju_2sg",
        "jaju": "Ju_1pl_incl", "roju": "Ju_1pl_excl", "peju": "Ju_2pl",
    },
    "Ho": {  # ir
        "oho": "Ho_3sg", "aha": "Ho_1sg", "reho": "Ho_2sg",
        "jaha": "Ho_1pl_incl", "roho": "Ho_1pl_excl", "peho": "Ho_2pl",
    },
    "E": {  # decir
        "he'i": "E_3sg", "ha'e": "E_1sg", "ere": "E_2sg",
        "ja'e": "E_1pl_incl", "ro'e": "E_1pl_excl", "peje": "E_2pl",
    },
}

IRREGULAR_FORM_INDEX = {
    form: (lemma, slot)
    for lemma, paradigm in IRREGULAR_PARADIGMS.items()
    for form, slot in paradigm.items()
}

def lookup_irregular(word: str) -> tuple[str, str] | None:
    return IRREGULAR_FORM_INDEX.get(word.lower())


# ---------------------------------------------------------------------------
# Processing pipeline & Main
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "lemma_id", "word", "primary_pos", "verb_class", "transitivity", 
    "is_irregular", "irregular_lemma", "root_class", "gender", 
    "orality", "human", "flags", "raw_pos",
]

def enrich(input_path: Path, output_path: Path) -> dict:
    stats = {"rows_in": 0, "rows_out": 0, "by_pos": {}, "by_flag": {}}

    with input_path.open(encoding="utf-8") as fin, \
         output_path.open("w", encoding="utf-8", newline="") as fout:

        reader = csv.reader(fin)
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        writer.writeheader()

        first = next(reader, None)
        if first is None:
            return stats

        is_header = not any("." in c for c in first) and first[0].lower() in ("word", "lemma", "term")
        rows_iter = iter(reader) if is_header else iter([first] + list(reader))

        for i, row in enumerate(rows_iter):
            if len(row) < 2:
                continue
            word, raw_pos = row[0].strip(), row[1].strip()
            if not word or not raw_pos:
                continue

            stats["rows_in"] += 1
            lemma_id = f"L{i:06d}"
            tags = parse_pos_tags(raw_pos)

            for primary_pos, applicable in split_into_primaries(tags):
                out_row = enrich_row(word, primary_pos, applicable, raw_pos, lemma_id)
                writer.writerow(out_row)
                
                stats["rows_out"] += 1
                stats["by_pos"][primary_pos] = stats["by_pos"].get(primary_pos, 0) + 1
                for f in out_row["flags"].split("|"):
                    if f:
                        stats["by_flag"][f] = stats["by_flag"].get(f, 0) + 1

    return stats


def main():
    if len(sys.argv) < 3:
        print("usage: enrich_lexicon.py INPUT.csv OUTPUT.csv", file=sys.stderr)
        sys.exit(2)
        
    stats = enrich(Path(sys.argv[1]), Path(sys.argv[2]))

    print(f"rows in:  {stats['rows_in']}")
    print(f"rows out: {stats['rows_out']}\n")
    print("by primary_pos:")
    for k, v in sorted(stats["by_pos"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:10s} {v}")
    print("\nreview flags raised:")
    for k, v in sorted(stats["by_flag"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:25s} {v}")


if __name__ == "__main__":
    main()