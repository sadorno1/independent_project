"""
verifier.py

Coq wf verifier + feedback generator.

Given a Sentence AST:
1. Renders it as a `Compute wf_sentence (...).` Coq term.
2. Writes a temporary .v file that loads the compiled Guaraní spec.
3. Runs coqc, parses the boolean output.
4. If false: runs diagnostic queries to identify which wf predicate failed.
5. Maps failed predicate → natural-language correction message.

Assumes Primitives.vo, NounPhrases.vo, Verb.vo, Sentences.vo are already
compiled and live in COQ_LIB_DIR (set via environment or passed explicitly).
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .types import (
    Sentence, ConjugatedVerb, NP,
    Person, Number, Polarity, Transitivity,
)


# ============================================================
#  Configuration
# ============================================================

# Path to directory containing the compiled .vo files.
# Override with COQ_LIB_DIR environment variable or pass to Verifier().
DEFAULT_COQ_LIB_DIR = Path(os.environ.get("COQ_LIB_DIR", "./coq"))

COQ_PREAMBLE = """\
From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.
Add LoadPath "{lib_dir}" as GuaraniGrammar.
Require Import GuaraniGrammar.Syntax.
Require Import GuaraniGrammar.NounPhrases.
Require Import GuaraniGrammar.Verb.
Require Import GuaraniGrammar.Sentences.
"""


# ============================================================
#  Predicate registry
# ============================================================
# Maps Coq predicate name → (query template, feedback template)
# Query template is the Compute expression used to isolate that predicate.
# Feedback template uses {verb}, {subject}, {expected} placeholders.

PREDICATES: list[dict] = [
    {
        "name": "cv_structure_ok",
        "query": "Compute cv_structure_ok ({cv}).",
        "feedback": (
            "Structural error: Chendal (attributive) verbs must be intransitive, "
            "but '{verb}' is marked transitive."
        ),
    },
    {
        "name": "cv_neg_ok",
        "query": "Compute cv_neg_ok ({cv}).",
        "feedback": (
            "Negation error: polarity is {polarity} but the verb "
            "'{verb}' {'lacks' if polarity == 'Negative' else 'has'} a negation suffix "
            "(nd-...-i / n-...-i). "
            "Expected: nd{verb}i (oral) or n{verb}i (nasal)."
        ),
    },
    {
        "name": "cv_incl_ok",
        "query": "Compute cv_incl_ok ({cv}).",
        "feedback": (
            "Inclusivity error: first-person plural verbs must specify "
            "ñande- (inclusive) or ore- (exclusive). '{verb}' is missing this distinction."
        ),
    },
    {
        "name": "cv_tense_ok",
        "query": "Compute cv_tense_ok ({cv}).",
        "feedback": (
            "Tense error: '{verb}' has more than one tense suffix, or uses "
            "-mo'ã without negative polarity. At most one tense marker is allowed."
        ),
    },
    {
        "name": "cv_neg_count_ok",
        "query": "Compute cv_neg_count_ok ({cv}).",
        "feedback": (
            "Negation suffix error: '{verb}' has more than one negation suffix. "
            "Use exactly one of -i, -ri, -tei, or -'ỹ."
        ),
    },
    {
        "name": "cv_modalizer_ok",
        "query": "Compute cv_modalizer_ok ({cv}).",
        "feedback": (
            "Mood error: imperative modalizers (-ke, -na, -mi, -py) require "
            "Imperative or Optative mood. '{verb}' uses them with Indicative."
        ),
    },
    {
        "name": "cv_mood_neg_ok",
        "query": "Compute cv_mood_neg_ok ({cv}).",
        "feedback": (
            "Prohibitive error: prohibitive mood requires Negative polarity "
            "and uses 'ani' prefix instead of nd-...-i. Check '{verb}'."
        ),
    },
    {
        "name": "cv_class_mood_ok",
        "query": "Compute cv_class_mood_ok ({cv}).",
        "feedback": (
            "Class/mood error: Chendal (attributive) verbs cannot be imperative "
            "or optative. '{verb}' is a Chendal verb."
        ),
    },
    {
        "name": "cv_homophone_ok",
        "query": "Compute cv_homophone_ok ({cv}).",
        "feedback": (
            "Homophone error: '{verb}' combines -pa (interrogative) and -pa "
            "(totalitative), or -mi (plead) and -mi (habitual). These are ambiguous. "
            "Use only one."
        ),
    },
    {
        "name": "cv_evidential_ok",
        "query": "Compute cv_evidential_ok ({cv}).",
        "feedback": (
            "Evidential error: 'kuri' (direct evidence) requires Indicative mood. "
            "'{verb}' uses kuri with a different mood."
        ),
    },
    {
        "name": "ss_agree_ok",
        "query": "Compute ss_agree_ok ({sentence}).",
        "feedback": (
            "Agreement error: subject '{subject}' is {subj_person}/{subj_number} "
            "but verb '{verb}' has a {verb_person}/{verb_number} prefix. "
            "Expected prefix: {expected_prefix}."
        ),
    },
    {
        "name": "ss_transitivity_ok",
        "query": "Compute ss_transitivity_ok ({sentence}).",
        "feedback": (
            "Transitivity error: '{verb}' is {transitivity} but the sentence "
            "{'has' if transitivity == 'Intransitive' else 'is missing'} a direct object."
        ),
    },
    {
        "name": "ss_human_pe_ok",
        "query": "Compute ss_human_pe_ok ({sentence}).",
        "feedback": (
            "Postposition error: human NP '{np}' requires postposition =pe or =me, "
            "not the non-human form."
        ),
    },
    {
        "name": "ss_double_neg_ok",
        "query": "Compute ss_double_neg_ok ({sentence}).",
        "feedback": (
            "Double negation error: if the verb is negative, no argument NP "
            "may also carry a negative pronoun. Remove one negation."
        ),
    },
    {
        "name": "ss_hikuai_ok",
        "query": "Compute ss_hikuai_ok ({sentence}).",
        "feedback": (
            "Hikuái error: hikuái must immediately follow the verb in VSO order "
            "when marking a plural third-person subject."
        ),
    },
    {
        "name": "ss_sent_type_ok",
        "query": "Compute ss_sent_type_ok ({sentence}).",
        "feedback": (
            "Sentence type error: '{verb}' has an interrogative suffix (-pa) "
            "but the sentence type is Declarative, or vice versa."
        ),
    },
]

# Fast lookup
_PRED_BY_NAME = {p["name"]: p for p in PREDICATES}


# ============================================================
#  Verifier
# ============================================================

@dataclass
class VerifierResult:
    wf:               bool
    failed_predicate: Optional[str]   # first failing predicate name, or None
    feedback:         Optional[str]   # natural-language correction message
    coq_term:         str             # the full Compute term that was checked
    raw_output:       str             # raw coqc stdout for debugging


class Verifier:
    def __init__(self, coq_lib_dir: Optional[Path] = None, timeout: int = 30):
        self.lib_dir = Path(coq_lib_dir or DEFAULT_COQ_LIB_DIR).resolve()
        self.timeout = timeout

    def _preamble(self) -> str:
        return COQ_PREAMBLE.format(lib_dir=str(self.lib_dir))

    def _run_coq(self, coq_source: str) -> tuple[bool, str]:
        """
        Write coq_source to a temp file, run coqc, return (success, stdout).
        success = True if coqc exited 0 and produced output.
        """
        with tempfile.NamedTemporaryFile(
            suffix=".v", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write(coq_source)
            tmp = f.name
        try:
            result = subprocess.run(
                ["coqc", tmp],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "coqc timed out"
        except FileNotFoundError:
            return False, "coqc not found in PATH"
        finally:
            Path(tmp).unlink(missing_ok=True)

    def _parse_bool(self, raw: str) -> Optional[bool]:
        """Extract the bool from a `= true : bool` or `= false : bool` line."""
        m = re.search(r"=\s*(true|false)\s*:", raw)
        if m:
            return m.group(1) == "true"
        return None

    def verify(self, sentence: Sentence) -> VerifierResult:
        """
        Check wf_sentence for the given Sentence AST.
        If false, diagnose which predicate failed and generate feedback.
        """
        term = sentence.to_coq_compute()
        source = self._preamble() + "\n" + term + "\n"
        _, raw = self._run_coq(source)
        wf = self._parse_bool(raw)

        if wf is None:
            # coqc error (type error in term, missing .vo, etc.)
            return VerifierResult(
                wf=False,
                failed_predicate="COQ_ERROR",
                feedback=f"Coq type-checking failed. Raw output:\n{raw[:500]}",
                coq_term=term,
                raw_output=raw,
            )

        if wf:
            return VerifierResult(
                wf=True,
                failed_predicate=None,
                feedback=None,
                coq_term=term,
                raw_output=raw,
            )

        # wf = false — diagnose
        failed, feedback = self._diagnose(sentence)
        return VerifierResult(
            wf=False,
            failed_predicate=failed,
            feedback=feedback,
            coq_term=term,
            raw_output=raw,
        )

    def _diagnose(self, sentence: Sentence) -> tuple[Optional[str], Optional[str]]:
        """
        Run each predicate query in order. Return the first that evaluates
        to false, with a natural-language feedback message.
        """
        cv_coq = sentence.verb.to_coq()
        sent_coq = sentence.to_coq()

        for pred in PREDICATES:
            query_template = pred["query"]
            if "{cv}" in query_template:
                query = query_template.format(cv=cv_coq)
            else:
                query = query_template.format(sentence=sent_coq)

            source = self._preamble() + "\n" + query + "\n"
            _, raw = self._run_coq(source)
            result = self._parse_bool(raw)

            if result is False:
                feedback = self._build_feedback(pred["name"], pred["feedback"], sentence)
                return pred["name"], feedback

        return None, "Well-formedness check failed but no specific predicate identified."

    def _build_feedback(
        self, pred_name: str, template: str, sentence: Sentence
    ) -> str:
        """
        Fill feedback template with surface-form details from the AST.
        Keeps it readable for the LLM correction prompt.
        """
        cv = sentence.verb

        # Verb surface (best-effort — render prefix + root for regular verbs)
        from .types import VF_Regular, VF_Irregular
        if isinstance(cv.verb_form, VF_Regular):
            verb_str = cv.verb_form.verb.v_root
            transitivity = cv.verb_form.verb.v_transitivity.value
        else:
            verb_str = cv.verb_form.irreg.value
            transitivity = "unknown"

        subject_str = sentence.subject.surface if sentence.subject else "Ø"
        subj_person = sentence.subject.person.value if sentence.subject else "Third"
        subj_number = sentence.subject.number.value if sentence.subject else "Singular"
        verb_person = cv.person.value
        verb_number = cv.number.value
        polarity = cv.polarity.value
        np_str = sentence.direct_obj.surface if sentence.direct_obj else ""

        # Simple string interpolation — templates use Python f-string-like syntax
        # but are plain strings, so we use .format() with all possible keys.
        try:
            return template.format(
                verb=verb_str,
                subject=subject_str,
                subj_person=subj_person,
                subj_number=subj_number,
                verb_person=verb_person,
                verb_number=verb_number,
                polarity=polarity,
                transitivity=transitivity,
                np=np_str,
                expected_prefix="[see prefix table]",
            )
        except (KeyError, IndexError):
            return f"Well-formedness predicate '{pred_name}' failed for '{verb_str}'."