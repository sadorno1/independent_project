"""
verifier.py

Coq well‑formedness verifier with diagnostic feedback.

Renders a Sentence AST as a `Compute wf_sentence (...).` term, runs coqc,
parses the boolean result, and—if false—runs individual predicate queries
to pinpoint the failure and generate a natural‑language correction message.
Supports multi‑candidate fallback: accepts the first valid parse, otherwise
returns the diagnosis from the candidate that progressed furthest.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .types import Sentence


DEFAULT_COQ_LIB_DIR = Path(os.environ.get("COQ_LIB_DIR", "./rocq"))

COQ_PREAMBLE = """\
From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.
Require Import Syntax.
Require Import noun_phrases.
Require Import verb.
Require Import sentence.
"""

# Predicates are checked in order; the first that returns `false` triggers feedback.
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
            "Negation error: polarity is {polarity} but '{verb}' is "
            "missing or has an extra negation suffix (nd-...-i / n-...-i)."
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
        "name": "ss_agree_ok",
        "query": "Compute ss_agree_ok ({sentence}).",
        "feedback": (
            "Agreement error: subject '{subject}' is {subj_person}/{subj_number} "
            "but verb '{verb}' has a {verb_person}/{verb_number} prefix."
        ),
    },
    {
        "name": "ss_transitivity_ok",
        "query": "Compute ss_transitivity_ok ({sentence}).",
        "feedback": (
            "Transitivity error: '{verb}' is {transitivity} but the sentence "
            "object structure doesn't match."
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

_PRED_BY_NAME = {p["name"]: p for p in PREDICATES}


@dataclass
class VerifierResult:
    wf: bool
    failed_predicate: Optional[str]
    feedback: Optional[str]
    coq_term: str
    raw_output: str


class Verifier:
    def __init__(self, coq_lib_dir: Optional[Path] = None, timeout: int = 30):
        self.lib_dir = Path(coq_lib_dir or DEFAULT_COQ_LIB_DIR).resolve()
        self.timeout = timeout

    def _preamble(self) -> str:
        lib_dir_str = str(self.lib_dir).replace("\\", "/")
        return COQ_PREAMBLE.format(lib_dir=lib_dir_str)

    def _run_coq(self, coq_source: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(
            suffix=".v", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write(coq_source)
            tmp = f.name
        try:
            result = subprocess.run(
                ["coqc", "-R", str(self.lib_dir), "", tmp],
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
        m = re.search(r"=\s*(true|false)\s*:", raw)
        if m:
            return m.group(1) == "true"
        return None

    def verify(self, sentence: Sentence) -> VerifierResult:
        term = sentence.to_coq_compute()
        source = self._preamble() + "\n" + term + "\n"
        _, raw = self._run_coq(source)
        wf = self._parse_bool(raw)

        if wf is None:
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

        _, failed, feedback = self._diagnose(sentence)
        return VerifierResult(
            wf=False,
            failed_predicate=failed,
            feedback=feedback,
            coq_term=term,
            raw_output=raw,
        )

    def verify_candidates(self, candidates: list[Sentence]) -> VerifierResult:
        if not candidates:
            return VerifierResult(
                wf=False,
                failed_predicate=None,
                feedback="No candidate parses to verify.",
                coq_term="",
                raw_output="",
            )

        best_index = -1
        best_result: Optional[VerifierResult] = None

        for sentence in candidates:
            term = sentence.to_coq_compute()
            source = self._preamble() + "\n" + term + "\n"
            _, raw = self._run_coq(source)
            wf = self._parse_bool(raw)

            if wf is True:
                return VerifierResult(
                    wf=True,
                    failed_predicate=None,
                    feedback=None,
                    coq_term=term,
                    raw_output=raw,
                )

            if wf is None:
                if best_result is None:
                    best_result = VerifierResult(
                        wf=False,
                        failed_predicate="COQ_ERROR",
                        feedback=f"Coq type-checking failed. Raw output:\n{raw[:500]}",
                        coq_term=term,
                        raw_output=raw,
                    )
                continue

            idx, failed, feedback = self._diagnose(sentence)
            if idx > best_index:
                best_index = idx
                best_result = VerifierResult(
                    wf=False,
                    failed_predicate=failed,
                    feedback=feedback,
                    coq_term=term,
                    raw_output=raw,
                )

        return best_result

    def _diagnose(self, sentence: Sentence) -> tuple[int, Optional[str], Optional[str]]:
        cv_coq = sentence.verb.to_coq()
        sent_coq = sentence.to_coq()

        for i, pred in enumerate(PREDICATES):
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
                return i, pred["name"], feedback

        return len(PREDICATES), None, None

    def _build_feedback(
        self, pred_name: str, template: str, sentence: Sentence
    ) -> str:
        cv = sentence.verb

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
            )
        except (KeyError, IndexError):
            return f"Well-formedness predicate '{pred_name}' failed for '{verb_str}'."