"""
merge.py

Merges es_gn_transitivity.csv (output of parse_es_gn.py) into
enriched.csv (output of enrich_lexicon.py).

For each verb row in enriched.csv:
  - If transitivity is already filled → leave it (Guaraní side is authoritative).
  - If blank → look up the word in the transitivity index.
    - Exactly one value (Transitive or Intransitive) → fill it in.
    - Both tr. and intr. found → set to "Ambitransitive", flag for review.
    - Not found → leave blank.
  - Also fills spanish_gloss column from the first matching Spanish headword.

Usage:
    python merge.py enriched.csv es_gn_transitivity.csv merged.csv
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict


def load_transitivity_index(
    transitivity_csv: Path,
) -> dict[str, dict]:
    """
    Build index: guarani_word → {
        "transitivities": set of "Transitive" / "Intransitive",
        "glosses": list of spanish_headword strings,
    }
    """
    index: dict[str, dict] = defaultdict(lambda: {"transitivities": set(), "glosses": []})

    with transitivity_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row["guarani_word"].strip().lower()
            tr   = row["transitivity"].strip()
            gloss = row["spanish_headword"].strip()
            if word and tr:
                index[word]["transitivities"].add(tr)
            if gloss and gloss not in index[word]["glosses"]:
                index[word]["glosses"].append(gloss)

    return dict(index)


def merge(
    enriched_csv: Path,
    transitivity_csv: Path,
    output_csv: Path,
) -> dict:
    index = load_transitivity_index(transitivity_csv)

    stats = {
        "rows_total":        0,
        "verb_rows":         0,
        "filled_from_merge": 0,
        "ambitransitive":    0,
        "still_blank":       0,
        "already_filled":    0,
        "gloss_filled":      0,
    }

    # Read all rows first to get fieldnames
    with enriched_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        original_fields = reader.fieldnames or []
        rows = list(reader)

    # Add new columns if not present
    new_fields = list(original_fields)
    if "spanish_gloss" not in new_fields:
        new_fields.append("spanish_gloss")

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fields)
        writer.writeheader()

        for row in rows:
            stats["rows_total"] += 1
            row.setdefault("spanish_gloss", "")

            if row.get("primary_pos") != "verb":
                writer.writerow(row)
                continue

            stats["verb_rows"] += 1
            word = row["word"].strip().lower()
            entry = index.get(word)

            # Fill transitivity
            current_tr = row.get("transitivity", "").strip()
            if current_tr:
                stats["already_filled"] += 1
            elif entry:
                trs = entry["transitivities"]
                if len(trs) == 1:
                    row["transitivity"] = next(iter(trs))
                    stats["filled_from_merge"] += 1
                elif len(trs) > 1:
                    row["transitivity"] = "Ambitransitive"
                    # Add flag
                    flags = row.get("flags", "")
                    flag_list = [f for f in flags.split("|") if f]
                    if "CHECK_AMBITRANSITIVE" not in flag_list:
                        flag_list.append("CHECK_AMBITRANSITIVE")
                    row["flags"] = "|".join(flag_list)
                    stats["ambitransitive"] += 1
                else:
                    stats["still_blank"] += 1
            else:
                stats["still_blank"] += 1

            # Fill Spanish gloss (first headword only)
            if not row.get("spanish_gloss") and entry and entry["glosses"]:
                row["spanish_gloss"] = entry["glosses"][0]
                stats["gloss_filled"] += 1

            writer.writerow(row)

    return stats


def main():
    if len(sys.argv) < 4:
        print(
            "usage: merge.py enriched.csv es_gn_transitivity.csv output.csv",
            file=sys.stderr,
        )
        sys.exit(2)

    enriched     = Path(sys.argv[1])
    transitivity = Path(sys.argv[2])
    output       = Path(sys.argv[3])

    stats = merge(enriched, transitivity, output)

    print(f"rows total:          {stats['rows_total']}")
    print(f"verb rows:           {stats['verb_rows']}")
    print(f"  already filled:    {stats['already_filled']}")
    print(f"  filled from merge: {stats['filled_from_merge']}")
    print(f"  ambitransitive:    {stats['ambitransitive']}")
    print(f"  still blank:       {stats['still_blank']}")
    print(f"gloss filled:        {stats['gloss_filled']}")
    print(f"output:              {output}")


if __name__ == "__main__":
    main()