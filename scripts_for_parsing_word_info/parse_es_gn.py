"""
parse_es_gn.py

Parses a prose Spanish→Guaraní dictionary file into a structured CSV:
[guarani_word, transitivity, spanish_headword, spanish_sense]
"""

import csv
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

SPANISH_WORD = r"[a-záéíóúüñ]+"
HEADWORD_PAT = re.compile(
    rf"\b({SPANISH_WORD}(?:,\s+{SPANISH_WORD})?)\.\s+"
    rf"(tr|intr|adj|adv|s|f|m|com|prnl|conj|prep|interj|exp|num|pron|art|dem|amb)"
    rf"(?:\.\s+y\s+(tr|intr|adj|adv|s|f|m|com))?"
    rf"\."
)

ALL_POS_TAGS = (
    "tr|intr|adj|adv|s|f|m|com|prnl|conj|prep|interj|exp|num|pron|art|dem|"
    "amb|fig|neol|arc|aux|def|imp|irr|sub|rel|voc|exclam|int|ind|pers|pos|"
    "sing|pl|neg|p\\. n|p\\. v|p\\.n|p\\.v|suf|pref"
)

NUMBERED_SENSE_PAT = re.compile(rf"\b(\d+)\.\s+({ALL_POS_TAGS})\.\s+")
GUARANI_WORD = r"[A-Za-zÀ-ÿñÑãẽĩõũỹÃẼĨÕŨỸ'’\-]+"
GUARANI_LIST_PAT = re.compile(GUARANI_WORD)

VERB_TAGS = {"tr", "intr"}
FIELDNAMES = ["guarani_word", "transitivity", "spanish_headword", "spanish_sense"]

# ---------------------------------------------------------------------------
# Core Parser Functions
# ---------------------------------------------------------------------------

def normalize_guarani(word: str) -> str:
    """Lowercase word and normalize curly apostrophes to straight standard."""
    w = word.lower().strip("-,.;:")
    return w.replace("\u2019", "'")


def find_entries(text: str) -> list[tuple[int, int, str, str]]:
    """Identifies individual dictionary entry blocks bounded by headword pattern matches."""
    matches = list(HEADWORD_PAT.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        entries.append((start, end, m.group(1), m.group(2)))
    return entries


def parse_senses(entry_text: str, first_pos_tag: str) -> list[tuple[str, str]]:
    """Slices an entry chunk into sub-senses by parsing its inner POS tags."""
    senses = []
    first_marker = re.search(rf"\b{first_pos_tag}\.\s+", entry_text)
    if not first_marker:
        return senses
        
    body_start = first_marker.end()
    numbered = list(NUMBERED_SENSE_PAT.finditer(entry_text, body_start))

    if not numbered:
        senses.append((first_pos_tag, entry_text[body_start:]))
    else:
        senses.append((first_pos_tag, entry_text[body_start:numbered[0].start()]))
        for j, nm in enumerate(numbered):
            sense_body_end = numbered[j + 1].start() if j + 1 < len(numbered) else len(entry_text)
            senses.append((nm.group(2), entry_text[nm.end():sense_body_end]))

    return senses


def extract_guarani_words(sense_body: str) -> list[str]:
    """Extracts alternative comma-separated Guaraní tokens, dropping multi-word phrases."""
    end = sense_body.find(". ")
    if end != -1:
        sense_body = sense_body[:end]

    chunks = [c.strip() for c in sense_body.split(",")]
    words = []
    for chunk in chunks:
        if not chunk:
            continue
        toks = chunk.split()
        if len(toks) != 1:
            continue
        tok = toks[0]
        if re.search(r"[A-Za-zÀ-ÿñÑãẽĩõũỹÃẼĨÕŨỸ]", tok):
            words.append(normalize_guarani(tok))
    return words


def parse_dictionary(text: str) -> list[dict]:
    """Transforms raw dictionary text into structured, unique verb rows."""
    seen = set()
    rows = []

    for start, end, headword, first_pos in find_entries(text):
        entry = text[start:end]
        for sense_pos, sense_body in parse_senses(entry, first_pos):
            if sense_pos not in VERB_TAGS:
                continue
                
            transitivity = "Transitive" if sense_pos == "tr" else "Intransitive"
            gloss = sense_body.strip().rstrip(".").strip()
            
            for w in extract_guarani_words(sense_body):
                key = (w, transitivity, headword)
                if key not in seen:
                    seen.add(key)
                    rows.append({
                        "guarani_word": w,
                        "transitivity": transitivity,
                        "spanish_headword": headword,
                        "spanish_sense": gloss,
                    })
    return rows


# ---------------------------------------------------------------------------
# Execution Block & Metrics
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("usage: parse_es_gn.py INPUT.txt OUTPUT.csv", file=sys.stderr)
        sys.exit(2)
        
    out_path = Path(sys.argv[2])
    rows = parse_dictionary(Path(sys.argv[1]).read_text(encoding="utf-8"))

    with out_path.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    # Calculate statistics
    by_word = {}
    for r in rows:
        by_word.setdefault(r["guarani_word"], set()).add(r["transitivity"])
    both = sorted(w for w, ts in by_word.items() if len(ts) > 1)

    print(f"rows out:           {len(rows)}")
    print(f"unique words:       {len(by_word)}")
    print(f"transitive senses:  {sum(1 for r in rows if r['transitivity'] == 'Transitive')}")
    print(f"intransitive senses:{sum(1 for r in rows if r['transitivity'] == 'Intransitive')}")
    print(f"words tagged BOTH:  {len(both)}")

    # Write diagnostic ambitransitive file
    if both:
        dump_path = out_path.with_suffix(".both.txt")
        word_sources: dict[str, dict[str, list[str]]] = {}
        for r in rows:
            w = r["guarani_word"]
            if w in word_sources or len(by_word[w]) >= 2:
                word_sources.setdefault(w, {}).setdefault(r["transitivity"], []).append(r["spanish_headword"])

        with dump_path.open("w", encoding="utf-8") as f:
            f.write(f"# {len(both)} words tagged as BOTH tr. and intr.\n")
            f.write(f"# Format: word | tr: <headwords> | intr: <headwords>\n\n")
            for w in sorted(word_sources):
                tr_heads = ", ".join(sorted(set(word_sources[w].get("Transitive", []))))
                intr_heads = ", ".join(sorted(set(word_sources[w].get("Intransitive", []))))
                f.write(f"{w}\n   tr.:   {tr_heads}\n   intr.: {intr_heads}\n\n")
        print(f"  full list with sources written to: {dump_path}")


if __name__ == "__main__":
    main()