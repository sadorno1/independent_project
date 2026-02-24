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
    return "g\u0303" in nfd or "G\u0303" in nfd  # g + combining tilde

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
    """
    CSV types column uses '|' but you said sometimes commas appear too.
    We split on both, then normalize spaces and apostrophes.
    """
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

def is_any_verb(types_list: list[str]) -> bool:
    # treat these as verbs (you can expand later)
    verbish = {"v.", "v. pr.", "v. atr.", "v. air."}
    return any(t in verbish for t in types_list)

# =========================
# MAP CSV TAGS -> GuaraniCore constructors
# =========================
# pos constructors in GuaraniCore.v:
# POS_NOUN POS_ADJ POS_ADV POS_VERB POS_VERB_PRED POS_VERB_ATTR POS_VERB_AIR
# POS_PRON POS_CONJ POS_INTERJ POS_VOC POS_EXP POS_H POS_PROPN POS_T
# POS_SUFFIX_N POS_SUFFIX_V POS_UNKNOWN

TAG_TO_POS = {
    "s.": "POS_NOUN",
    "adj.": "POS_ADJ",
    "adv.": "POS_ADV",
    "v.": "POS_VERB",
    "v. pr.": "POS_VERB_PRED",
    "v. atr.": "POS_VERB_ATTR",
    "v. air.": "POS_VERB_AIR",
    "pron.": "POS_PRON",
    "conj.": "POS_CONJ",
    "interj.": "POS_INTERJ",
    "voc.": "POS_VOC",
    "exp.": "POS_EXP",
    "h.": "POS_H",
    "p. n.": "POS_PROPN",
    "t.": "POS_T",
    "suf. a. n.": "POS_SUFFIX_N",
    "suf. a. v.": "POS_SUFFIX_V",
}

# subtypes (optional fields)
ADV_SUB = {
    "adv. de neg.": "ADV_NEG",
    "adv. de tiempo": "ADV_TIME",
}
PRON_SUB = {
    "pron. dem.": "PRON_DEM",
    "pron. ind.": "PRON_IND",
    "pron. pos.": "PRON_POS",
}
ADJ_SUB = {
    "adj. ind.": "ADJ_IND",
    "adj. ind. y pron. ind.": "ADJ_IND_AND_PRON_IND",
}

LABELS = {
    "neol.": "L_NEOL",
}

# =========================
# COQ STRING / IDENT HELPERS
# =========================
def coq_escape_string(s: str) -> str:
    # Coq string literals are double-quoted
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

    # Read CSV
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
    entry_names: list[str] = []

    for idx, (word, types_str) in enumerate(rows):
        tlist = parse_types(types_str)

        # POS tags
        pos_tags: list[str] = []
        for t in tlist:
            if t in TAG_TO_POS:
                pos_tags.append(TAG_TO_POS[t])

        # If we got nothing recognized, keep POS_UNKNOWN so the entry still exists
        if not pos_tags:
            pos_tags = ["POS_UNKNOWN"]

        # Labels
        labels: list[str] = []
        for t in tlist:
            if t in LABELS:
                labels.append(LABELS[t])

        # Subtypes (pick first matching; if multiple appear, you can change policy later)
        adv_sub = None
        pron_sub = None
        adj_sub = None
        for t in tlist:
            if adv_sub is None and t in ADV_SUB:
                adv_sub = ADV_SUB[t]
            if pron_sub is None and t in PRON_SUB:
                pron_sub = PRON_SUB[t]
            if adj_sub is None and t in ADJ_SUB:
                adj_sub = ADJ_SUB[t]

        adv_sub_coq = f"Some {adv_sub}" if adv_sub else "None"
        pron_sub_coq = f"Some {pron_sub}" if pron_sub else "None"
        adj_sub_coq = f"Some {adj_sub}" if adj_sub else "None"

        # Orality from spelling
        oral = "NASAL" if is_nasal(word) else "ORAL"

        # Verb conjugation class (Milestone 3 policy)
        # - irregular stems table in your grammar: ju, ho, 'e
        # - otherwise treat any verb-ish entry as VPropio
        w_low = word.lower()
        if w_low in {"ju", "ho", "'e"}:
            verb_conj = "Some VIrregular"
        elif is_any_verb(tlist):
            verb_conj = "Some VPropio"
        else:
            verb_conj = "None"

        coq_name = "w_" + sanitize_ident(word)
        if coq_name in entry_names:
            coq_name = f"{coq_name}_{idx}"
        entry_names.append(coq_name)

        w_esc = coq_escape_string(word)

        decls_entries.append(
            f"Definition {coq_name} : lex_entry :=\n"
            f"  {{| e_form := \"{w_esc}\";\n"
            f"     e_orality := {oral};\n"
            f"     e_pos := {mk_list(pos_tags)};\n"
            f"     e_labels := {mk_list(labels)};\n"
            f"     e_adv_sub := {adv_sub_coq};\n"
            f"     e_pron_sub := {pron_sub_coq};\n"
            f"     e_adj_sub := {adj_sub_coq};\n"
            f"     e_verb_conj := {verb_conj}\n"
            f"  |}}.\n"
        )

    entries_list_body = "; ".join(entry_names)

    content: list[str] = []
    content.append("(* AUTO-GENERATED FROM word_types.csv. DO NOT EDIT BY HAND. *)\n")
    content.append("From Stdlib Require Import String List.\n")
    content.append("Import ListNotations.\n")
    content.append("Open Scope string_scope.\n\n")
    content.append("Require Import GuaraniCore.\n\n")
    content.extend(decls_entries)
    content.append("\n")
    content.append(f"Definition lex_entries_generated : list lex_entry := [{entries_list_body}].\n\n")

    # Derive vroot list from entries (only entries with e_verb_conj = Some _)
    content.append(
        "Definition lex_verbs_generated : list vroot :=\n"
        "  fold_right\n"
        "    (fun e acc =>\n"
        "       match entry_to_vroot e with\n"
        "       | Some vr => vr :: acc\n"
        "       | None => acc\n"
        "       end)\n"
        "    []\n"
        "    lex_entries_generated.\n"
    )

    out_path.write_text("".join(content), encoding="utf-8")
    print(f"Wrote {out_path} with {len(entry_names)} entries total.")

if __name__ == "__main__":
    main()
