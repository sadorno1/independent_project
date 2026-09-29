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

from .types import Sentence, AdverbialSentence, CoordinatedSentence, NonverbalSentence


DEFAULT_COQ_LIB_DIR = Path(os.environ.get("COQ_LIB_DIR", "./rocq"))

COQ_PREAMBLE = """\
From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.
Require Import Syntax.
Require Import Numbers.
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
        "name": "no_dup_suffixes",
        "query": "Compute no_dup_suffixes (cv_suffixes ({cv})).",
        "feedback": (
            "Suffix error: '{verb}' carries the same verbal suffix more than "
            "once (e.g. a doubled negation -i)."
        ),
    },
    {
        "name": "suffixes_ordered",
        "query": "Compute suffixes_ordered (cv_suffixes ({cv})).",
        "feedback": (
            "Suffix order error: the suffixes on '{verb}' are not in the "
            "required slot order."
        ),
    },
    {
        "name": "cv_evidential_ok",
        "query": "Compute cv_evidential_ok ({cv}).",
        "feedback": (
            "Evidential error: '{verb}' carries the evidential marker "
            "'{evidential}' with {mood} mood. Kuri (direct evidence / recent "
            "past) requires Indicative mood."
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
        "name": "ss_neg_concord_ok",
        "query": "Compute ss_neg_concord_ok ({sentence}).",
        "feedback": (
            "Double negation error: if the verb is negative, no argument NP "
            "may also carry a negative pronoun. Remove one negation."
        ),
    },
    {
        "name": "ss_hierarchy_ok",
        "query": "Compute ss_hierarchy_ok ({sentence}).",
        "feedback": (
            "Person hierarchy error: when a 1st-person argument acts on a 2nd-person "
            "argument (or vice versa), a portmanteau prefix is required — ro- (1sg→2) "
            "or jo- (2→1sg). '{verb}' uses separate agreement prefixes instead."
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
        "name": "ss_type_ok",
        "query": "Compute ss_type_ok ({sentence}).",
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
    sentence: Optional["Sentence | AdverbialSentence | CoordinatedSentence | NonverbalSentence"] = None


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

    def verify(self, sentence: Sentence | AdverbialSentence | CoordinatedSentence | NonverbalSentence) -> VerifierResult:
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
                sentence=sentence,
            )

        if wf:
            return VerifierResult(
                wf=True,
                failed_predicate=None,
                feedback=None,
                coq_term=term,
                raw_output=raw,
                sentence=sentence,
            )

        _, failed, feedback = self._diagnose(sentence)
        return VerifierResult(
            wf=False,
            failed_predicate=failed,
            feedback=feedback,
            coq_term=term,
            raw_output=raw,
            sentence=sentence,
        )

    def verify_candidates(self, candidates: list[Sentence | AdverbialSentence | CoordinatedSentence | NonverbalSentence]) -> VerifierResult:
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
                    sentence=sentence,
                )

            if wf is None:
                if best_result is None:
                    best_result = VerifierResult(
                        wf=False,
                        failed_predicate="COQ_ERROR",
                        feedback=f"Coq type-checking failed. Raw output:\n{raw[:500]}",
                        coq_term=term,
                        raw_output=raw,
                        sentence=sentence,
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
                    sentence=sentence,
                )

        return best_result

    def _diagnose(self, candidate) -> tuple[int, Optional[str], Optional[str]]:
        if isinstance(candidate, AdverbialSentence):
            return self._diagnose_adverbial(candidate)
        if isinstance(candidate, CoordinatedSentence):
            return self._diagnose_coordinated(candidate)
        if isinstance(candidate, NonverbalSentence):
            return self._diagnose_nonverbal(candidate)
        return self._diagnose_simple(candidate)

    def _diagnose_adverbial(self, adv: AdverbialSentence) -> tuple[int, Optional[str], Optional[str]]:
        """CS_Adverbial has no simple_sentence predicate chain of its own —
        wf_complex is just wf_sentence(main) && wf_sentence(subord) &&
        wf_adv_clause(ac). The morpheme/type pairing is only ever built from
        ADV_SUBORDINATOR_FORM_INDEX (types.py), so wf_adv_clause is always
        true by construction; a failure must be in one of the two clauses."""
        idx, failed, feedback = self._diagnose_simple(adv.main)
        if failed is not None:
            return idx, failed, f"In the main clause: {feedback}"
        idx, failed, feedback = self._diagnose_simple(adv.subord)
        if failed is not None:
            return idx, failed, f"In the subordinate clause ('{adv.ac.ac_subord}'): {feedback}"
        return len(PREDICATES), None, None

    def _diagnose_coordinated(self, coord: CoordinatedSentence) -> tuple[int, Optional[str], Optional[str]]:
        """CS_Coordinated is just wf_sentence(s1) && wf_sentence(s2) — no
        third condition the way CS_Adverbial has wf_adv_clause."""
        idx, failed, feedback = self._diagnose_simple(coord.s1)
        if failed is not None:
            return idx, failed, f"In the first clause: {feedback}"
        idx, failed, feedback = self._diagnose_simple(coord.s2)
        if failed is not None:
            return idx, failed, f"In the second clause: {feedback}"
        return len(PREDICATES), None, None

    def _diagnose_nonverbal(self, nvs: NonverbalSentence) -> tuple[int, Optional[str], Optional[str]]:
        """wf_nonverbal has no factored predicate chain the way wf_sentence
        does — it's a single wf_np / wf_np && wf_np boolean, so there's no
        finer-grained breakdown to offer. Every NP shape the analyzer builds
        is individually wf on its own, so a failure here is almost always
        an embedded NP_Rel/NP_Comp clause whose verb doesn't satisfy its own
        conditions."""
        return (
            0, "wf_nonverbal",
            "Non-verbal sentence error: one of the noun phrases in this "
            "equative/predicative/existential/possessive sentence is not "
            "well-formed (most likely an embedded relative or complement "
            "clause whose verb doesn't satisfy its own well-formedness "
            "conditions).",
        )

    def _predicate_trace(
        self, sentence: Sentence, stop_at_first_false: bool = True
    ) -> list[tuple[str, Optional[bool]]]:
        """Runs each predicate in PREDICATES in order against `sentence`,
        recording pass (True) / fail (False) / coqc error (None). By default
        stops at the first failure (mirrors what actually determines
        well-formedness); pass stop_at_first_false=False for a full trace
        used by verbose diagnostics."""
        cv_coq = sentence.verb.to_coq()
        sent_coq = sentence.to_coq()
        trace: list[tuple[str, Optional[bool]]] = []

        for pred in PREDICATES:
            query_template = pred["query"]
            if "{cv}" in query_template:
                query = query_template.format(cv=cv_coq)
            else:
                query = query_template.format(sentence=sent_coq)

            source = self._preamble() + "\n" + query + "\n"
            _, raw = self._run_coq(source)
            result = self._parse_bool(raw)
            trace.append((pred["name"], result))

            if stop_at_first_false and result is False:
                break

        return trace

    def predicate_trace(self, sentence: Sentence) -> list[tuple[str, Optional[bool]]]:
        """Public, full (non-short-circuiting) predicate-by-predicate trace
        for a single simple sentence, for verbose output: shows the pass/fail
        of every well-formedness predicate, not just the first failure."""
        return self._predicate_trace(sentence, stop_at_first_false=False)

    def _diagnose_simple(self, sentence: Sentence) -> tuple[int, Optional[str], Optional[str]]:
        trace = self._predicate_trace(sentence, stop_at_first_false=True)

        for i, (name, result) in enumerate(trace):
            if result is False:
                pred = _PRED_BY_NAME[name]
                feedback = self._build_feedback(name, pred["feedback"], sentence)
                return i, name, feedback

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
            irreg_names = {
                "Irreg_Ju": "ju (aju/reju/ou, venir)",
                "Irreg_Ho": "ho (aha/reho/oho, ir)",
                "Irreg_E": "'e (ha'e/ere/he'i, decir)",
            }
            verb_str = irreg_names.get(cv.verb_form.irreg.value, cv.verb_form.irreg.value)
            # Coq's cv_transitivity treats all irregulars as Intransitive
            transitivity = "Intransitive"

        subject_str = sentence.subject.surface if sentence.subject else "Ø"
        subj_person = sentence.subject.person.value if sentence.subject else "Third"
        subj_number = sentence.subject.number.value if sentence.subject else "Singular"
        verb_person = cv.person.value
        verb_number = cv.number.value

        # Person/number match but agreement still failed: the mismatch is
        # inclusivity (ñande-/ñane- inclusive vs ro-/ore- exclusive).
        if (pred_name == "ss_agree_ok" and sentence.subject is not None
                and subj_person == verb_person and subj_number == verb_number):
            from .types import SubjPronoun
            subj_incl = {
                SubjPronoun.Subj1PL_INCL: "Inclusive",
                SubjPronoun.Subj1PL_EXCL: "Exclusive",
            }.get(sentence.subject.pronoun)
            verb_incl = cv.incl.value if cv.incl else None
            if subj_incl and verb_incl and subj_incl != verb_incl:
                return (
                    f"Agreement error: subject '{subject_str}' is {subj_incl} "
                    f"but verb '{verb_str}' carries an {verb_incl} prefix "
                    f"(ñande-/ñane- = inclusive, ro-/ore- = exclusive)."
                )
        polarity = cv.polarity.value
        np_str = sentence.direct_obj.surface if sentence.direct_obj else ""

        from .types import _EVIDENTIAL_SURFACE
        evidential_str = (
            _EVIDENTIAL_SURFACE.get((cv.evidential.marker, cv.evidential.niko_variant), cv.evidential.marker.value)
            if cv.evidential else ""
        )
        mood_str = cv.mood.value

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
                evidential=evidential_str,
                mood=mood_str,
            )
        except (KeyError, IndexError):
            return f"Well-formedness predicate '{pred_name}' failed for '{verb_str}'."