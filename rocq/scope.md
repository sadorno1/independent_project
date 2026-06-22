# Project Scope: Verified Guaraní Grammar + LLM Evaluation

---

## What this is

A mechanically verified Coq formalization of Paraguayan Guaraní morphology and syntax, used as a constraint-checking backend for LLM-generated Guaraní text. The verifier catches specific categories of morphological and syntactic errors, generates structured feedback, and feeds that back to the LLM in a correction loop. The evaluation compares LLM output quality before and after verification, rated by native Guaraní speakers.

Target venue: ACL Findings or ComputEL (low-resource NLP workshop)


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

## The verifier pipeline

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


### LLM correction prompt template

```
The Guaraní sentence you generated has a grammatical error:

Original: {original_output}
Error: {feedback_message}
Rule: {grammar_section_ref}

Please generate a corrected version. Produce only the corrected Guaraní sentence.
```

---

## Test suite (50 prompts)

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

Does the verifier catch real grammatical errors that LLMs make in Guaraní, and does the correction loop produce better output?

Three conditions:
1. **LLM only** — raw output from the model with no verification
2. **LLM + verifier** — output after one round of verifier feedback + correction
3. **Gold standard** — translation from a native speaker (used as reference, not shown to raters during blind evaluation)

Models to test: GPT-4, Claude 3.5 Sonnet, at minimum. Add a smaller model (Llama 3 or similar) if time permits.

### Native speaker recruitment

Target: 3–5 native Guaraní speakers.
- Reach out through Universidad Nacional de Asunción linguistics department
- Contact Ateneo de Lengua y Cultura Guaraní
- Reddit/Facebook Guaraní language communities
- My own contacts in Paraguay

What I need from them:
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

## Timeline

| Work |
|------|
| Theorems |
| Python parser + coqc integration. Get one end-to-end example working. |
| Build full verifier pipeline. Run on 50 prompts manually to check for bugs. |
| Automated evaluation run: all 50 prompts × 2–3 LLMs × 2 conditions. |
| Native speaker evaluation (send instrument, collect ratings). Fix parser bugs found in week 5. |
| Analyze results, Benchmarks. Write paper sections: system description, evaluation setup, results. |
| Related work, discussion, limitations. Revise. Submit. |

