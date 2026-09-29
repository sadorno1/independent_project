"""
coq_context.py

Extracts the definitional content (inductive types, definitions, records,
notations) from the project's Coq grammar files, for injection into an LLM
prompt as passive grammar context (the "coq" context mode). This is separate
from and additive to the existing verifier feedback loop.

Note on filenames: the on-disk files are Syntax.v, Numbers.v, verb.v,
noun_phrases.v, sentence.v. Their header comments record the names used
elsewhere in project docs — Syntax.v was originally Primitives.v,
noun_phrases.v is NounPhrases.v, sentence.v is Sentences.v — so this module
reads the current on-disk names in true dependency order (verb.v is a real
dependency of noun_phrases.v and sentence.v, per their own Require Import
lines; see verifier.py's COQ_PREAMBLE for the equivalent Require list).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

ContextMode = Literal["none", "coq"]

# Dependency order: each file only requires files earlier in this list.
COQ_FILES = ["Syntax.v", "Numbers.v", "verb.v", "noun_phrases.v", "sentence.v"]

_INCLUDE_PREFIXES = (
    "Inductive", "Definition", "Fixpoint", "|", "End", "Module", "Record", "Notation",
)

_EXCLUDE_SUBSTRINGS = (
    "Proof.", "Qed.", "Defined.", "intros", "apply", "exact", "simpl",
    "rewrite", "induction", "destruct", "auto", "trivial", "reflexivity", "(*",
)


def _extract_definitions(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(_INCLUDE_PREFIXES):
            continue
        if any(tok in stripped for tok in _EXCLUDE_SUBSTRINGS):
            continue
        kept.append(line)
    return "\n".join(kept)


def load_coq_context(coq_dir: str) -> str:
    """Reads COQ_FILES from coq_dir in dependency order and extracts their
    definitional content, skipping proof scripts and comments. Returns the
    concatenated result, each file's section prefixed with a header comment
    naming the file it came from."""
    base = Path(coq_dir)
    sections: list[str] = []
    for filename in COQ_FILES:
        text = (base / filename).read_text(encoding="utf-8")
        body = _extract_definitions(text)
        sections.append(f"(* === {filename} === *)\n{body}")
    return "\n\n".join(sections)


if __name__ == "__main__":
    import sys

    coq_dir = sys.argv[1] if len(sys.argv) > 1 else "rocq"
    print(load_coq_context(coq_dir))
