"""
parse_es_gn.py

Input:  Spanish→Guaraní dictionary as prose text (one or more lines).
        Each entry follows the pattern:
            <spanish_headword>[, <variant>]. <pos>. <Guaraní translations>.
        Verb entries use `tr.` (transitive) or `intr.` (intransitive) as POS.
        Multiple senses are numbered: `2. intr. ...`, `3. tr. ...` etc.

Output: CSV with columns:
            guarani_word, transitivity, spanish_headword, spanish_sense

        One row per (guarani_word, transitivity) pairing. A word that appears
        as both tr. and intr. (under the same or different headwords) gets
        multiple rows. Downstream merge resolves to either Transitive,
        Intransitive, or Both depending on count.

Strategy:
    1. Locate entry starts by regex on the headword pattern.
    2. Slice the text into per-entry chunks.
    3. Within each chunk, find all senses (initial + numbered) and their POS.
    4. For verb senses (tr./intr.), extract the comma-separated Guaraní list.

Robustness notes:
    - Curly apostrophe ’ (U+2019) and straight ' both occur — preserve as-is,
      lowercase but don't strip.
    - Guaraní words are alphabetic + apostrophe + accented/nasalized vowels.
    - Duplicate entries in input (copy-paste artifact) are deduped on output.
"""

import csv
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Spanish headword: starts a line/segment with a lowercase Spanish word
# (may have accented chars), optionally followed by ", <variant>" for
# gendered forms like "completo, ta", then a period, then a POS tag.
#
# We anchor on "<word>[, <word>]. <pos-marker>." where pos-marker is one of
# the dictionary's POS abbreviations.
SPANISH_WORD = r"[a-záéíóúüñ]+"
HEADWORD_PAT = re.compile(
    rf"\b({SPANISH_WORD}(?:,\s+{SPANISH_WORD})?)\.\s+"
    rf"(tr|intr|adj|adv|s|f|m|com|prnl|conj|prep|interj|exp|num|pron|art|dem|amb)"
    rf"(?:\.\s+y\s+(tr|intr|adj|adv|s|f|m|com))?"
    rf"\."
)

# All POS tags that can head a sense. Used in NUMBERED_SENSE_PAT so any of
# them properly closes the previous sense. Missing tags here caused leakage
# (e.g. `tr. X. 2. prnl. Y` was reading Y as still part of the tr. sense).
ALL_POS_TAGS = (
    "tr|intr|adj|adv|s|f|m|com|prnl|conj|prep|interj|exp|num|pron|art|dem|"
    "amb|fig|neol|arc|aux|def|imp|irr|sub|rel|voc|exclam|int|ind|pers|pos|"
    "sing|pl|neg|p\\. n|p\\. v|p\\.n|p\\.v|suf|pref"
)

# Sense within an entry. We use HEADWORD_PAT's match position as anchor for
# the first sense, then scan for numbered senses inside the entry.
NUMBERED_SENSE_PAT = re.compile(rf"\b(\d+)\.\s+({ALL_POS_TAGS})\.\s+")

# A Guaraní word: letters (incl. accented & nasalized), apostrophes (both),
# tilde, hyphen. Allows multi-character sequences including the special
# Guaraní glyphs like ã ẽ ĩ õ ũ ỹ.
GUARANI_WORD = r"[A-Za-zÀ-ÿñÑãẽĩõũỹÃẼĨÕŨỸ'’\-]+"

# After a verb POS marker, the translations section runs until the next
# sense marker or the next entry boundary. We extract all Guaraní-word
# tokens from that section (comma-separated, optionally space-separated).
GUARANI_LIST_PAT = re.compile(GUARANI_WORD)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

VERB_TAGS = {"tr", "intr"}


def normalize_guarani(word: str) -> str:
    """Lowercase + normalize curly apostrophe to straight (matches Verb.v).
    Preserves diacritics (ã, ẽ, ĩ, õ, ũ, ỹ, é, á, etc.)."""
    w = word.lower().strip("-,.;:")
    w = w.replace("\u2019", "'")  # ’ → '
    return w


def find_entries(text: str) -> list[tuple[int, int, str, str]]:
    """
    Returns list of (start_pos, end_pos, headword, first_pos_tag).
    Entries are slices of `text` bounded by consecutive headword matches.
    """
    matches = list(HEADWORD_PAT.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        headword = m.group(1)
        pos_tag = m.group(2)
        entries.append((start, end, headword, pos_tag))
    return entries


def parse_senses(entry_text: str, first_pos_tag: str) -> list[tuple[str, str]]:
    """
    Given the full entry text and the POS of its first sense, return a list
    of (pos_tag, sense_body) tuples. sense_body is the text between this
    sense's POS marker and the next sense marker (or end of entry).
    """
    senses = []

    # First sense: find where the first POS marker ends (after "tr." or "intr."
    # etc.) and treat everything up to the first numbered sense as body.
    first_marker = re.search(rf"\b{first_pos_tag}\.\s+", entry_text)
    if not first_marker:
        return senses
    body_start = first_marker.end()

    # Find all numbered senses
    numbered = list(NUMBERED_SENSE_PAT.finditer(entry_text, body_start))

    if not numbered:
        senses.append((first_pos_tag, entry_text[body_start:]))
    else:
        # First sense runs from body_start to first numbered sense
        senses.append((first_pos_tag, entry_text[body_start:numbered[0].start()]))
        for j, nm in enumerate(numbered):
            sense_pos = nm.group(2)
            sense_body_start = nm.end()
            sense_body_end = (
                numbered[j + 1].start() if j + 1 < len(numbered) else len(entry_text)
            )
            senses.append((sense_pos, entry_text[sense_body_start:sense_body_end]))

    return senses


def extract_guarani_words(sense_body: str) -> list[str]:
    """
    From a sense body (text after a `tr.`/`intr.` marker), pull out the
    Guaraní translation words. The dictionary convention is:
        - comma-separated = alternative translations (keep all)
        - space-separated = multi-word phrase (one translation unit)

    We respect that convention: split on commas first, then for each
    comma-separated chunk, only keep it if it's a single token. Multi-token
    chunks are phrases like "rahauka tekotevẽva" — we can't decide which
    token is the verb, so we drop them. They're already covered when the
    head verb appears elsewhere as a single-word translation.

    Cut at the first ". " (period + whitespace) since trailing material is
    typically an example sentence or note.
    """
    # Cut at first ". " (sentence-ending period)
    end = sense_body.find(". ")
    if end != -1:
        sense_body = sense_body[:end]

    chunks = [c.strip() for c in sense_body.split(",")]
    words = []
    for chunk in chunks:
        if not chunk:
            continue
        # Split chunk on whitespace
        toks = chunk.split()
        if len(toks) != 1:
            # Multi-word translation: skip (can't pick the verb)
            continue
        tok = toks[0]
        if not re.search(r"[A-Za-zÀ-ÿñÑãẽĩõũỹÃẼĨÕŨỸ]", tok):
            continue
        words.append(normalize_guarani(tok))
    return words


def parse_dictionary(text: str) -> list[dict]:
    """
    Parse the full text and return a list of dicts:
        { guarani_word, transitivity, spanish_headword, spanish_sense }
    Deduped across the (guarani_word, transitivity, spanish_headword) key.
    """
    seen = set()
    rows = []

    for start, end, headword, first_pos in find_entries(text):
        entry = text[start:end]
        for sense_pos, sense_body in parse_senses(entry, first_pos):
            if sense_pos not in VERB_TAGS:
                continue
            transitivity = "Transitive" if sense_pos == "tr" else "Intransitive"
            words = extract_guarani_words(sense_body)
            # The sense gloss is the trimmed sense_body — useful as the
            # Spanish-side definition for downstream feedback.
            gloss = sense_body.strip().rstrip(".").strip()
            for w in words:
                key = (w, transitivity, headword)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "guarani_word": w,
                    "transitivity": transitivity,
                    "spanish_headword": headword,
                    "spanish_sense": gloss,
                })
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FIELDNAMES = ["guarani_word", "transitivity", "spanish_headword", "spanish_sense"]


def main():
    if len(sys.argv) < 3:
        print("usage: parse_es_gn.py INPUT.txt OUTPUT.csv", file=sys.stderr)
        sys.exit(2)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    text = in_path.read_text(encoding="utf-8")
    rows = parse_dictionary(text)

    with out_path.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    # Stats
    n_total = len(rows)
    n_words = len({r["guarani_word"] for r in rows})
    n_tr = sum(1 for r in rows if r["transitivity"] == "Transitive")
    n_intr = sum(1 for r in rows if r["transitivity"] == "Intransitive")

    # Words appearing as both
    by_word = {}
    for r in rows:
        by_word.setdefault(r["guarani_word"], set()).add(r["transitivity"])
    both = sorted(w for w, ts in by_word.items() if len(ts) > 1)

    print(f"rows out:         {n_total}")
    print(f"unique words:     {n_words}")
    print(f"transitive senses: {n_tr}")
    print(f"intransitive senses: {n_intr}")
    print(f"words tagged as BOTH tr. and intr.: {len(both)}")

    # Diagnostic: dump full BOTH list with headword sources.
    # Helps distinguish genuine ambitransitives from parser bugs.
    if both:
        dump_path = out_path.with_suffix(".both.txt")
        # Build word → {transitivity → [headwords]} map
        word_sources: dict[str, dict[str, list[str]]] = {}
        for r in rows:
            w = r["guarani_word"]
            if w not in by_word or len(by_word[w]) < 2:
                continue
            word_sources.setdefault(w, {}).setdefault(
                r["transitivity"], []
            ).append(r["spanish_headword"])

        with dump_path.open("w", encoding="utf-8") as f:
            f.write(f"# {len(both)} words tagged as BOTH tr. and intr.\n")
            f.write(f"# Format: word | tr: <headwords> | intr: <headwords>\n\n")
            for w in sorted(word_sources):
                tr_heads = ", ".join(sorted(set(word_sources[w].get("Transitive", []))))
                intr_heads = ", ".join(sorted(set(word_sources[w].get("Intransitive", []))))
                f.write(f"{w}\n")
                f.write(f"  tr.:   {tr_heads}\n")
                f.write(f"  intr.: {intr_heads}\n\n")
        print(f"  full list with sources written to: {dump_path}")


if __name__ == "__main__":
    main()