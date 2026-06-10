# Project Scope: Verified Guaraní Grammar + LLM Evaluation

---

## What this is

A mechanically verified Coq formalization of Paraguayan Guaraní morphology and syntax, used as a constraint-checking backend for LLM-generated Guaraní text. The verifier catches specific categories of morphological and syntactic errors, generates structured feedback, and feeds that back to the LLM in a correction loop. The evaluation compares LLM output quality before and after verification, rated by native Guaraní speakers.

Target venue: ACL Findings or ComputEL (low-resource NLP workshop).  
Timeline: ~8 weeks to working system + paper draft.

---

## Part 1: Coq grammar files

### Primitives.v — done

Shared types and allomorphy functions used by every other file. Nothing to add here.

### Numbers.v — done

Numeral grammar up to millions. Nothing to add here.

### NounPhrases.v — done

Full NP grammar. The one thing still missing is `render_np`, which produces a surface string from a `guarani_np` term. This is needed for the verifier feedback loop (to show the corrected form, not just say what was wrong). Add this before moving on.

Rendering rules:
- `NP_Bare n` → `noun_surface n PossCtx_None`
- `NP_Dem prox num n` → `dem_adj_form prox num ++ " " ++ noun_surface n PossCtx_None`
- `NP_Poss pm n` → `poss_marker_form (n_orality n) pm ++ " " ++ noun_surface n PossCtx_FirstSecond`
- `NP_Num gn n` → render numeral ++ " " ++ noun_surface
- `NP_Suf np suf` → render_np np ++ render_nom_suffix suf (np_orality (np_meta_of np))`
- `NP_PronSubj p` → `render_subj_pronoun p`
- etc.

### Verb.v — done (refactored)

All verb morphology including the factored `wf_conjugated_verb` predicates and `render_verb` dispatch. Nothing to add before Sentences.v.

### Sentences.v — next file

This is the main remaining Coq work. Scope is intentionally limited to what's needed for the evaluation — see below.

---

## Part 2: Sentences.v

### Sentence types in scope

Only verbal sentences. Non-verbal (equative, predicative, existential) are deferred — they're common but the morphological interest is mostly in verbal sentences, and 8 weeks is not enough time to do both well.

```
Inductive word_order : Type :=
  | SVO | SOV | VSO | VOS | OSV | OVS.

Inductive sentence_type : Type :=
  | Declarative
  | YesNoInterrog    (* adds =pa or =piko *)
  | ContentInterrog  (* mba'e, máva, etc. in NP position *)
  | Imperative
  | Prohibitive.     (* ani + verb + -tei *)

Record simple_sentence : Type := mkSentence {
  ss_subject  : option guarani_np;   (* null subjects allowed *)
  ss_verb     : conjugated_verb;
  ss_object   : option guarani_np;   (* null objects allowed *)
  ss_ind_obj  : option guarani_np;   (* ditransitive only *)
  ss_postp    : option (guarani_np * postposition);  (* PostpComp only *)
  ss_order    : word_order;
  ss_type     : sentence_type;
  ss_hikuai   : bool                 (* whether hikuái follows verb *)
}.
```

### Grammar rules enforced by `wf_sentence`

**Rule A: Subject-verb agreement (§8.1)**

If a subject NP is present, the verb's person, number, and inclusivity must match `np_meta_of subject`. Null subjects are always ok — the verb carries person/number itself.

Examples:
- *Che aguata* ✓ — 1sg NP, 1sg prefix
- *Che reho* ✗ — 1sg NP, 2sg prefix

**Rule B: Transitivity matching (§4.1–4.4)**

The arguments present must match the verb's declared transitivity.
- `Intransitive` → no direct object, no indirect object
- `Transitive` → direct object optional, no indirect object
- `Ditransitive` → direct object required, indirect object required
- `PostpComplement` → postpositional phrase required, no bare object

**Rule C: Person hierarchy for explicit arguments (§4.2)**

When both subject and object NPs are present in a transitive sentence, the verb prefix must follow 1 > 2 > 3. Checked via `trans_prefix_selection` from Verb.v.

Examples:
- *Ha'e che-nupã* ✓ — 3sg subject, 1sg object → inactive prefix
- *Ha'e o-nupã che* ✗ — active o- when object outranks subject

**Rule D: Double negation (§4.9, §3.5.3)**

If any NP in the sentence uses a negative pronoun (checked via `is_negative_pron` and `NP_PronNeg`), the verb must have Negative polarity. This is Guaraní's negative concord — *mba'eve ndajapói* (I don't do anything) requires both the negative pronoun and the negative verb.

**Rule E: Hikuái placement (§4.1.1)**

3rd person plural pronoun *hikuái* must be postverbal. Encoded as: `ss_hikuai = true` requires `ss_order ∈ {VSO, VOS}` (or more precisely, the verb appears before any postverbal pronoun slot). Checked against word order.

**Rule F: Sentence type / mood consistency**

| Sentence type | Required mood |
|--------------|--------------|
| Declarative | Indicative |
| YesNoInterrog | Indicative (=pa is a suffix, not a mood change) |
| ContentInterrog | Indicative |
| Imperative | Imperative |
| Prohibitive | Prohibitive |

**Rule G: Verb well-formedness**

`wf_conjugated_verb cv = true` from Verb.v. This is just a delegation — Sentences.v inherits all 11 morphological constraints automatically.

### What's NOT in scope for Sentences.v

- Non-verbal sentences
- Subordinate/complex clauses (you have `NP_Rel` and `NP_Comp` as NP-level placeholders, which is enough for the paper)
- Noun incorporation
- Information structure / topic-focus marking
- Evidentiality
- Full adverb placement

### Theorems to prove in Sentences.v (~25)

Five rule groups, roughly 5 theorems each:

- Rule A: agreement holds for matching NPs; fails for mismatched; null subject always ok
- Rule B: intransitive with object fails; transitive without object ok; ditransitive needs both
- Rule C: hierarchy cases — 3rd subj + 1st obj needs inactive; 1st subj + 3rd obj needs active
- Rule D: negative pronoun + positive verb fails; negative pronoun + negative verb ok
- Rule E: hikuái + SVO fails; hikuái + VSO ok

---

## Part 3: Dictionary.v

A minimal lexicon so examples aren't all generic variables. Only what's needed to run the 50-prompt test suite.

### Target size

- 30 verbs (10 Areal, 10 Aireal, 5 Chendal, 5 relational roots)
- 50 nouns (mix of Uniform, Triform, TriformNoT, Biform)
- 10 adjectives

### Priority verbs to include

These come up directly in the test prompts:

| Root | Class | Transitivity | Root class | Gloss |
|------|-------|-------------|-----------|-------|
| guata | Areal | Intransitive | Plain | walk |
| mba'apo | Areal | Intransitive | Plain | work |
| nupã | Areal | Transitive | Plain | beat |
| jogua | Areal | Transitive | Plain | buy |
| mombe'u | Areal | Ditransitive | Plain | tell |
| kotevẽ | Chendal | Intransitive | Plain | need |
| ayhu | Areal | Transitive | Relational | love |
| japo | Areal | Transitive | Plain | do/make |
| kuaa | Chendal | Intransitive | Relational | know |
| 'u | Areal | Transitive | Plain | eat |
| ho | Irregular | — | — | go |
| ju | Irregular | — | — | come |
| 'e | Irregular | — | — | say |

---

## Part 4: The verifier pipeline

### Architecture

```
LLM prompt
    ↓
LLM generates Guaraní text
    ↓
Python parser: text → Coq term (as string)
    ↓
coqc runs: Compute wf_sentence <term>
    ↓
if true  → accept, log
if false → identify failed predicate
         → generate feedback string
         → send back to LLM with correction prompt
    ↓
LLM generates corrected output
    ↓
re-run verifier
    ↓
log both outputs for human evaluation
```

### Parser approach

Parsing is the hardest part and doesn't need to be perfect — it needs to be good enough to catch the error categories in the test suite. A brittle parser that works on 50 controlled prompts is sufficient for the paper; the point is the verification and evaluation, not a production parser.

Approach: morpheme segmentation by regex + lookup table, then rule-based NP/VP identification.

```python
def segment_verb(word: str, verb_table: dict) -> dict:
    # check for nd-/n- negation prefix
    # strip agreement prefix (a/re/o/ja/ro/pe + variants)
    # strip voice prefix (je/jo/mbo etc.)
    # strip relational prefix (h/r)
    # look up remaining root in verb_table
    # strip suffixes right-to-left by known suffix list
    return {
        "negated": bool,
        "person": person,
        "number": number,
        "voice": voice,
        "root": str,
        "suffixes": list
    }

def parse_sentence(text: str, lexicon: dict) -> SimpleSentence:
    words = text.strip().split()
    verb_word = identify_verb(words, lexicon)
    verb_data = segment_verb(verb_word, lexicon["verbs"])
    subject = identify_subject_np(words, verb_word)
    obj = identify_object_np(words, verb_word, subject)
    order = determine_word_order(words, subject, verb_word, obj)
    return build_coq_term(verb_data, subject, obj, order)
```

Then the Coq term gets written as a string into a test file:

```coq
(* generated by verifier.py *)
Compute wf_sentence
  (mkSentence
    (Some (NP_PronSubj Subj1SG))
    (mkConjVerb (VF_Regular v_mbapo)
                First Singular None Indicative Negative Active
                (VS_FutNegMoa :: VS_NegI :: nil))
    None None None SVO Declarative false).
```

### Feedback messages

When `wf_sentence` returns false, the verifier checks each predicate individually and generates a natural language feedback string:

| Failed predicate | Feedback message |
|-----------------|-----------------|
| `cv_neg_ok` | "Negative polarity requires a negation suffix (-i, -ri, etc.) on the verb." |
| `cv_tense_ok` (FutNegMoa + Positive) | "Use -mo'ã for negative future, not -ta. These cannot co-occur." |
| Subject-verb agreement | "Verb prefix {prefix} doesn't match subject {person}/{number}. Expected {correct_prefix}." |
| Person hierarchy | "With a {obj_person} object and {subj_person} subject, use {correct_mode} prefix, not {used_prefix}." |
| Double negation | "Negative pronoun {pron} requires the verb to also be negated (double negation)." |
| Transitivity | "Verb {root} is {transitivity} — it cannot take a direct object." |

### LLM correction prompt template

```
The Guaraní sentence you generated has a grammatical error:

Original: {original_output}
Error: {feedback_message}
Rule: {grammar_section_ref}

Please generate a corrected version. Produce only the corrected Guaraní sentence.
```

---

## Part 5: Test suite (50 prompts)

### Structure

Each prompt has:
- an English prompt sent to the LLM
- the expected correct Guaraní output
- the grammar rule being tested
- at least one known bad pattern the verifier should catch

### Prompt categories

**Person hierarchy — 10 prompts**

These are the highest-value tests because this is one of the most common LLM errors on agglutinative languages with non-trivial agreement.

| # | Prompt | Expected | Error to catch |
|---|--------|----------|---------------|
| 1 | "I love you (sg)" | rohayhu | active a- instead of portmanteau ro- |
| 2 | "They beat me" | chenupã | active o- instead of inactive che- |
| 3 | "You (sg) see me" | chehechapo | active re- instead of inactive che- |
| 4 | "I buy it" | ajogua | should be active (ok) |
| 5 | "She tells him" | omombe'u chupe | inactive prefix when 3rd→3rd |
| 6 | "I love you all" | pohayhu | po- portmanteau for 1→2pl |
| 7 | "You (sg) beat her" | renupã | active re- (2nd subj > 3rd obj) |
| 8 | "She beats you" | ndenupã | inactive nde- (3rd subj, 2nd obj outranks) |
| 9 | "We (incl) see you" | rohechapo | ro- portmanteau |
| 10 | "They tell me" | chemombe'u | inactive che- |

**Negative morphology — 8 prompts**

| # | Prompt | Expected | Error to catch |
|---|--------|----------|---------------|
| 11 | "I will not work" | ndamba'apomo'ãi | -ta + negative (\*ndamba'apotái) |
| 12 | "I don't do anything" | mba'eve ndajapói | negative pronoun + positive verb |
| 13 | "Nobody knows" | avave ndoikuaái | same as above |
| 14 | "I'm not walking" | ndaguatái | missing suffix |
| 15 | "Don't go!" | ani reho tei | regular negation instead of prohibitive |
| 16 | "I didn't eat" | ndahúi | wrong suffix selection |
| 17 | "She won't come" | ndoúmo'ãi | irregular verb + negative future |
| 18 | "I never work" | araka'eve ndamba'apói | negative time adverb + double neg |

**Relational roots (h-/r- alternation) — 8 prompts**

| # | Prompt | Expected | Error to catch |
|---|--------|----------|---------------|
| 19 | "I love" | ahayhu | missing h- with active prefix |
| 20 | "She loves me" | cherayhu | missing r- with inactive prefix |
| 21 | "I know Guaraní" | aikuaa guaraní | h- vs r- on kuaa |
| 22 | "She knows me" | chekuaa | inactive + r- |
| 23 | "I remember" (rekóke) | arekóke | h-/r- on reko |
| 24 | "I want" (pochy) | aipochy | correct aireal class |
| 25 | "She hears" | ohendu | h- with active prefix |
| 26 | "She hears me" | cherendu | r- with inactive |

**Nasal harmony — 6 prompts**

| # | Prompt | Expected | Error to catch |
|---|--------|----------|---------------|
| 27 | "We (incl) walk" | ñaguata | ja- instead of ña- for nasal verb |
| 28 | "We (incl) eat" | ñandu | ña- with nasal root |
| 29 | "At the field" (ñú) | ñúme | pe instead of me |
| 30 | "The children" (mitã) | mitãnguéra | kuéra instead of nguéra |
| 31 | "His house was" | hogakue | wrong suffix allomorph |
| 32 | "With my mother" | chesyndive → chesydie | ndive instead of ndie for nasal |

**Imperative and optative — 6 prompts**

| # | Prompt | Expected | Error to catch |
|---|--------|----------|---------------|
| 33 | "Walk!" | eguata | o- instead of e- |
| 34 | "Let him walk" | toguata | wrong optative prefix |
| 35 | "Please walk" | eguatana | modalizer in wrong mood |
| 36 | "Walk, all of you" | peguata | wrong 2pl imperative |
| 37 | "Please sit, you all" | peguapymikena | stacked modalizers |
| 38 | "Let's walk (incl)" | jaguata | correct ja- optative |

**Tense and aspect — 6 prompts**

| # | Prompt | Expected | Error to catch |
|---|--------|----------|---------------|
| 39 | "I already walked" | aguatama | missing -ma completive |
| 40 | "I'm about to walk" | aguatapota | wrong tense marker |
| 41 | "I used to walk" | aguatami | wrong -mi tonicity (habitual vs rogative) |
| 42 | "I must walk" | aguatava'erã | wrong suffix ordering |
| 43 | "I walk again" | aguatajevy | missing iterative |
| 44 | "I walked in vain" | aguatarei | frustrative |

**Transitivity and argument structure — 6 prompts**

| # | Prompt | Expected | Error to catch |
|---|--------|----------|---------------|
| 45 | "I need you" (kotevẽ) | aikotevẽ nderehe | wrong postposition |
| 46 | "I walk home" | ahaguata chépe | PostpComp without postposition |
| 47 | "I eat a horse" | aha'u kavaju | intransitive used transitively (different root) |
| 48 | "I tell you the news" | amombe'u ndéve la noticia | ditransitive argument order |
| 49 | "She needs water" | ikotevẽ y nderehe | Chendal 3sg prefix |
| 50 | "I buy and sell" | ajogua ha aheja | coordination |

---

## Part 6: Evaluation

### What we're measuring

Not fluency in general — specifically: does the verifier catch real grammatical errors that LLMs make in Guaraní, and does the correction loop produce better output?

Three conditions:
1. **LLM only** — raw output from the model with no verification
2. **LLM + verifier** — output after one round of verifier feedback + correction
3. **Gold standard** — translation from a native speaker (used as reference, not shown to raters during blind evaluation)

Models to test: GPT-4, Claude 3.5 Sonnet, at minimum. Add a smaller model (Llama 3 or similar) if time permits — the gap is likely larger there and makes the argument stronger.

### Native speaker recruitment

Target: 3–5 native Guaraní speakers. Paraguay has ~6 million speakers so finding fluent speakers for a paid remote evaluation task is feasible. Options:
- Reach out through Universidad Nacional de Asunción linguistics department
- Contact Ateneo de Lengua y Cultura Guaraní
- Reddit/Facebook Guaraní language communities
- Your own contacts in Paraguay

What you need from them:
1. Gold-standard translations for all 50 prompts (one speaker sufficient, others rate)
2. Grammaticality ratings (1–5 scale) for LLM only vs LLM + verifier outputs
3. Naturalness ratings (separate from grammaticality — a sentence can be grammatically correct but stilted)

Rating instrument (simple):

```
Sentence: [output]

1. Is this grammatically correct Guaraní?
   1 = clearly wrong  2 = has errors  3 = acceptable  4 = correct  5 = perfectly natural

2. Would a native speaker say this?
   1 = never  2 = unlikely  3 = maybe  4 = yes  5 = exactly how I'd say it

3. If you marked anything below 4 on Q1, what is wrong? (free text)
```

Blind evaluation: speakers see condition 1 and condition 2 in random order, don't know which is which.

### Metrics

| Metric | How it's computed |
|--------|-----------------|
| Verifier precision | % of flagged sentences that native speakers also rated as incorrect |
| Verifier recall | % of sentences rated incorrect by native speakers that verifier flagged |
| Grammaticality improvement | mean rating (condition 2) minus mean rating (condition 1), by error category |
| Naturalness improvement | same for Q2 |
| Error category breakdown | which of the 7 wf constraints catches the most real errors |

Verifier precision matters more than recall for the paper's argument — if the verifier flags something, it should actually be wrong. Low precision would undermine the claim.

### What a good result looks like

Realistically: precision ~0.85+, recall ~0.60–0.75 (some errors are outside the formalized grammar scope), grammaticality improvement of ~0.5–1.0 points on the 1–5 scale for the error categories the verifier covers.

The paper's argument doesn't require the verifier to catch everything — it requires it to catch the things it's designed to catch, reliably, and for those corrections to be accepted by native speakers as improvements.

### What a bad result looks like and what to do

If precision is low (verifier flags grammatical sentences as wrong): re-examine the well-formedness predicates, probably there's an overconstraint somewhere.

If recall is low (many errors the verifier misses): that's expected and honest — the paper explicitly scopes to formalized morphological rules and doesn't claim to cover all Guaraní grammar.

If grammaticality improvement is small: check whether LLMs are already getting these rules right. If GPT-4 already generates correct portmanteau prefixes 90% of the time, that test category isn't interesting — focus the paper on the categories where LLMs actually fail.

---

## Timeline

| Week | Work |
|------|------|
| 1 | Add `render_np` to NounPhrases.v. Write Sentences.v types and `wf_sentence`. |
| 2 | Theorems for Sentences.v. Write Dictionary.v (30 verbs, 50 nouns). |
| 3 | Python parser + coqc integration. Get one end-to-end example working. |
| 4 | Build full verifier pipeline. Run on 50 prompts manually to check for bugs. |
| 5 | Automated evaluation run: all 50 prompts × 2–3 LLMs × 2 conditions. |
| 6 | Native speaker evaluation (send instrument, collect ratings). Fix parser bugs found in week 5. |
| 7 | Analyze results. Write paper sections: system description, evaluation setup, results. |
| 8 | Related work, discussion, limitations. Revise. Submit. |

The parser in week 3–4 is the highest-risk item. If it's taking too long, scope it down: do morpheme segmentation only (verb parsing), skip full NP parsing, and limit the test suite to the prompts where the error is purely verbal morphology. That's still ~35 of the 50 prompts and covers the most interesting grammar.