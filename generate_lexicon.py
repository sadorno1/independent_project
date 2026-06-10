import csv
import re
import unicodedata
from pathlib import Path

# =========================
# NORMALIZATION
# =========================
APOSTROPHE_VARIANTS = ["’", "ʼ", "‘", "´", "`"]

def normalize_apostrophes(s: str) -> str:
    for a in APOSTROPHE_VARIANTS:
        s = s.replace(a, "'")
    return s

def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = normalize_apostrophes(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# =========================
# NASALITY DETECTION
# =========================
NASAL_VOWELS = {"ã", "ẽ", "ĩ", "õ", "ũ", "ỹ"}
NASAL_CONS = {"m", "n", "ñ"}  # plus g̃ handled below
NASAL_DIGRAPHS = ["mb", "nd", "ng", "nt"]

def has_g_tilde(s: str) -> bool:
    nfd = unicodedata.normalize("NFD", s)
    return "g\u0303" in nfd or "G\u0303" in nfd

def is_nasal(word: str) -> bool:
    w = norm_text(word).lower()
    if has_g_tilde(w):
        return True
    for dg in NASAL_DIGRAPHS:
        if dg in w:
            return True
    for ch in w:
        if ch in NASAL_VOWELS or ch in NASAL_CONS:
            return True
    return False

# =========================
# TYPE PARSING
# =========================
def parse_types(types_str: str) -> list[str]:
    raw = norm_text(types_str)
    if not raw:
        return []
    parts = re.split(r"[|,]", raw)
    out = []
    for p in parts:
        t = norm_text(p).lower()
        if t:
            out.append(t)
    # dedup preserving order
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq

# =========================
# MAP CSV TAGS -> minimal pos
# =========================
# These constructors must exist in GuaraniLexiconTypes.v:
# POS_PRON POS_NOUN POS_VERB_AREAL POS_VERB_ATTR POS_CONJ POS_OTHER

TAG_TO_POS = {
    "pron.": "POS_PRON",
    "s.": "POS_NOUN",
    "conj.": "POS_CONJ",

    # verb-ish tags -> decide policy
    "v. air.": "POS_VERB_AREAL",
    "v. atr.": "POS_VERB_ATTR",

    # for now, bucket generic verbs into AREAL (you can refine later)
    "v.": "POS_VERB_AREAL",
    "v. pr.": "POS_VERB_AREAL",
}

# =========================
# COQ STRING / IDENT HELPERS
# =========================
def coq_escape_string(s: str) -> str:
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return s

def sanitize_ident(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "_", s)
    if re.match(r"^\d", s):
        s = "w_" + s
    if not s:
        s = "w_empty"
    return s

def mk_list(items: list[str]) -> str:
    if not items:
        return "[]"
    return "[" + "; ".join(items) + "]"

# =========================
# MAIN
# =========================
def main():
    in_path = Path("word_types.csv")
    out_path = Path("LexiconGenerated.v")

    rows: list[tuple[str, str]] = []
    with in_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header. Expected: word,types")
        fields = {h.strip().lower() for h in reader.fieldnames}
        if not {"word", "types"}.issubset(fields):
            raise ValueError(f"CSV must have headers word,types. Found: {reader.fieldnames}")

        for r in reader:
            word = norm_text(r.get("word", ""))
            types = norm_text(r.get("types", ""))
            if not word or not types:
                continue
            rows.append((word, types))

    decls_entries: list[str] = []
    lookup_cases: list[str] = []
    entry_names: set[str] = set()
    seen_lookup_forms: set[str] = set()

    for idx, (word, types_str) in enumerate(rows):
        tlist = parse_types(types_str)

        # POS tags (minimal)
        pos_tags: list[str] = []
        for t in tlist:
            if t in TAG_TO_POS:
                pos_tags.append(TAG_TO_POS[t])

        # fallback: keep entry but tag as POS_OTHER
        if not pos_tags:
            pos_tags = ["POS_OTHER"]

        # orality from spelling
        oral = "NASAL" if is_nasal(word) else "ORAL"

        # unique Coq name
        coq_name = "w_" + sanitize_ident(word)
        if coq_name in entry_names:
            coq_name = f"{coq_name}_{idx}"
        entry_names.add(coq_name)

        w_esc = coq_escape_string(word)

        decls_entries.append(
            f"Definition {coq_name} : lex_entry :=\n"
            f"  {{| e_form := \"{w_esc}\";\n"
            f"     e_orality := {oral};\n"
            f"     e_pos := {mk_list(pos_tags)}\n"
            f"  |}}.\n"
        )

        # lookup case by surface string (dedup exact surface forms).
        # Keep the first occurrence to avoid redundant match patterns.
        if word not in seen_lookup_forms:
            lookup_cases.append(f"  | \"{w_esc}\" => Some {coq_name}\n")
            seen_lookup_forms.add(word)

    content: list[str] = []
    content.append("(* AUTO-GENERATED FROM word_types.csv. DO NOT EDIT BY HAND. *)\n")
    content.append("From Stdlib Require Import String List.\n")
    content.append("Import ListNotations.\n")
    content.append("Open Scope string_scope.\n\n")
    content.append("Require Import GuaraniCore.\n")
    content.append("Require Import GuaraniLexiconTypes.\n\n")

    content.extend(decls_entries)
    content.append("\n")

    # Match-based lookup (simple + fast)
    content.append("Definition lookup (s : string) : option lex_entry :=\n")
    content.append("  match s with\n")
    content.extend(lookup_cases)
    content.append("  | _ => None\n")
    content.append("  end.\n")

    out_path.write_text("".join(content), encoding="utf-8")
    print(f"Wrote {out_path} with {len(lookup_cases)} entries total.")

if __name__ == "__main__":
    main()
