"""
extract_word_types.py

Extracts word entries and their associated grammatical tags from a two-column 
dictionary PDF, exporting the results to a pipe-separated types CSV.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

import pdfplumber

# ===========================================================================
# Configuration & Tag definitions
# ===========================================================================

PDF_PATH = "references/dictionary_with_types.pdf"
START_PAGE = 1
END_PAGE = None
OUT_CSV = "word_types.csv"

MUST_HAVE = ["aipo", "achegety", "ãga", "aguyje"]

KNOWN_TAGS = {
    "s.", "adj.", "adv.", "conj.", "pron.", "interj.", "voc.", "exp.", "h.",
    "neol.", "p. n.", "t.", "bif.", "v.", "v. pr.", "v. atr.", "v. air.",
    "suf. a. n.", "suf. a. v.", "pron. dem.", "pron. ind.", "pron. pos.",
    "adj. ind.", "adj. ind. y pron. ind.", "adv. de neg.", "adv. de tiempo",
}

def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def norm_tag(s: str) -> str:
    return norm_space(s).lower()

# Longest matching multi-word sequences take priority during parsing
COMBINED_TAGS = sorted([t for t in KNOWN_TAGS if " " in t], key=len, reverse=True)
SIMPLE_TAGS = sorted([t for t in KNOWN_TAGS if " " not in t], key=len, reverse=True)
KNOWN_TAGS_NORM = {norm_tag(t): t for t in KNOWN_TAGS}

# ===========================================================================
# Normalization Helpers
# ===========================================================================

APOSTROPHE_VARIANTS = ["’", "ʼ", "‘", "´", "`"]

def normalize_apostrophes(s: str) -> str:
    for a in APOSTROPHE_VARIANTS:
        s = s.replace(a, "'")
    return s

def normalize_text_noise(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = normalize_apostrophes(s)
    s = re.sub(r"(\d+)\.\s*([A-Za-zÁÉÍÓÚÜÑñ])", r"\1. \2", s)
    s = re.sub(r"^\s*\d+\s*$", "", s)
    return norm_space(s)

# ===========================================================================
# Two-Column Layout Extractor
# ===========================================================================

def _group_words_into_lines(words: List[dict], y_tol: float = 2.2) -> List[List[dict]]:
    words_sorted = sorted(words, key=lambda w: (round(w["top"], 1), w["x0"]))
    lines: List[List[dict]] = []
    cur: List[dict] = []
    cur_y = None

    for w in words_sorted:
        y = w["top"]
        if cur_y is None or abs(y - cur_y) <= y_tol:
            cur.append(w)
            cur_y = y if cur_y is None else (cur_y + y) / 2
        else:
            lines.append(sorted(cur, key=lambda z: z["x0"]))
            cur = [w]
            cur_y = y
    if cur:
        lines.append(sorted(cur, key=lambda z: z["x0"]))
    return lines

def _line_to_text(words_line: List[dict]) -> str:
    txt = " ".join(w["text"] for w in words_line)
    for target in [",", ".", ";", ":", ")"]:
        txt = txt.replace(f" {target}", target)
    txt = txt.replace("( ", "(")
    return normalize_text_noise(txt)

def extract_lines_from_pdf_two_column(pdf_path: str, start_page: int = 1, end_page: int | None = None) -> List[str]:
    all_lines: List[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        sp = max(1, start_page)
        ep = total if end_page is None else min(end_page, total)

        for p in range(sp - 1, ep):
            page = pdf.pages[p]
            words = page.extract_words(
                x_tolerance=2, y_tolerance=2, keep_blank_chars=False, use_text_flow=False
            ) or []

            if not words:
                continue

            mid_x = page.width / 2
            left_words = [w for w in words if (w["x0"] + w["x1"]) / 2 <= mid_x]
            right_words = [w for w in words if (w["x0"] + w["x1"]) / 2 > mid_x]

            for col_words in (left_words, right_words):
                lines = _group_words_into_lines(col_words, y_tol=2.2)
                for ln in lines:
                    text = _line_to_text(ln)
                    if text:
                        all_lines.append(text)

    # Reconstruct soft hyphenations spanning line-breaks
    merged: List[str] = []
    i = 0
    while i < len(all_lines):
        cur = all_lines[i]
        if cur.endswith("-") and i + 1 < len(all_lines):
            merged.append(cur[:-1] + all_lines[i + 1].lstrip())
            i += 2
        else:
            merged.append(cur)
            i += 1

    return merged

# ===========================================================================
# Parsing Engine
# ===========================================================================

WORD_CHARS = r"A-Za-zÁÉÍÓÚÜÑñãõÃÕáéíóúüẽĩũẼĨŨỹỸ'\-"
HEADWORD_LINE_RE = re.compile(rf"^\s*(?P<word>[{WORD_CHARS}]+)\.\s*(?P<rest>.*)$", re.UNICODE)

def split_entries(lines: List[str]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    cur_word = None
    cur_parts: List[str] = []

    for line in lines:
        line = normalize_text_noise(line)
        if not line:
            continue

        m = HEADWORD_LINE_RE.match(line)
        if m:
            if cur_word is not None:
                entries.append({"word": cur_word, "body": norm_space(" ".join(cur_parts))})
            cur_word = normalize_text_noise(m.group("word"))
            rest = m.group("rest").strip()
            cur_parts = [rest] if rest else []
        else:
            if cur_word is not None:
                cur_parts.append(line)

    if cur_word is not None:
        entries.append({"word": cur_word, "body": norm_space(" ".join(cur_parts))})

    return entries


def strip_leading_separators(s: str) -> str:
    return re.sub(r"^[,;]+\s*", "", s.lstrip())

def consume_combined_prefix_tags(s: str) -> Tuple[List[str], str]:
    out: List[str] = []
    s = strip_leading_separators(normalize_text_noise(s))

    changed = True
    while changed:
        changed = False
        low = s.lower()
        for ct in COMBINED_TAGS:
            ctl = ct.lower()
            if low.startswith(ctl):
                after = s[len(ct):]
                if after == "" or after[0].isspace() or after.startswith(",") or after.startswith(";"):
                    out.append(ct)
                    s = strip_leading_separators(after)
                    changed = True
                    break
    return out, s

def consume_simple_prefix_tags(s: str, max_tags: int = 6) -> Tuple[List[str], str]:
    out: List[str] = []
    s = strip_leading_separators(normalize_text_noise(s))
    count = 0

    while count < max_tags:
        if not re.match(r"^([A-Za-zÁÉÍÓÚÜÑñ]+(?:\.)?)", s):
            break

        matched = None
        for tag in SIMPLE_TAGS:
            if s.lower().startswith(tag.lower()):
                matched = tag
                break

        if matched is None:
            break

        out.append(matched)
        s = strip_leading_separators(s[len(matched):])
        count += 1

    return out, s

def extract_tags_from_chunk(chunk: str) -> List[str]:
    s = normalize_text_noise(chunk)
    ctags, rem = consume_combined_prefix_tags(s)
    stags, _ = consume_simple_prefix_tags(rem, max_tags=6)

    seen = set()
    out = []
    for t in (ctags + stags):
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out

def extract_types_from_entry_body(body: str) -> List[str]:
    types: List[str] = []
    body = normalize_text_noise(body)

    # Global headword level tags
    for t in extract_tags_from_chunk(body):
        if t not in types:
            types.append(t)

    # Internal sub-sense tags ("1. ...", "2. ...")
    senses = re.split(r"(?=\b\d+\.\s*)", body)
    for s in senses:
        s = s.strip()
        if not s:
            continue
        s = re.sub(r"^\d+\.\s*", "", s)
        for t in extract_tags_from_chunk(s):
            if t not in types:
                types.append(t)

    return types

# ===========================================================================
# I/O Execution Block
# ===========================================================================

def save_csv(data: List[Dict[str, List[str]]], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["word", "types"])
        for r in data:
            w.writerow([r["word"], "|".join(r["types"])])

def debug_check(data: List[Dict[str, List[str]]], must_have: List[str]) -> None:
    idx = {r["word"].lower(): r["types"] for r in data}
    print("\n=== DEBUG CHECK ===")
    for w in must_have:
        k = normalize_text_noise(w).lower()
        print(f"OK: {w} -> {idx[k]}" if k in idx else f"MISSING: {w}")
    print("===================\n")

if __name__ == "__main__":
    lines = extract_lines_from_pdf_two_column(PDF_PATH, start_page=START_PAGE, end_page=END_PAGE)
    entries = split_entries(lines)

    parsed: List[Dict[str, List[str]]] = []
    for e in entries:
        types = extract_types_from_entry_body(e["body"])
        if types:
            parsed.append({"word": e["word"], "types": types})

    save_csv(parsed, OUT_CSV)
    print(f"Parsed entries: {len(parsed)}\nWrote {OUT_CSV}")
    debug_check(parsed, MUST_HAVE)