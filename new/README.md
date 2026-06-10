# Guaraní Formal Grammar in Coq

A mechanically verified formalization of Paraguayan Guaraní grammar. Each file encodes specific grammatical rules as inductive types, computable functions, well-formedness predicates, and machine-checked theorems. Primary reference: *A Grammar of Paraguayan Guaraní* (Estigarribia 2020), cited by chapter and section throughout.

## File structure and dependencies

```
Primitives.v
    ↑
    ├── Numbers.v
    └── NounPhrases.v  (imports Primitives, Numbers)

Primitives.v
    ↑
    └── Verb.v

Sentences.v  (planned — imports NounPhrases, Verb)
```

---

## Primitives.v

Shared phonological and grammatical primitives used by every other file.

### Types

| Type | Constructors | What it encodes | §ref |
|------|-------------|-----------------|------|
| `orality` | `Oral`, `Nasal` | The fundamental phonological distinction driving all prefix/suffix allomorphy in the language | §1.2 |
| `word_ending` | `EndAEO`, `EndIUY` | Final vowel class of a noun root; determines nominal plural suffix (-ita vs -eta) | §2.2.1.a |
| `person` | `First`, `Second`, `Third` | Grammatical person | §2.1.3 |
| `number` | `Singular`, `Plural` | Grammatical number | §2.1.3 |
| `inclusivity` | `Inclusive`, `Exclusive` | Distinguishes 1pl inclusive *ñande* (speaker + hearer) from exclusive *ore* (speaker, not hearer) | §2.1.2.b |
| `poss_marker` | `Poss1`–`Poss3Pl` (7) | Possessive markers: *che*, *nde/ne*, *i/iñ*, *ñánde/ñáne*, *ore*, *pénde/péne*, *i/iñ* (3pl) | §2.1.2.b |

### Allomorphy functions

Every function encodes one phonological alternation rule driven by `orality` or `word_ending`.

| Function | Oral | Nasal | Rule encoded | §ref |
|----------|------|-------|-------------|------|
| `plural_suffix_adj` | kuéra | nguéra | Adjectival plural clitic alternation | §2.2.1.a |
| `plural_suffix_noun` | -ita (EndAEO) / -eta (EndIUY) | same | Nominal plural suffix by final vowel class | §2.2.1.a |
| `super_suffix` | -ite | -ete | Superlative suffix alternation | §2.2.1.d |
| `neg_prefix` | nd | n | Negation circumfix prefix alternation | §2.2.2.c |
| `passive_prefix` | je | ñe | Passive voice prefix alternation | §2.2.2.b.2 |
| `reciprocal_prefix` | jo | ño | Reciprocal voice prefix alternation | §2.2.2.b.3 |
| `coactive_prefix` | mbo | mo | Coactive (causative-of-intransitive) prefix alternation | §2.2.2.b.4 |
| `totalitative_suffix` | pa | mba | Totalitative aspect suffix alternation | §1.2 |
| `poss_marker_form` | varies | varies | Surface form of each possessive marker; *che* and *ore* are invariant, others alternate | §2.1.2.b |

### Theorems (8)

All proofs are by `reflexivity` or `discriminate` on the string-valued functions.

| Theorem | Statement |
|---------|-----------|
| `plural_adj_distinct` | `"kuéra" ≠ "nguéra"` |
| `plural_noun_distinct` | `"-ita" ≠ "-eta"` |
| `plural_adj_total` | Every `orality` maps to one of the two adjectival plural forms |
| `plural_noun_total` | Every `word_ending` maps to one of the two nominal plural forms |
| `neg_prefix_distinct` | `"nd" ≠ "n"` |
| `poss1_always_che` | `poss_marker_form o Poss1 = "che"` for all `o` |
| `poss1excl_always_ore` | `poss_marker_form o Poss1Excl = "ore"` for all `o` |
| `poss2_forms_distinct` | `poss_marker_form Oral Poss2 ≠ poss_marker_form Nasal Poss2` |

---

## Numbers.v

Grammar of the Guaraní numeral system from 1 to millions. Encodes how numerals *compose* — not their arithmetic values.

### Design

The system is base-10 with multiplicative composition. Power words:

| Word | Value | Multiplied form |
|------|-------|----------------|
| pa | 10 | mokõipa = 20, mboha­pypa = 30, … |
| sa | 100 | mokõisa = 200, … |
| su | 1,000 | mokõisu = 2,000, … |
| sua | 1,000,000 | mokõisua = 2,000,000, … |

`Peteĩ` (1) has **no `Mult` constructor** — the type system prevents `*peteĩsa` (you just say *sa* for 100). This constraint is enforced at the type level: `Fail Example wrong_peteisa := S1000_MultSa PeteĩM` does not compile.

### Types

| Type | Constructors | What it encodes |
|------|-------------|-----------------|
| `Digit` | `Peteĩ`…`Porundy` (9) | Basic digits 1–9 |
| `Mult` | `MokõiM`…`PorundyM` (8) | Multiplier forms of digits 2–9; Peteĩ has no multiplier |
| `Teen` | `Pateĩ`…`Paporundy` (9) | Fused forms 11–19 (pa + digit) |
| `Sub100` | 5 constructors | Numerals 1–99 |
| `Sub1000` | 5 constructors | Numerals 1–999 |
| `Sub1000Su` | 5 constructors | Numerals 1–999,999 |
| `GuaraniNum` | 5 constructors | Full numerals up to millions |

Each layer follows the same pattern: bare power word, power word with tail, multiplied power word, multiplied power word with tail.

### Functions

| Function | What it does |
|----------|-------------|
| `mult_to_digit` | Maps each `Mult` back to its corresponding `Digit` |
| `is_one` | Returns `true` only for the unique `peteĩ` path; used by `NounPhrases.v` to determine singular vs plural for numeral NPs |

### Theorems (8)

| Theorem | Statement |
|---------|-----------|
| `peteĩ_not_mult` | No `Mult` constructor maps to `Peteĩ` via `mult_to_digit` |
| `mult_to_digit_inj` | `mult_to_digit` is injective |
| `sa_ne_satail` | Bare *sa* is syntactically distinct from *sa* + tail |
| `su_ne_sutail` | Bare *su* is distinct from *su* + tail |
| `sua_ne_suatail` | Bare *sua* is distinct from *sua* + tail |
| `is_one_petei` | `is_one` returns `true` for the peteĩ path |
| `is_one_mult_false` | `is_one` returns `false` for any multiplied numeral |
| `is_one_sua_false` | `is_one` returns `false` for the million power word |

---

## NounPhrases.v

Full noun phrase grammar: root class alternation, noun and adjective types, all pronoun classes, demonstratives, nominal suffixes with ordering constraints, postpositions, NP well-formedness, and metadata inference for verb agreement.

### Root class system (§3.1.3)

Many noun (and some adjective/verb) roots change their initial consonant based on possessive context. The `root_class` type and `root_prefix` function encode this:

| Class | Non-possessed | 1st/2nd or NP possessor | 3rd person pronominal | Example |
|-------|-------------|------------------------|----------------------|---------|
| `Uniform` | "" | "" | "" | *jagua* always |
| `Triform` | t | r | h | *tova / rova / hova* (face) |
| `TriformNoT` | "" | r | h | *óga / róga / hóga* (house) |
| `Biform` | "" | r | "" (uses *i-* separately) | *túva / ru* (father) |
| `Quadriform` | t | r | h | *to'o / ro'o / ho'o* + 4th form (meat) |

`poss_context` has three constructors: `PossCtx_None`, `PossCtx_FirstSecond`, `PossCtx_Third`.  
Surface form of a noun in context: `noun_surface : noun -> poss_context -> string`.

### Types

| Type | What it encodes | §ref |
|------|----------------|------|
| `root_class` | 5 root alternation classes (see above) | §3.1.3 |
| `poss_context` | 3 possessive contexts driving root prefix selection | §3.1.3 |
| `noun` | Record: bare root string, `orality`, `word_ending`, `root_class` | §3.1 |
| `adjective` | Record: surface form string, `orality`, `root_class` (some adjectives are relational) | §3.3 |
| `subj_pronoun` | 7 subject pronouns: *che, nde, ha'e, ñande, ore, peẽ, ha'ekuéra* | §3.5.1 |
| `dem_proximity` | 6 demonstrative proximity levels (see below) | §3.4.2 |
| `dem_set` | `DemPresent` (referent visible) vs `DemRemoved` (absent/hearsay) | §3.4.2 |
| `indef_pron` | 8 indefinite pronouns: *maymáva, opáva, avave, mba'eve, oimeraẽva, mokõive, ambuéva, peteĩ mba'e* | §3.5.3 |
| `interrog_pron` | 10 interrogative pronouns: *mba'e, máva, mba'éicha, moõ, araka'e, mba'erã, mba'ére, mba'égui, mbovy, avamba'e* | §3.5.2 |
| `neg_pron` | 6 negative pronouns: *mba'eve, avave, ni peteĩ, mamove, araka'eve, máramo* — all require double negation on verb | §3.5.3 |
| `nominal_suffix` | 15 suffixes (see below) | §3.1.1, §3.7, §3.2.1.1, §2.2.1.d |
| `postposition` | 12 postpositions (see below) | §5 |
| `np_meta` | Record: `orality`, `number`, `person` — inferred from NP for verb agreement | — |
| `embedded_clause` | Placeholder record for relative/complement clause bodies (string form; avoids circular import with Verb.v) | §3.2.1.1, §12.2 |

### Demonstrative system (§3.4.2)

Two sets based on whether the referent is co-present or removed:

| Constructor | Singular form | Plural form | Meaning |
|-------------|-------------|------------|---------|
| `DemProxSpeaker` | ko | ko'ã | near speaker |
| `DemProxHearer` | pe | umi | near hearer |
| `DemDistal` | amo | umi | distal to both |
| `DemSharedPerson` | ku | umi | shared knowledge, persons |
| `DemSharedEvent` | ako | umi | shared knowledge, events |
| `DemHearsay` | aipo | umi | no direct knowledge |

- Adjective forms: `dem_adj_form : dem_proximity -> number -> string`
- Pronoun forms (with *-va*): `dem_pron_form : dem_proximity -> number -> string` — e.g., *ko* → *kóva*, *pe* → *péva*

### Nominal suffix system (§3.1.1, §3.7, §3.2.1.1, §2.2.1.d)

| Constructor | Oral | Nasal | Category | Grammar rule |
|-------------|------|-------|----------|-------------|
| `NS_Plural` | kuéra | nguéra | Plural | Countable plural §3.1.1 |
| `NS_Multitude` | eta | eta | Plural | Large/uncountable quantity §3.1.1 |
| `NS_Collective` | ty | ndy | Plural | Abundance of plants/objects §3.1.1 |
| `NS_PastKue` | kue | ngue | Temporal | Post-stative: was-but-no-longer §3.7 |
| `NS_FutureRa` | rã | rã | Temporal | Destinative: will-be, prospective §3.7 |
| `NS_ComparVe` | ve | ve | Degree | Comparative §2.2.1.d |
| `NS_Super` | ite | ete | Degree | Superlative §2.2.1.d |
| `NS_Privative` | 'ỹ | 'ỹ | Derivational | Absence/negation §3.2.2 |
| `NS_Diminutive` | 'i | 'i | Derivational | Small size or affection §3.2.3 |
| `NS_Attenuative` | vy | ngy | Derivational | Less intense §3.2.3 |
| `NS_NomHA` | ha | ha | Nominalizing | General nominalizer / subordinator §3.2.1.1.1 |
| `NS_NomVA` | va | va | Nominalizing | Adjectivizer / relativizer §3.2.1.1.3 |
| `NS_NomPY` | py | mby | Nominalizing | Passive nominalizer §3.2.1.1.2 |
| `NS_NomKue` | kue | ngue | Nominalizing | Abstract nominalizer (distinct from temporal) |
| `NS_OrdinalHA` | ha | ha | Ordinal | Ordinal suffix: *peteĩha* = first §3.4.3 |

### Suffix ordering constraint (§3.7)

`suffix_pair_ok : nominal_suffix -> nominal_suffix -> bool` encodes which two-suffix sequences are grammatical. `NP_Suf2` is only well-formed if this returns `true`.

| Pair | Valid | Example / reason |
|------|-------|-----------------|
| `NS_FutureRa` then `NS_PastKue` | ✓ | Frustrative: *cherogarãngue* = "my former future house" |
| `NS_PastKue` then `NS_FutureRa` | ✗ | *\*cherogakuerã* — §3.7 explicitly prohibits this |
| `NS_NomHA` then `NS_PastKue` | ✓ | Past agentive: *-hare* = "one who was" §3.2.1.1.1 |
| `NS_NomHA` then `NS_FutureRa` | ✓ | Future agentive: *-harã* = "one who will" §3.2.1.1.1 |
| `NS_NomPY` then `NS_PastKue` | ✓ | Past passive: *-pyre* = "thing that was V-ed" §3.2.1.1.2 |
| `NS_NomPY` then `NS_FutureRa` | ✓ | Future passive: *-pyrã* = "thing destined to be V-ed" §3.2.1.1.2 |
| all other pairs | ✗ | blocked |

### NP AST (`guarani_np`)

**Noun-headed NPs:**

| Constructor | Arguments | What it builds | §ref |
|-------------|-----------|----------------|------|
| `NP_Bare` | `noun` | Bare noun | §3.1 |
| `NP_Dem` | `dem_proximity`, `number`, `noun` | Demonstrative + noun: *ko jagua* | §3.4.2 |
| `NP_Art` | `number`, `noun` | Article + noun: *la jagua* (Spanish borrowing) | §3.4.1 |
| `NP_Adj` | `noun`, `adjective` | Noun + adjective: *jagua ñarõ* | §3.3 |
| `NP_Poss` | `poss_marker`, `noun` | Possessive + noun: *che juru* | §3.6 |
| `NP_Num` | `GuaraniNum`, `noun` | Numeral + noun: *mbohapy ryguasu* | §3.4.3 |
| `NP_Gen` | `guarani_np`, `noun` | Genitive by juxtaposition: *Maria ajaka* | §3.6 |
| `NP_DemPoss` | `dem_proximity`, `poss_marker`, `noun` | Dem + possessive + noun: *ko che irũ* | §3.4.2 |
| `NP_Rel` | `noun`, `embedded_clause` | Noun + relative clause (verb + *-va*): *kuña oikuaáva* | §3.2.1.1.3, §12.2.1 |
| `NP_Comp` | `embedded_clause` | Complement clause (verb + *-ha* as noun) | §3.2.1.1.1, §12.2.2 |
| `NP_Suf` | `guarani_np`, `nominal_suffix` | NP + one nominal suffix | §3.1.1, §3.7 |
| `NP_Suf2` | `guarani_np`, `nominal_suffix`, `nominal_suffix` | NP + two ordered suffixes; requires `suffix_pair_ok s1 s2 = true` | §3.7 |

**Pronoun NPs (no noun head):**

| Constructor | Arguments | What it builds | §ref |
|-------------|-----------|----------------|------|
| `NP_PronSubj` | `subj_pronoun` | *che, nde, ha'e, ñande, ore, peẽ, ha'ekuéra* | §3.5.1 |
| `NP_PronPoss` | `poss_marker` | Possessive pronoun: *chemba'e* = mine | §3.5.5 |
| `NP_PronDem` | `dem_proximity`, `number` | Demonstrative pronoun: *kóva, péva, amóva, …* | §3.5.4 |
| `NP_PronIndef` | `indef_pron` | *maymáva, opáva, avave, mba'eve, …* | §3.5.3 |
| `NP_PronInterrog` | `interrog_pron` | *mba'e, máva, moõ, araka'e, mbovy, …* | §3.5.2 |
| `NP_PronNeg` | `neg_pron` | *mba'eve, avave, mamove, araka'eve, …* | §3.5.3 |

**Coordination:**

| Constructor | Rule encoded | §ref |
|-------------|-------------|------|
| `NP_CoordHa` | *NP ha NP* — always yields `Plural`; merges person by 1st > 2nd > 3rd | §12.1 |
| `NP_CoordTera` | *NP tera NP* — or; inherits metadata from left conjunct | §12.1 |

### Postpositions (§5)

`postposition_form : orality -> postposition -> string`

| Constructor | Oral | Nasal | Meaning |
|-------------|------|-------|---------|
| `Post_Pe` | pe | me | in, at, to |
| `Post_Gui` | gui | gui | from |
| `Post_Gua` | gua | gua | from, of origin (invariant) |
| `Post_Rehe` | rehe | rehe | at, about, because of |
| `Post_Ndive` | ndive | ndie | with (accompaniment) |
| `Post_Guive` | guive | guive | since (invariant) |
| `Post_Peve` | peve | peve | until (invariant) |
| `Post_Rupi` | rupi | rupi | through, by means of (invariant) |
| `Post_Ari` | 'ári | 'ári | upon, on top of (invariant) |
| `Post_Guy` | guy | guy | under, below (invariant) |
| `Post_Guara` | guarã | guarã | for (benefactive, invariant) |
| `Post_Hagua` | haguã | haguã | in order to (purposive, invariant) |

### Well-formedness (`wf_np`)

| Rule | What it enforces |
|------|-----------------|
| `is_noun_headed` check on `NP_Suf` | Suffixes only attach to noun-headed NPs; pronouns cannot take nominal suffixes |
| `has_suffix` check on `NP_Suf` | No stacking via `NP_Suf` on `NP_Suf`; use `NP_Suf2` for valid two-suffix combinations |
| `suffix_pair_ok` check on `NP_Suf2` | The two-suffix sequence must be grammatical per §3.7 |
| `NP_Suf2` base check | `NP_Suf2` cannot wrap an already-suffixed NP; no triple suffixes |
| `NP_Gen` recursion | Possessor NP in a genitive must itself be well-formed |
| Coordination recursion | Both conjuncts of `NP_CoordHa`/`NP_CoordTera` must be well-formed |

### Metadata inference (`np_meta_of`)

Produces `np_meta` (person, number, orality) for use in verb agreement in Sentences.v.

| NP form | Person | Number | Orality |
|---------|--------|--------|---------|
| `NP_Bare n` | Third | Singular | `n_orality n` |
| `NP_Dem _ num n` | Third | `num` | `n_orality n` |
| `NP_Art num n` | Third | `num` | `n_orality n` |
| `NP_Adj n _` | Third | Singular | `n_orality n` |
| `NP_Poss pm n` | from `pm` | from `pm` | `n_orality n` |
| `NP_Num gn n` | Third | Singular if `is_one gn`, else Plural | `n_orality n` |
| `NP_Gen _ n` | Third | Singular | `n_orality n` |
| `NP_Suf x NS_Plural` | from `x` | Plural | from `x` |
| `NP_Suf x NS_Multitude` | from `x` | Plural | from `x` |
| `NP_Suf x _` | from `x` | from `x` | from `x` (transparent) |
| `NP_PronSubj p` | from `p` | from `p` | Oral (§3.5.1: subject pronouns never nasalize) |
| `NP_CoordHa x1 x2` | merge(person(x1), person(x2)) — 1st > 2nd > 3rd | Plural | from `x1` |
| `NP_CoordTera x1 _` | from `x1` | from `x1` | from `x1` |

`person_merge` is commutative, idempotent, and First always dominates.

### Theorems (grouped by rule, ~80 total)

| Rule group | Theorems | Grammar rule covered |
|------------|----------|---------------------|
| **NP-A** Root class prefixes | `rule_NPA1`–`rule_NPA7` (10) | t-/r-/h- selection for all 5 root classes; Uniform always empty; TriformNoT has no t- §3.1.3 |
| **NP-B** Well-formedness | `rule_NPB1`–`rule_NPB6` (8) | Base NPs wf; single suffix wf; double-suf stacking blocked; suffix on pronoun blocked; gen preserves wf §3.1, §3.7 |
| **NP-C** Suffix ordering | `rule_NPC1`–`rule_NPC7` (7) | -rã+kue valid; -kue+rã invalid; -ha+kue, -ha+rã, -py+kue, -py+rã valid; double plural invalid §3.7 |
| **NP-D** Subject pronoun metadata | `rule_NPD1`–`rule_NPD4` (4) | Person/number consistent; always Oral; render injective §3.5.1 |
| **NP-E** Bare noun metadata | `rule_NPE1`–`rule_NPE3` (3) | Always Third, Singular; orality from noun §3.1 |
| **NP-F** Plural allomorphy | `rule_NPF1`–`rule_NPF2` (2) | Nasal noun → nguéra; oral noun → kuéra §3.1.1 |
| **NP-G** Demonstrative system | `rule_NPG1`–`rule_NPG7` (9) | Form selection for all 6 proximity levels; proximal plural is ko'ã not umi; -va pronoun forms; always Third §3.4.2 |
| **NP-H** Suffix metadata effects | `rule_NPH1`–`rule_NPH5` (7) | Plural/multitude force Plural; temporal/degree/comparative suffixes are metadata-transparent §3.1.1, §3.7 |
| **NP-I** Genitive metadata | `rule_NPI1`–`rule_NPI4` (4) | Always Third, Singular; orality from head noun; noun-headed §3.6 |
| **NP-J** Possessive NP metadata | `rule_NPJ1`–`rule_NPJ3` (3) | Person/number from poss_marker; orality from noun §3.6 |
| **NP-K** Numeral NP metadata | `rule_NPK1`–`rule_NPK3` (3) | peteĩ → Singular; other numerals → Plural; always Third §3.4.3, §3.1.1 |
| **NP-L** Coordination metadata | `rule_NPL1`–`rule_NPL3` (4) | ha-coord always Plural; First dominates from either position; tera inherits left §12.1 |
| **NP-M** `person_merge` properties | `rule_NPM1`–`rule_NPM3` (4) | Commutative, idempotent, First always dominates |
| **NP-N** Postposition allomorphy | `rule_NPN1`–`rule_NPN3` (6) | pe→me (nasal); ndive→ndie (nasal); gua invariant §5 |
| **NP-O** Negative pronouns | `rule_NPO1`–`rule_NPO2` (4) | avave and mba'eve classified negative; maymáva and oimeraẽva not §3.5.3 |
| **NP-P** Interrogative rendering | `rule_NPP1`–`rule_NPP2` (5) | Each interrogative has distinct surface form; all Third, Singular for agreement §3.5.2 |

---

## Verb.v

Complete verb morphology: conjugation classes, transitivity, voice, mood, negation, tense/aspect/mood suffixes, person hierarchy for transitives, relational verb roots, irregular verbs, suffix ordering, and well-formedness.

### Types

| Type | Constructors | What it encodes | §ref |
|------|-------------|-----------------|------|
| `verb_class` | `Areal`, `Aireal`, `Chendal` | Three conjugation classes: standard active (a/re/o), glottal-initial active (ai/rei/oi), inactive/stative (che/nde/i) | §4.1–4.2 |
| `transitivity` | `Intransitive`, `Transitive`, `Ditransitive`, `PostpComplement` | Argument structure type; Chendal must be Intransitive | §4.1–4.4 |
| `verb_root_class` | `VRoot_Plain`, `VRoot_Relational` | Whether the root has h-/r-/t- alternation (same system as nouns) | §4.6 |
| `prefix_type` | `PfxActive`, `PfxInactive`, `PfxImperative`, `PfxPortmanteau` | Context for selecting relational root prefix | §4.6 |
| `voice` | `Active`, `Passive`, `Reciprocal`, `Coactive`, `Objective`, `Subsuntive` | Six grammatical voices | §6 |
| `mood` | `Indicative`, `Imperative`, `Optative`, `Prohibitive` | Four moods | §4.10.3 |
| `polarity` | `Positive`, `Negative` | Sentence polarity; Negative requires negation circumfix | §4.9 |
| `verbal_suffix` | 29 constructors | Full set of verbal suffixes (see below) | §4.9–4.10, §14 |
| `portmanteau_config` | `Port_1to2sg`, `Port_1to2pl` | 1st→2sg (ro-) and 1st→2pl (po-) portmanteau prefixes | §4.2 |
| `trans_prefix_mode` | `TPM_Active`, `TPM_Inactive`, `TPM_Portmanteau`, `TPM_Reflexive` | Result of person-hierarchy selection for transitive verbs | §4.2 |
| `irregular_verb` | `Irreg_Ju`, `Irreg_Ho`, `Irreg_E` | The three irregular verbs: *ju* (come), *ho* (go), *'e* (say) with root allomorphs | §4.5 |
| `verb` | record | `v_class`, `v_orality`, `v_root`, `v_transitivity`, `v_root_class` | — |
| `verb_form` | `VF_Regular verb`, `VF_Irregular irregular_verb` | Dispatch type: regular verb record or irregular verb enum. `render_verb` dispatches on this; callers (Sentences.v) need not know the distinction. | — |
| `conjugated_verb` | record | `cv_verb_form`, `cv_person`, `cv_number`, `cv_incl`, `cv_mood`, `cv_polarity`, `cv_voice`, `cv_suffixes` | — |

### Verbal suffix system (§4.9–4.10, §14)

29 constructors organized by function and ordered slot (see §14):

| Slot | Constructor(s) | Surface form | Category |
|------|---------------|-------------|----------|
| 1 | `VS_CausUka` | -uka | Causative of transitive §6.6.3 |
| 2 | `VS_AbilKuaa` | -kuaa | Ability §4.10.3.2 |
| 3 | `VS_TotalPa` | -pa/-mba | Totalitative §4.10.2 |
| 4 | `VS_ImpForce`, `VS_ImpRequest`, `VS_ImpPlead`, `VS_ImpUrge` | -ke, -na, -mi, -py | Imperative modalizers §4.10.3.1.2 |
| 5 | `VS_Volitive` | -se | Want to §4.10.3.4.1 |
| 6 | `VS_ComparVe` | -ve | Comparative |
| 7 | `VS_FutTa`, `VS_FutNe`, `VS_FutNegMoa`, `VS_ImmFutPota`, `VS_ObligVaera`, `VS_PastVaekue` | -ta, -ne, -mo'ã, -pota/-mbota, -va'erã, -va'ekue | Tense markers §4.10.1 |
| 8 | `VS_NegI`, `VS_NegRi`, `VS_NegTei`, `VS_Privative` | -i, -ri, -tei, -'ỹ | Negation suffixes §4.9, §4.10.3.1.3 |
| 9 | `VS_Intensifier` | -ite/-ete | Intensifier |
| 10 | `VS_NomVa`, `VS_NomHa` | -va, -ha | Nominalizers/complementizers §3.2.1.1 |
| 11 | `VS_AspectMa`, `VS_IterJevy`, `VS_HabitMi`, `VS_HabitVa`, `VS_FrustrRei`, `VS_Desiderative` | -ma, -jevy, -mi, -va, -rei, -nga'u | Aspect/mood §4.10.2, §4.10.3 |
| 12 | `VS_InterrogPa` | -pa | Interrogative clitic §8.5 |

`suffixes_ordered`: checks that suffix slots are non-decreasing left-to-right. Used in `wf_conjugated_verb`.

### Agreement prefix tables

**`areal_ind_prefix`** — standard active verbs (§4.1.1):

| Person/Number | Oral | Nasal |
|---|---|---|
| 1sg | a | a |
| 2sg | re | re |
| 3 (any number) | o | o |
| 1pl inclusive | ja | ña |
| 1pl exclusive | ro | ro |
| 2pl | pe | pe |

**`aireal_ind_prefix`** — glottal-initial active verbs (§4.2):

Same as Areal except: 1sg → ai, 2sg → rei, 3 → oi, 1pl.incl → jai/ñai, 1pl.excl → roi, 2pl → pei.

**`chendal_ind_prefix`** — inactive/stative verbs (§4.1.2):

| Person/Number | Oral | Nasal |
|---|---|---|
| 1sg | che | che |
| 2sg | nde | ne |
| 3 (any number) | i | iñ |
| 1pl inclusive | ñande | ñane |
| 1pl exclusive | ore | ore |
| 2pl | pende | pene |

**`imp_prefix`** — Imperative (§4.10.3.1.1): 2sg Areal/Aireal → `e`; all others same as indicative. Chendal never gets `e-`.

**`opt_prefix`** — Optative (§4.10.3.4.2, §14): `t-` + person markers. Active: ta/te/to/taja(taña)/toro/tape. Chendal: `"ta"` ++ inactive prefix (epenthetic *a*).

**`agr_prefix`**: unified dispatch over mood → calls the appropriate prefix function.

### Voice prefix rendering (§6)

`voice_prefix : voice -> orality -> string`

| Voice | Oral | Nasal |
|-------|------|-------|
| Active | "" | "" |
| Passive | je | ñe |
| Reciprocal | jo | ño |
| Coactive | mbo | mo |
| Objective | ro | ro |
| Subsuntive | poro | poro |

### Relational verb roots (§4.6)

`verb_relational_prefix : verb_root_class -> prefix_type -> string`

Relational roots take `h-` with active, imperative, and portmanteau prefix contexts; `r-` with inactive prefix context. Same t-/r-/h- system as relational nouns. `VRoot_Plain` always returns `""`.

Example: root *-ayhu* 'to love':  
- `a-h-ayhu` (1sg active) — h- with active prefix  
- `che-r-ayhu` (inactive — 3sg loves me) — r- with inactive prefix  
- `t-ayhu` (nominal, non-possessed) — t- in nominal context

### Negation circumfix (§4.9)

Prefix: `neg_prefix_for : orality -> string` → `"nd"` (Oral), `"n"` (Nasal).  
Eufonic vowel: `neg_eufonic : verb_class -> person -> number -> option inclusivity -> string` — inserted between neg prefix and agreement prefix to avoid consonant clusters. Chendal always uses `"a"`; active verbs use vowel matching the agreement prefix (`a`, `e`, `o`, `a` for 2pl).  
Suffix: one of `VS_NegI`, `VS_NegRi`, `VS_NegTei`, `VS_Privative` depending on mood and root.

**Future negation (§4.9):** `-mo'ã` replaces `-ta` in negative future contexts. `VS_FutTa` and `VS_FutNegMoa` cannot co-occur; `VS_FutNegMoa` requires `Negative` polarity.

### Person hierarchy for transitive verbs (§4.2)

`trans_prefix_selection : person -> number -> person -> number -> trans_prefix_mode`

Hierarchy: 1 > 2 > 3. When object outranks subject, the verb takes an inactive prefix marking the object. When subject outranks object, active prefix marks the subject. Special cases:

| Subject | Object | Mode | Prefix |
|---------|--------|------|--------|
| 1st | 2sg | `TPM_Portmanteau Port_1to2sg` | ro- |
| 1st | 2pl | `TPM_Portmanteau Port_1to2pl` | po- |
| 1st | 3rd | `TPM_Active` | subject active prefix |
| 2nd | 1st | `TPM_Inactive` | object inactive prefix |
| 3rd | 1st | `TPM_Inactive` | object inactive prefix |
| 3rd | 2nd | `TPM_Inactive` | object inactive prefix |
| same person (non-3rd) | — | `TPM_Reflexive` | use passive/reciprocal voice |
| 3rd | 3rd | `TPM_Active` | active o- |

### Irregular verb paradigms (§4.5)

`irreg_form : irregular_verb -> person -> number -> option inclusivity -> string`

| Person | *ju* (come) | *ho* (go) | *'e* (say) |
|--------|------------|----------|-----------|
| 1sg | aju | aha | ha'e |
| 2sg | reju | reho | ere |
| 3 | ou | oho | he'i |
| 1pl.incl | jaju | jaha | ja'e |
| 1pl.excl | roju | roho | ro'e |
| 2pl | peju | peho | peje |

### Rendering

`render_regular_verb : conjugated_verb -> verb -> string`  
Concatenates: (prohibitive *ani*) ++ neg_prefix ++ agr_prefix ++ voice_prefix ++ relational_prefix ++ root ++ suffixes.

`render_verb : conjugated_verb -> string`  
Unified entry point. Dispatches on `cv_verb_form`:
- `VF_Regular v` → `render_regular_verb cv v`
- `VF_Irregular iv` → `irreg_form iv person number incl` ++ rendered suffixes

Sentences.v calls `render_verb` only.

### Well-formedness (`wf_conjugated_verb`)

`wf_conjugated_verb` is a conjunction of 11 named predicates, each capturing one orthogonal constraint family. Proofs about a single constraint unfold only that predicate.

| Predicate | Constraint enforced | §ref |
|-----------|-------------------|------|
| `cv_structure_ok` | Chendal verbs must be Intransitive; Areal/Aireal can be any transitivity | §4.1.2 |
| `cv_neg_ok` | Polarity and negation suffix agree: Negative ↔ has a neg suffix; Positive ↔ no neg suffix | §4.9 |
| `cv_incl_ok` | 1pl requires `Some inclusivity`; all other persons/numbers require `None` | §4.1.1 |
| `cv_tense_ok` | At most one future tense marker; `VS_FutNegMoa` requires Negative polarity | §4.10.1, §4.9 |
| `cv_neg_count_ok` | At most one negation suffix | §4.9 |
| `cv_modalizer_ok` | Imperative modalizers (-ke/-na/-mi/-py) only in Imperative or Optative mood | §4.10.3.1.2 |
| `cv_mood_neg_ok` | Prohibitive requires Negative polarity and prohibits -i/-ri; Optative prohibits -i/-ri | §4.10.3.1.3, §4.10.3.4.2 |
| `cv_class_mood_ok` | Chendal verbs cannot use Imperative or Optative mood | §4.1.2 |
| `cv_homophone_ok` | Interrogative -pa and totalitative -pa cannot co-occur; habitual -mi and pleading -mi cannot co-occur | §4.10 |
| `no_dup_suffixes` | No suffix appears twice in the list | — |
| `suffixes_ordered` | Suffix slots are non-decreasing left to right | §14 |

### Theorems (grouped by rule, ~70 total)

| Rule group | Theorems | Grammar rule covered |
|------------|----------|---------------------|
| **A** Areal prefixes | `rule_A1`–`rule_A6` (7) | Full 1sg/2sg/3/1pl.incl/1pl.excl/2pl paradigm §4.1.1 |
| **B** Aireal prefixes | `rule_B1`–`rule_B6` (7) | ai/rei/oi/jai(ñai)/roi/pei paradigm §4.2 |
| **C** Chendal prefixes | `rule_C1`–`rule_C6` (8) | che/nde(ne)/i(iñ)/ñande(ñane)/ore/pende(pene) §4.1.2 |
| **D** Imperative prefix | `rule_D1`–`rule_D3` (4) | e- for 2sg Areal/Aireal only; Chendal no e-; 2pl same as indicative §4.10.3.1.1 |
| **E** Optative prefix | `rule_E1`–`rule_E3` (3) | ta/to/tape for 1sg/3/2pl active; Chendal gets ta+inactive §4.10.3.4.2 |
| **F** Voice prefixes | `rule_F1`–`rule_F6` (7) | All six voices; oral/nasal alternation; Active empty §6 |
| **G** Negation circumfix | `rule_G1`–`rule_G6` (6) | nd/n prefix; eufonic vowels; Chendal always a; no neg without suffix §4.9 |
| **H** Future negation | `rule_H1`–`rule_H3` (3) | -ta and -mo'ã exclusive; -mo'ã requires Negative; rendering §4.9 |
| **I** Person hierarchy | `rule_I1`–`rule_I10` (8) | All trans_prefix_selection cases; portmanteau rendering §4.2 |
| **J** Relational root | `rule_J1`–`rule_J5` (5) | h- with active/imp/portmanteau; r- with inactive; plain always empty §4.6 |
| **K** Irregular verbs | `rule_K1`–`rule_K5` (5) | Selected forms of ju/ho/'e paradigms §4.5 |
| **L** Inclusivity | `rule_L1`–`rule_L2` (2) | 1pl requires inclusivity; non-1pl forbids it §4.1.1 |
| **M** Suffix mutual exclusion | `rule_M1`–`rule_M3` (3) | No double future; habitual/pleading -mi exclusive; interrog/total -pa exclusive |
| **N** Prohibitive | `rule_N1`–`rule_N2` (2) | Requires Negative; cannot use -i §4.10.3.1.3 |
| **O** Imperative modalizers | `rule_O1` (1) | Modalizers blocked in Indicative §4.10.3.1.2 |
| **P** Affix ordering | `rule_P1`, `rule_P4`, `rule_P8`–`rule_P10` (5) | Valid and invalid suffix orderings §14 |
| **Q** Chendal structure | `rule_Q1`–`rule_Q3` (3) | Chendal no Transitive; Intransitive ok; Areal any transitivity §4.1.2 |
| **R** Chendal mood | `rule_R1`–`rule_R4` (4) | Chendal no Imperative/Optative (predicate + full wf) §4.1.2 |
| **S** Future exclusivity | `rule_S1`–`rule_S2` (2) | No -ta+-pota; single future ok §4.10.1 |
| **T** General wf | `rule_T1`–`rule_T3` (3) | No dup suffixes; bare positive verb wf; empty suffix renders empty |

---

## Sentences.v (planned)

Will cover clause composition and sentence-level well-formedness. Imports both `NounPhrases.v` and `Verb.v`.

### Planned sentence types

| Type | Example | Rule |
|------|---------|------|
| Intransitive | *Aguata* (I walk) | Subject + Verb |
| Transitive | *Ajogua kavaju* (I buy a horse) | Subject + Verb + Object (object optional) |
| Ditransitive | *Amombe'u ndéve la noticia* | Subject + Verb + DirectObj + IndirectObj |
| PostpComp | *Aikotevẽ nderehe* (I need you) | Subject + Verb + PostpPhrase |

Non-verbal sentences (equative, predicative, existential, possessive) are deferred.

### Planned well-formedness constraints

| Rule | Constraint | §ref |
|------|-----------|------|
| A: Subject-verb agreement | Verb prefix must match subject NP in person, number, and (for 1pl) inclusivity | §8.1 |
| B: Transitivity matching | Object arguments must match verb's transitivity type | §4.1–4.4 |
| C: Person hierarchy | When both subject and object are explicit, verb prefix must respect 1 > 2 > 3 | §4.2 |
| D: Double negation | Negative pronouns (*avave*, *mba'eve*, etc.) require a negated verb | §4.9, §3.5.3 |
| E: *Hikuái* placement | 3rd person plural pronoun must be postverbal (VSO/VOS order only) | §4.1.1 |
| F: Sentence type consistency | Mood must match sentence type (declarative → Indicative; imperative → Imperative; prohibitive → Prohibitive) | §4.10.3 |
| G: Verb well-formedness | `wf_conjugated_verb` from Verb.v must hold | — |

Word order (§8.1): all six permutations (SVO, SOV, VSO, VOS, OSV, OVS) are grammatical; order encodes information structure. Null subject and object are both permitted and common.

---

## Not yet formalized

Recognized in the grammar but deferred:

| Feature | Description | §ref |
|---------|-------------|------|
| Chendal 3rd person *hi'*/*ij* variants | Two further 3rd person allomorphs for specific root types; currently simplified to *i*/*iñ* | §3.1.3 |
| Accent shift from tonic suffixes | Tonic suffixes move stress; constructors distinguish tonic/atonic pairs but stress position is not rendered | §1.2 |
| Objective voice *guero-* variant | Currently only *ro-* is modeled | §2.2.2.b.5 |
| Gender marking with *kuña* | *mitã kuña* = girl; not yet in NP types | §2.2.1.b |
| *[+human]* feature on nouns | Required to enforce *=pe/=me* marking on human direct objects | §5.1 |
| Noun incorporation | Productive morpheme stacking at the word/clause boundary | §11 |
| Serial verb constructions | `NP_Rel`/`NP_Comp` cover the basic *-va/-ha* constructions; full internal agreement not yet enforced | §12.2.2 |
| Evidentiality markers | Not yet modeled | §7 |
| Information structure | Topic/focus marking | §13 |
| Full adverb system | Placement rules for all adverb classes | §2.1.4 |
| Complex/subordinate clauses | Temporal (*ramo*), causal (*rupi*), conditional (*rõ*), purposive (*haguã*) clauses | §12.2.3 |