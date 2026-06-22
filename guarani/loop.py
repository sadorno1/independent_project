"""
loop.py

Orchestrates an LLM execution loop that feeds generations through the morph 
analyzer and Coq verifier, sending programmatic feedback back for automatic correction.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .analyzer import load_lexicon, analyze, ParseResult
from .types import Sentence, ConjugatedVerb, NP, Person, Number, WordOrder, SentenceType
from .verifier import Verifier, VerifierResult

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3

CORRECTION_PROMPT_TEMPLATE = """\
The following Guaraní sentence has a grammatical error:

  sentence: {sentence}

Error: {feedback}

Please produce a corrected version of the sentence. Output only the corrected \
Guaraní sentence, nothing else.
"""

# ===========================================================================
# Structural Extraction & AST Generator
# ===========================================================================

def tokenize(text: str) -> list[str]:
    return text.strip().split()


def build_sentence(tokens: list[str]) -> Optional[Sentence]:
    """Scans for a verb pivot and structural SVO arguments to form a Sentence AST."""
    verb_parse: Optional[ParseResult] = None
    verb_idx: int = -1

    for i, token in enumerate(tokens):
        parses = analyze(token)
        if parses:
            parses.sort(key=lambda p: 0 if p.confidence == "exact_irreg" else 1)
            verb_parse = parses[0]
            verb_idx = i
            break

    if verb_parse is None:
        logger.warning("No verb parse found in tokens: %s", tokens)
        return None

    cv = verb_parse.conj_verb
    subj_tokens = tokens[:verb_idx]
    subject: Optional[NP] = None
    
    if subj_tokens:
        subj_surface = " ".join(subj_tokens)
        is_plural = any(t in ("hikuái", "hikuai", "kuéra", "kuera") for t in subj_tokens)
        subject = NP(
            surface=subj_surface,
            person=Person.Third,
            number=Number.Plural if is_plural else Number.Singular,
            human=False,
        )

    obj_tokens = tokens[verb_idx + 1:]
    direct_obj: Optional[NP] = None
    
    if obj_tokens:
        direct_obj = NP(
            surface=" ".join(obj_tokens),
            person=Person.Third,
            number=Number.Singular,
            human=False,
        )

    return Sentence(
        verb=cv, subject=subject, direct_obj=direct_obj,
        word_order=WordOrder.WO_SVO, sent_type=SentenceType.ST_Declarative,
    )

# ===========================================================================
# Execution Model & Correction Loop Engine
# ===========================================================================

@dataclass
class LoopResult:
    original_sentence: str
    final_sentence: str
    accepted: bool
    iterations: int
    history: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def run_loop(
    llm_fn: Callable[[str], str],
    initial_prompt: str,
    lexicon_csv: str | Path,
    coq_lib_dir: Optional[str | Path] = None,
    max_iterations: int = MAX_ITERATIONS,
    log_path: Optional[str | Path] = None,
) -> LoopResult:
    """Executes the complete generation-verification-correction engine workflow."""
    load_lexicon(lexicon_csv)
    verifier = Verifier(coq_lib_dir=coq_lib_dir)

    current_sentence = llm_fn(initial_prompt).strip()
    original_sentence = current_sentence
    history: list[dict] = []

    for iteration in range(max_iterations):
        logger.info("[%d] Checking: %s", iteration, current_sentence)

        tokens = tokenize(current_sentence)
        sentence_ast = build_sentence(tokens)

        if sentence_ast is None:
            history.append({
                "iteration": iteration, "sentence": current_sentence, "parse_error": True,
                "wf": None, "feedback": "Could not identify a verb in the sentence.",
            })
            correction_prompt = (
                f"The Guaraní sentence '{current_sentence}' could not be parsed. "
                "Please rewrite it as a simple subject-verb-object sentence."
            )
            current_sentence = llm_fn(correction_prompt).strip()
            continue

        vr: VerifierResult = verifier.verify(sentence_ast)
        history.append({
            "iteration": iteration, "sentence": current_sentence, "parse_error": False,
            "wf": vr.wf, "failed_predicate": vr.failed_predicate,
            "feedback": vr.feedback, "coq_term": vr.coq_term,
        })

        if vr.wf:
            logger.info("[%d] Accepted.", iteration)
            result = LoopResult(
                original_sentence=original_sentence, final_sentence=current_sentence,
                accepted=True, iterations=iteration + 1, history=history,
            )
            _maybe_log(result, log_path)
            return result

        logger.info("[%d] Failed predicate: %s", iteration, vr.failed_predicate)
        correction_prompt = CORRECTION_PROMPT_TEMPLATE.format(
            sentence=current_sentence,
            feedback=vr.feedback or "Unknown grammatical error.",
        )
        current_sentence = llm_fn(correction_prompt).strip()

    result = LoopResult(
        original_sentence=original_sentence, final_sentence=current_sentence,
        accepted=False, iterations=max_iterations, history=history,
    )
    _maybe_log(result, log_path)
    return result


def _maybe_log(result: LoopResult, log_path: Optional[str | Path]) -> None:
    if log_path is None:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(result.to_json() + "\n")