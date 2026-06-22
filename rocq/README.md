# Guaraní Formal Grammar in Coq

A mechanically verified formalization of Paraguayan Guaraní grammar. Each file encodes specific grammatical rules as inductive types, computable functions, well-formedness predicates, and machine-checked theorems. Primary reference: *A Grammar of Paraguayan Guaraní* (Estigarribia 2020), cited by chapter and section throughout.


## Syntax.v

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

`Peteĩ` (1) has **no `Mult` constructor** — the type system prevents `*peteĩsa` (you just say *sa* for 100). This constraint is enforced at the type level.

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

Full noun phrase grammar: root class alternation, noun and adjective types, all pronoun classes, demonstratives, nominal suffixes with ordering constraints, postpositions, embedded clauses, NP well-formedness, metadata inference for verb agreement, and surface rendering.

### Root class system (§3.1.3)

| Class | Non-possessed | 1st/2nd or NP possessor | 3rd person pronominal | Example |
|-------|-------------|------------------------|----------------------|---------|
| `Uniform` | "" | "" | "" | *jagua* always |
| `Triform` | t | r | h | *tova / rova / hova* (face) |
| `TriformNoT` | "" | r | h | *óga / róga / hóga* (house) |
| `Biform` | "" | r | "" (uses *i-* separately) | *túva / ru* (father) |
| `Quadriform` | t | r | h | *to'o / ro'o / ho'o* + 4th form (meat) |

`poss_context`: `PossCtx_None`, `PossCtx_FirstSecond`, `PossCtx_Third`.
`noun_surface : noun -> poss_context -> string`

### Types

| Type | What it encodes | §ref |
|------|----------------|------|
| `root_class` | 5 root alternation classes | §3.1.3 |
| `poss_context` | 3 possessive contexts driving root prefix selection | §3.1.3 |
| `noun` | Record: root string, `orality`, `word_ending`, `root_class`, `n_human : bool` | §3.1, §5.1 |
| `adjective` | Record: surface form string, `orality`, `root_class` | §3.3 |
| `subj_pronoun` | 7 subject pronouns: *che, nde, ha'e, ñande, ore, peẽ, ha'ekuéra* | §3.5.1 |
| `dem_proximity` | 6 demonstrative proximity levels | §3.4.2 |
| `indef_pron` | 8 indefinite pronouns | §3.5.3 |
| `interrog_pron` | 10 interrogative pronouns | §3.5.2 |
| `neg_pron` | 6 negative pronouns — all require double negation on verb | §3.5.3 |
| `nominal_suffix` | 15 suffixes | §3.1.1, §3.7, §3.2.1.1, §2.2.1.d |
| `postposition` | 12 postpositions | §5 |
| `np_meta` | Record: `orality`, `number`, `person`, `inclusivity` — inferred from NP for verb agreement | — |
| `embedded_clause` | Alias for `conjugated_verb`; used by `NP_Rel` and `NP_Comp` | §3.2.1.1, §12.2 |

The `noun` record carries `n_human : bool` (§5.1: [+human] nouns require `=pe/=me` as postpositional complement marker).

`embedded_clause` is aliased directly to `conjugated_verb` from Verb.v. No duplication: `wf_np` for `NP_Rel` and `NP_Comp` delegates to `wf_conjugated_verb` plus a suffix-shape check (`VS_NomVa` for relatives, `VS_NomHa` for complements).

### Demonstrative system (§3.4.2)

| Constructor | Singular | Plural | Meaning |
|-------------|---------|--------|---------|
| `DemProxSpeaker` | ko | ko'ã | near speaker |
| `DemProxHearer` | pe | umi | near hearer |
| `DemDistal` | amo | umi | distal to both |
| `DemSharedPerson` | ku | umi | shared knowledge, persons |
| `DemSharedEvent` | ako | umi | shared knowledge, events |
| `DemHearsay` | aipo | umi | no direct knowledge |

`dem_adj_form : dem_proximity -> number -> string`
`dem_pron_form : dem_proximity -> number -> string` — e.g., *ko* → *kóva*, *pe* → *péva*

### Nominal suffix system (§3.1.1, §3.7, §3.2.1.1, §2.2.1.d)

| Constructor | Oral | Nasal | Category | §ref |
|-------------|------|-------|----------|------|
| `NS_Plural` | kuéra | nguéra | Plural | §3.1.1 |
| `NS_Multitude` | eta | eta | Plural | §3.1.1 |
| `NS_Collective` | ty | ndy | Plural | §3.1.1 |
| `NS_PastKue` | kue | ngue | Temporal | §3.7 |
| `NS_FutureRa` | rã | rã | Temporal | §3.7 |
| `NS_ComparVe` | ve | ve | Degree | §2.2.1.d |
| `NS_Super` | ite | ete | Degree | §2.2.1.d |
| `NS_Privative` | 'ỹ | 'ỹ | Derivational | §3.2.2 |
| `NS_Diminutive` | 'i | 'i | Derivational | §3.2.3 |
| `NS_Attenuative` | vy | ngy | Derivational | §3.2.3 |
| `NS_NomHA` | ha | ha | Nominalizing | §3.2.1.1.1 |
| `NS_NomVA` | va | va | Nominalizing | §3.2.1.1.3 |
| `NS_NomPY` | py | mby | Nominalizing | §3.2.1.1.2 |
| `NS_NomKue` | kue | ngue | Nominalizing | — |
| `NS_OrdinalHA` | ha | ha | Ordinal | §3.4.3 |

### Suffix ordering constraint (§3.7)

`suffix_pair_ok : nominal_suffix -> nominal_suffix -> bool`

| Pair | Valid | Example |
|------|-------|---------|
| `NS_FutureRa` then `NS_PastKue` | ✓ | *cherogarãngue* = "my former future house" |
| `NS_PastKue` then `NS_FutureRa` | ✗ | *\*cherogakuerã* |
| `NS_NomHA` then `NS_PastKue` | ✓ | *-hare* = "one who was" |
| `NS_NomHA` then `NS_FutureRa` | ✓ | *-harã* = "one who will" |
| `NS_NomPY` then `NS_PastKue` | ✓ | *-pyre* = "thing that was V-ed" |
| `NS_NomPY` then `NS_FutureRa` | ✓ | *-pyrã* = "thing destined to be V-ed" |
| all other pairs | ✗ | blocked |

### NP AST (`guarani_np`)

**Noun-headed NPs:**

| Constructor | Arguments | What it builds | §ref |
|-------------|-----------|----------------|------|
| `NP_Bare` | `noun` | Bare noun | §3.1 |
| `NP_Dem` | `dem_proximity`, `number`, `noun` | *ko jagua* | §3.4.2 |
| `NP_Art` | `number`, `noun` | *la jagua* (Spanish borrowing; article not rendered) | §3.4.1 |
| `NP_Adj` | `noun`, `adjective` | *jagua ñarõ* | §3.3 |
| `NP_Poss` | `poss_marker`, `noun` | *che juru* | §3.6 |
| `NP_Num` | `GuaraniNum`, `noun` | *mbohapy ryguasu* | §3.4.3 |
| `NP_Gen` | `guarani_np`, `noun` | *Maria ajaka* — full-NP possessor triggers r- form | §3.6 |
| `NP_DemPoss` | `dem_proximity`, `poss_marker`, `noun` | *ko che irũ* | §3.4.2 |
| `NP_Rel` | `noun`, `embedded_clause` | *kuña oikuaáva* — clause must carry `VS_NomVa` | §3.2.1.1.3, §12.2.1 |
| `NP_Comp` | `embedded_clause` | complement clause as noun — must carry `VS_NomHa` | §3.2.1.1.1, §12.2.2 |
| `NP_Suf` | `guarani_np`, `nominal_suffix` | NP + one suffix | §3.1.1, §3.7 |
| `NP_Suf2` | `guarani_np`, `nominal_suffix`, `nominal_suffix` | NP + two ordered suffixes; requires `suffix_pair_ok` | §3.7 |

**Pronoun NPs:**

| Constructor | Arguments | What it builds | §ref |
|-------------|-----------|----------------|------|
| `NP_PronSubj` | `subj_pronoun` | *che, nde, ha'e, ñande, ore, peẽ, ha'ekuéra* | §3.5.1 |
| `NP_PronPoss` | `poss_marker` | *chemba'e* = mine | §3.5.5 |
| `NP_PronDem` | `dem_proximity`, `number` | *kóva, péva, amóva, …* | §3.5.4 |
| `NP_PronIndef` | `indef_pron` | *maymáva, opáva, avave, …* | §3.5.3 |
| `NP_PronInterrog` | `interrog_pron` | *mba'e, máva, moõ, mbovy, …* | §3.5.2 |
| `NP_PronNeg` | `neg_pron` | *mba'eve, avave, mamove, …* | §3.5.3 |

**Coordination:**

| Constructor | Rule | §ref |
|-------------|------|------|
| `NP_CoordHa` | *NP ha NP* — always Plural; person merge 1st > 2nd > 3rd | §12.1 |
| `NP_CoordTera` | *NP tera NP* — or; inherits metadata from left conjunct | §12.1 |

### Postpositions (§5)

`postposition_form : orality -> postposition -> string`

| Constructor | Oral | Nasal | Meaning |
|-------------|------|-------|---------|
| `Post_Pe` | pe | me | in, at, to; marks [+human] direct objects |
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
| `is_noun_headed` on `NP_Suf` | Suffixes only on noun-headed NPs |
| `has_suffix` on `NP_Suf` | No stacking `NP_Suf` on `NP_Suf`; use `NP_Suf2` |
| `suffix_pair_ok` on `NP_Suf2` | Two-suffix sequence must be grammatical per §3.7 |
| `NP_Suf2` base check | Cannot wrap an already-suffixed NP |
| `NP_Rel` check | `wf_conjugated_verb` && clause carries `VS_NomVa` |
| `NP_Comp` check | `wf_conjugated_verb` && clause carries `VS_NomHa` |
| `NP_Gen` recursion | Possessor NP must be well-formed |
| Coordination recursion | Both conjuncts must be well-formed |

### Metadata inference (`np_meta_of`)

| NP form | Person | Number | Orality |
|---------|--------|--------|---------|
| `NP_Bare n` | Third | Singular | `n_orality n` |
| `NP_Dem _ num n` | Third | `num` | `n_orality n` |
| `NP_Poss pm n` | from `pm` | from `pm` | `n_orality n` |
| `NP_Num gn n` | Third | Singular if `is_one gn`, else Plural | `n_orality n` |
| `NP_Gen _ n` | Third | Singular | `n_orality n` |
| `NP_Suf x NS_Plural` | from `x` | Plural | from `x` |
| `NP_Suf x _` | from `x` | from `x` | from `x` (transparent) |
| `NP_PronSubj p` | from `p` | from `p` | Oral |
| `NP_CoordHa x1 x2` | merge(p1, p2) — 1st > 2nd > 3rd | Plural | from `x1` |
| `NP_CoordTera x1 _` | from `x1` | from `x1` | from `x1` |

`person_merge` is commutative, idempotent, First always dominates.

### Surface rendering (`render_np`)

`render_np : guarani_np -> string`

| Constructor | Output |
|-------------|--------|
| `NP_Bare n` | `noun_surface n PossCtx_None` |
| `NP_Dem prox num n` | `dem_adj_form prox num ++ " " ++ noun_surface n PossCtx_None` |
| `NP_Art _ n` | `noun_surface n PossCtx_None` — article dropped per project spec |
| `NP_Adj n a` | `noun_surface n PossCtx_None ++ " " ++ a_form a` |
| `NP_Poss pm n` | `poss_marker_form (n_orality n) pm ++ " " ++ noun_surface n (poss_context_of_marker pm)` |
| `NP_Num gn n` | `render_num gn ++ " " ++ noun_surface n PossCtx_None` |
| `NP_Gen poss n` | `render_np poss ++ " " ++ noun_surface n PossCtx_FirstSecond` |
| `NP_Rel n cv` | `noun_surface n PossCtx_None ++ " " ++ render_verb cv` |
| `NP_Comp cv` | `render_verb cv` |
| `NP_Suf inner suf` | `render_np inner ++ render_nom_suffix suf (np_orality (np_meta_of inner))` |
| `NP_PronSubj p` | `render_subj_pronoun p` |
| `NP_PronPoss pm` | `poss_marker_form Oral pm ++ "mba'e"` |
| `NP_PronDem prox num` | `dem_pron_form prox num` |
| `NP_CoordHa x1 x2` | `render_np x1 ++ " ha " ++ render_np x2` |
| `NP_CoordTera x1 x2` | `render_np x1 ++ " térã " ++ render_np x2` |

### Theorems (60 total)

| Rule group | Theorems | Grammar rule covered |
|------------|----------|---------------------|
| **NP-A** Root class prefixes | `rule_NPA1`–`rule_NPA7` (8) | t-/r-/h- for all 5 root classes; Uniform always empty; TriformNoT no t- §3.1.3 |
| **NP-B** Well-formedness | `rule_NPB1`–`rule_NPB8` (16) | Base NPs wf; single suffix wf; stacking blocked; suffix on pronoun blocked; gen preserves wf; NP_Rel needs VS_NomVa; NP_Comp needs VS_NomHa §3.1, §3.7, §3.2.1.1 |
| **NP-C** Suffix ordering | `rule_NPC1`–`rule_NPC7` (7) | -rã+kue valid; -kue+rã invalid; -ha+kue, -ha+rã, -py+kue, -py+rã valid; double plural invalid §3.7 |
| **NP-D** Subject pronoun metadata | `rule_NPD1`, `rule_NPD3` (2) | Person consistent; subject pronoun NP always Oral §3.5.1 |
| **NP-E** Bare noun metadata | `rule_NPE1`–`rule_NPE2` (2) | Bare noun NP always Third, Singular §3.1 |
| **NP-F** Plural allomorphy | `rule_NPF1`–`rule_NPF2` (2) | Nasal noun → nguéra; oral noun → kuéra §3.1.1 |
| **NP-G** Demonstrative system | `rule_NPG1`, `rule_NPG3`, `rule_NPG6` (3) | ko proximal singular form; ko'ã not umi for proximal plural; demonstrative NP always Third §3.4.2 |
| **NP-H** Suffix metadata effects | `rule_NPH1`, `rule_NPH4` (2) | NS_Plural forces Plural number; NS_PastKue is metadata-transparent §3.1.1, §3.7 |
| **NP-I** Genitive metadata | `rule_NPI1` (1) | Genitive NP always Third person §3.6 |
| **NP-J** Possessive NP metadata | `rule_NPJ1` (1) | Person from poss_marker §3.6 |
| **NP-K** Numeral NP metadata | `rule_NPK1`–`rule_NPK2` (2) | peteĩ → Singular; other numerals → Plural §3.4.3 |
| **NP-L** Coordination metadata | `rule_NPL1` (1) | ha-coordination NP always Plural §12.1 |
| **NP-M** `person_merge` | `rule_NPM1`, `rule_NPM3` (2) | Commutative; First always dominates |
| **NP-N** Postposition allomorphy | `rule_NPN1` (2) | pe (oral) / me (nasal) allomorphy of Post_Pe §5 |
| **NP-O** Negative pronouns | `rule_NPO1`–`rule_NPO2` (2) | avave is negative; maymáva is not §3.5.3 |
| **NP-P** Interrogative rendering | `rule_NPP2` (1) | Interrogative pronoun NP always Third person §3.5.2 |
| **NP-Q** Rendering | `rule_NPQ1`–`rule_NPQ6` (6) | Uniform bare = root; NP_Art drops article; ha-coord uses "ha"; NP_Rel = noun + verb; NP_Comp = verb |

---

## Verb.v

Complete verb morphology: conjugation classes, transitivity, voice, mood, evidentiality, negation, tense/aspect/mood suffixes, person hierarchy for transitives, relational verb roots, irregular verbs, suffix ordering, and well-formedness.

### Types

| Type | Constructors | What it encodes | §ref |
|------|-------------|-----------------|------|
| `verb_class` | `Areal`, `Aireal`, `Chendal` | Three conjugation classes: standard active (a/re/o), glottal-initial active (ai/rei/oi), inactive/stative (che/nde/i) | §4.1–4.2 |
| `transitivity` | `Intransitive`, `Transitive`, `Ditransitive`, `PostpComplement` | Argument structure; Chendal must be Intransitive | §4.1–4.4 |
| `verb_root_class` | `VRoot_Plain`, `VRoot_Relational` | Whether the root has h-/r- alternation | §4.6 |
| `chendal_3sg_form` | `C3sg_I`, `C3sg_Hi`, `C3sg_Ij` | Chendal 3rd-person allomorphs: i-/iñ- (default), hi-/hiñ- (common), ij-/iñ- (before vowel roots) | §4.1.2 |
| `prefix_type` | `PfxActive`, `PfxInactive`, `PfxImperative`, `PfxPortmanteau` | Context for relational root prefix selection | §4.6 |
| `voice` | `Active`, `Passive`, `Reciprocal`, `Coactive`, `Objective`, `Obj_Guero`, `Subsuntive` | Seven grammatical voices; `Obj_Guero` = guero- variant of sociative causative | §6, §17.2 |
| `mood` | `Indicative`, `Imperative`, `Optative`, `Prohibitive` | Four moods | §4.10.3 |
| `polarity` | `Positive`, `Negative` | Sentence polarity; Negative requires negation circumfix | §4.9 |
| `niko_variant` | `NK_Niko`, `NK_Ko`, `NK_Ngo`, `NK_Ningo` | Four free-variant surface forms of the =niko veridical clitic | §7.1 |
| `evidential_marker` | 11 constructors (see below) | Evidential clitics and markers | §7 |
| `evidential` | record: `ev_marker`, `ev_niko_v` | Packed evidential with optional niko surface variant | §7 |
| `verbal_suffix` | 31 constructors (see below) | Full set of verbal suffixes | §4.9–4.10, §7.2, §12.2.3.1, §14 |
| `portmanteau_config` | `Port_1to2sg`, `Port_1to2pl` | 1st→2sg (ro-) and 1st→2pl (po-) portmanteau prefixes | §4.2 |
| `trans_prefix_mode` | `TPM_Active`, `TPM_Inactive`, `TPM_Portmanteau`, `TPM_Reflexive` | Person-hierarchy selection result | §4.2 |
| `irregular_verb` | `Irreg_Ju`, `Irreg_Ho`, `Irreg_E` | Irregular verbs: *ju* (come), *ho* (go), *'e* (say) | §4.5 |
| `verb` | record | `v_class`, `v_orality`, `v_root`, `v_transitivity`, `v_root_class`, `v_chendal_3sg` | — |
| `verb_form` | `VF_Regular verb`, `VF_Irregular irregular_verb` | Dispatch type; callers use `render_verb` only | — |
| `conjugated_verb` | record | `cv_verb_form`, `cv_person`, `cv_number`, `cv_incl`, `cv_mood`, `cv_polarity`, `cv_voice`, `cv_suffixes`, `cv_evidential` | — |

### Evidential marker system (§7)

`cv_evidential : option evidential` — optional field on `conjugated_verb`. Most evidentials are clitics with free distribution; `-je` is a verb suffix modeled as `VS_HearsayJe`.

| Constructor | Surface | Type | §ref |
|-------------|---------|------|------|
| `Ev_Voi` | voi | Emphatic | §7.1 |
| `Ev_Niko` | niko/ko/ngo/ningo | Veridical emphatic (4 free variants via `niko_variant`) | §7.1 |
| `Ev_Ndaje` | ndaje | Hearsay clitic | §7.2 |
| `Ev_Jeko` | jeko | Hearsay clitic | §7.2 |
| `Ev_NandEko` | ñandeko | Hearsay clitic | §7.2 |
| `Ev_Kuri` | kuri | Direct evidence / recent past — requires Indicative mood | §7.3 |
| `Ev_Rae` | ra'e | Recent inference / mirative | §7.4 |
| `Ev_Rakae` | raka'e | Distant inference | §7.4 |
| `Ev_MboRae` | mbora'e | Uncertain inference (mbo + ra'e) | §7.4 |
| `Ev_Nipo` | nipo | Uncertainty / counterexpectation | §7.4 |
| `Ev_Hina` | hína | Progressive / emphatic | §4.10.2, §7.1 |

`render_evidential` appended to base verb form by `render_verb`. `cv_evidential_ok` enforces that `Ev_Kuri` requires Indicative mood.

### Verbal suffix system (§4.9–4.10, §7.2, §12.2.3.1, §14)

31 constructors:

| Slot | Constructor(s) | Surface form | Category |
|------|---------------|-------------|----------|
| 1 | `VS_CausUka` | -uka | Causative of transitive §6.6.3 |
| 2 | `VS_AbilKuaa` | -kuaa | Ability §4.10.3.2 |
| 3 | `VS_TotalPa` | -pa/-mba | Totalitative §4.10.2 |
| 4 | `VS_ImpForce`, `VS_ImpRequest`, `VS_ImpPlead`, `VS_ImpUrge` | -ke, -na, -mi, -py | Imperative modalizers §4.10.3.1.2 |
| 5 | `VS_Volitive` | -se | Want to §4.10.3.4.1 |
| 6 | `VS_ComparVe` | -ve | Comparative |
| 7 | `VS_FutTa`, `VS_FutNe`, `VS_FutNegMoa`, `VS_ImmFutPota`, `VS_ObligVaera`, `VS_PastVaekue` | -ta, -ne, -mo'ã, -pota/-mbota, -va'erã, -va'ekue | Tense §4.10.1 |
| 8 | `VS_NegI`, `VS_NegRi`, `VS_NegTei`, `VS_Privative` | -i, -ri, -tei, -'ỹ | Negation §4.9, §4.10.3.1.3 |
| 9 | `VS_Intensifier` | -ite/-ete | Intensifier |
| 10 | `VS_NomVa`, `VS_NomHa` | -va, -ha | Nominalizers §3.2.1.1 |
| 11 | `VS_AspectMa`, `VS_IterJevy`, `VS_HabitMi`, `VS_HabitVa`, `VS_FrustrRei`, `VS_Desiderative`, `VS_Simultaneous` | -ma, -jevy, -mi, -va, -rei, -nga'u, -vo | Aspect/mood; -vo = simultaneous subordinator §12.2.3.1 |
| 12 | `VS_InterrogPa` | -pa | Interrogative clitic §8.5 |
| 13 | `VS_HearsayJe` | -je | Hearsay evidential suffix §7.2 |

### Agreement prefix tables

**`areal_ind_prefix`** (§4.1.1):

| Person/Number | Oral | Nasal |
|---|---|---|
| 1sg | a | a |
| 2sg | re | re |
| 3 | o | o |
| 1pl inclusive | ja | ña |
| 1pl exclusive | ro | ro |
| 2pl | pe | pe |

**`aireal_ind_prefix`** (§4.2): 1sg → ai, 2sg → rei, 3 → oi, 1pl.incl → jai/ñai, 1pl.excl → roi, 2pl → pei.

**`chendal_ind_prefix`** (§4.1.2) — takes `chendal_3sg_form` argument:

| Person/Number | C3sg_I oral | C3sg_Hi oral | C3sg_Ij oral | Nasal |
|---|---|---|---|---|
| 1sg | che | che | che | che |
| 2sg | nde | nde | nde | ne |
| 3 | i | hi | ij | iñ / hiñ / iñ |
| 1pl inclusive | ñande | ñande | ñande | ñane |
| 1pl exclusive | ore | ore | ore | ore |
| 2pl | pende | pende | pende | pene |

### Voice prefix rendering (§6)

| Voice | Oral | Nasal | Notes |
|-------|------|-------|-------|
| `Active` | "" | "" | — |
| `Passive` | je | ñe | — |
| `Reciprocal` | jo | ño | — |
| `Coactive` | mbo | mo | — |
| `Objective` | ro | ro | sociative causative |
| `Obj_Guero` | guero | guero | variant of Objective; invariant across orality §17.2 |
| `Subsuntive` | poro | poro | — |

### Relational verb roots (§4.6)

`h-` with Active/Imperative/Portmanteau; `r-` with Inactive. `VRoot_Plain` always `""`.

### Negation circumfix (§4.9)

Prefix: `neg_prefix_for` → `"nd"` (Oral), `"n"` (Nasal).
Eufonic vowel: `neg_eufonic` — Chendal always `"a"`; active verbs match agreement prefix vowel.
`VS_FutNegMoa` replaces `VS_FutTa` in negative future; they cannot co-occur.

### Person hierarchy (§4.2)

| Subject | Object | Mode |
|---------|--------|------|
| 1st | 2sg | `TPM_Portmanteau Port_1to2sg` (ro-) |
| 1st | 2pl | `TPM_Portmanteau Port_1to2pl` (po-) |
| 1st | 3rd | `TPM_Active` |
| 2nd/3rd | 1st | `TPM_Inactive` |
| 3rd | 2nd | `TPM_Inactive` |
| 3rd | 3rd | `TPM_Active` |
| same person (non-3rd) | — | `TPM_Reflexive` |

### Irregular verb paradigms (§4.5)

| Person | *ju* (come) | *ho* (go) | *'e* (say) |
|--------|------------|----------|-----------|
| 1sg | aju | aha | ha'e |
| 2sg | reju | reho | ere |
| 3 | ou | oho | he'i |
| 1pl.incl | jaju | jaha | ja'e |
| 1pl.excl | roju | roho | ro'e |
| 2pl | peju | peho | peje |

### Rendering

`render_verb : conjugated_verb -> string`
Dispatches on `cv_verb_form`; appends evidential clitic from `cv_evidential` if present.

`render_regular_verb`: (prohibitive *ani*) ++ neg_prefix ++ agr_prefix ++ voice_prefix ++ relational_prefix ++ root ++ suffixes.

### Well-formedness (`wf_conjugated_verb`)

Conjunction of 12 named predicates:

| Predicate | Constraint | §ref |
|-----------|-----------|------|
| `cv_structure_ok` | Chendal must be Intransitive | §4.1.2 |
| `cv_neg_ok` | Polarity ↔ neg suffix presence | §4.9 |
| `cv_incl_ok` | 1pl requires `Some inclusivity`; others require `None` | §4.1.1 |
| `cv_tense_ok` | At most one future marker; `VS_FutNegMoa` requires Negative | §4.10.1 |
| `cv_neg_count_ok` | At most one negation suffix | §4.9 |
| `cv_modalizer_ok` | Imperative modalizers only in Imperative/Optative | §4.10.3.1.2 |
| `cv_mood_neg_ok` | Prohibitive requires Negative and forbids -i/-ri; Optative forbids -i/-ri | §4.10.3.1.3 |
| `cv_class_mood_ok` | Chendal cannot be Imperative or Optative | §4.1.2 |
| `cv_homophone_ok` | Interrog -pa ≠ totalitative -pa; habitual -mi ≠ pleading -mi | §4.10 |
| `no_dup_suffixes` | No suffix appears twice | — |
| `suffixes_ordered` | Suffix slots non-decreasing left to right | §14 |
| `cv_evidential_ok` | `Ev_Kuri` requires Indicative mood | §7.3 |

### Theorems (100 total)

| Rule group | Theorems | Grammar rule covered |
|------------|----------|---------------------|
| **A** Areal prefixes | `rule_A1`–`rule_A6` (7) | Full paradigm §4.1.1 |
| **B** Aireal prefixes | `rule_B1`–`rule_B6` (7) | ai/rei/oi/jai(ñai)/roi/pei §4.2 |
| **C** Chendal prefixes | `rule_C1`–`rule_C6`, `rule_C3b`, `rule_C3c` (12) | che/nde/i/ñande/ore/pende; hi- allomorph oral/nasal; ij- allomorph oral/nasal §4.1.2 |
| **D** Imperative prefix | `rule_D1`–`rule_D3` (4) | e- for 2sg Areal/Aireal only §4.10.3.1.1 |
| **E** Optative prefix | `rule_E1`–`rule_E3` (3) | ta/to/tape; Chendal gets ta+inactive §4.10.3.4.2 |
| **F** Voice prefixes | `rule_F1`–`rule_F6`, `rule_F5b` (9) | All seven voices; guero- invariant; guero- ≠ ro- §6, §17.2 |
| **G** Negation circumfix | `rule_G1`–`rule_G6` (7) | nd/n; eufonic vowels; Chendal always a; neg requires suffix §4.9 |
| **H** Future negation | `rule_H1`–`rule_H3` (3) | -ta and -mo'ã exclusive; -mo'ã requires Negative §4.9 |
| **I** Person hierarchy | `rule_I1`–`rule_I9` (5) | Selected `trans_prefix_selection` cases (active/inactive/portmanteau) §4.2 |
| **J** Relational root | `rule_J1`–`rule_J5` (3) | h- relational active prefix; r- relational inactive prefix; plain root always empty §4.6 |
| **K** Irregular verbs | `rule_K1`–`rule_K5` (5) | Selected forms of ju/ho/'e §4.5 |
| **L** Inclusivity | `rule_L1`–`rule_L2` (2) | 1pl requires; non-1pl forbids §4.1.1 |
| **M** Suffix exclusion | `rule_M1`–`rule_M3` (3) | No double future; -mi exclusive; -pa exclusive §4.10 |
| **N** Prohibitive | `rule_N1`–`rule_N2` (2) | Requires Negative; cannot use -i §4.10.3.1.3 |
| **O** Imperative modalizers | `rule_O1` (1) | Blocked in Indicative §4.10.3.1.2 |
| **P** Affix ordering | `rule_P1`, `rule_P4`, `rule_P8`–`rule_P14` (8) | Valid/invalid orderings; -je last; -vo in slot 11 §14 |
| **Q** Chendal structure | `rule_Q1`–`rule_Q3` (3) | No Transitive; Intransitive ok; Areal any §4.1.2 |
| **R** Chendal mood | `rule_R1`–`rule_R4` (4) | No Imperative/Optative §4.1.2 |
| **S** Future exclusivity | `rule_S1`–`rule_S2` (2) | No -ta+-pota; single future ok §4.10.1 |
| **T** General wf | `rule_T1`–`rule_T3` (3) | No dup suffixes; bare positive verb wf; empty render §14 |
| **EV** Evidentiality | `rule_EV1`–`rule_EV7` (7) | kuri requires Indicative; voi any mood; niko 4 variants; kuri/ra'e/raka'e render; -je renders §7 |

---

## Sentences.v

Sentence-level well-formedness for verbal sentences. Imports `NounPhrases.v` and `Verb.v`.

### Sentence types

```
Inductive word_order : Type :=
  | WO_SVO | WO_SOV | WO_VSO | WO_VOS | WO_OSV | WO_OVS.

Inductive sentence_type : Type :=
  | ST_Declarative | ST_Interrog_YN | ST_Interrog_Content
  | ST_Imperative  | ST_Prohibitive.
```

### `simple_sentence` record

| Field | Type | Description |
|-------|------|-------------|
| `ss_subject` | `option guarani_np` | Null subject allowed (pro-drop) |
| `ss_verb` | `conjugated_verb` | The main verb |
| `ss_dir_obj` | `option guarani_np` | Direct object |
| `ss_indir_obj` | `option guarani_np` | Indirect object (full NP, not pronoun enum) |
| `ss_postp_obj` | `option (guarani_np * postposition)` | Postpositional complement |
| `ss_order` | `word_order` | Surface word order |
| `ss_type` | `sentence_type` | Sentence type |
| `ss_interrog` | `option interrog_particle` | =pa or =piko |
| `ss_hikuai` | `bool` | Whether *hikuái* follows verb |

### Well-formedness predicates

`wf_sentence` = conjunction of all 8:

| Predicate | Rule | Constraint | §ref |
|-----------|------|-----------|------|
| `ss_agree_ok` | A | Subject NP person/number/inclusivity must match verb; null subject always ok | §8.1 |
| `ss_transitivity_ok` | B | Arguments must match verb transitivity; IO without DO on Ditransitive is ill-formed | §4.1–4.4 |
| `ss_hierarchy_ok` | C | When subject and object explicit on Transitive verb, prefix must follow 1 > 2 > 3 | §4.2 |
| `ss_neg_concord_ok` | D | Negative pronoun in subject, DO, or IO requires Negative verb polarity | §4.9, §3.5.3 |
| `ss_hikuai_ok` | E | *hikuái* flag requires 3rd person verb and V-initial word order | §4.1.1 |
| `ss_type_ok` | F | Sentence type and verb mood must be consistent | §4.10.3 |
| `ss_human_pe_ok` | G | [+human] postpositional complement NP requires `Post_Pe` | §5.1 |
| `wf_conjugated_verb` | — | All 12 verb-internal constraints from Verb.v | — |

### Adverbial clause types (§12.2.3)

`adv_clause_type` — 16 constructors:

| Constructor | Subordinator(s) | §ref |
|-------------|----------------|------|
| `AC_Purposive` | =haguã | §12.2.3.1 |
| `AC_PurpNeg` | ani haguã | §12.2.3.1 |
| `AC_PurpSimult` | -vo (movement verb) | §12.2.3.1 |
| `AC_Concessive` | ramo jepe | §12.2.3.2 |
| `AC_ConcessPotential` | jepe (+ optative on subord) | §12.2.3.2 |
| `AC_Causal_Gui` | =gui | §12.2.3.3 |
| `AC_Causal_Rehe` | =rehe / =re | §12.2.3.3 |
| `AC_Causal_Rupi` | =rupi | §12.2.3.3 |
| `AC_Causal_Porque` | porque (Spanish borrowing) | §12.2.3.3 |
| `AC_Cond_Hyp` | =rõ or =ramo (free variation) | §12.2.3.4 |
| `AC_Cond_Counter` | =rire on subord clause | §12.2.3.4 |
| `AC_Manner` | -ha-icha / -hague-icha (past) | §12.2.3.5 |
| `AC_Temp_Simult` | =ramo/=rõ (stressed) / -vo / aja / jave | §12.2.3.6 |
| `AC_Temp_Ant` | mboyve | §12.2.3.6 |
| `AC_Temp_Post` | rire (stressed) / vove | §12.2.3.6 |
| `AC_Locative` | -ha + postposition | §12.2.3.7 |

`wf_adv_clause` checks that `ac_subord` matches the expected morpheme(s) for its type.

`CS_Counterfactual` is a separate complex sentence constructor (not `CS_Adverbial`) because the main clause must additionally carry both `VS_ObligVaera` and `VS_FutNegMoa`.

### Non-verbal sentences (§8.2–8.4)

Lightweight wrappers: `NVS_Equative`, `NVS_Predicative`, `NVS_Existential`, `NVS_Possessive`. `wf_nonverbal` delegates to `wf_np` on constituent NPs.

### Theorems (38 total)

| Rule group | Theorems | Grammar rule covered |
|------------|----------|---------------------|
| **SA** Subject-verb agreement | `rule_SA1`–`rule_SA4` (4) | Null subject ok; matching ok; mismatch bad; incl/excl mismatch bad §8.1 |
| **ST** Transitivity | `rule_ST1`–`rule_ST3`, `rule_ST7`–`rule_ST8` (5) | Intransitive no args; intransitive+obj bad; transitive+obj ok; IO-without-DO bad; ditransitive+both ok §4.1–4.4 |
| **SH** Person hierarchy | `rule_SH1`–`rule_SH2` (2) | Partial args pass; intransitive skips §4.2 |
| **SN** Double negation | `rule_SN1`–`rule_SN3` (3) | avave+pos bad; avave+neg ok; negative IO triggers neg-concord §4.9, §3.5.3 |
| **SK** Hikuái placement | `rule_SK1`–`rule_SK2`, `rule_SK4` (3) | No hikuái always ok; 1sg+hikuái bad; VSO+3rd+hikuái ok §4.1.1 |
| **SP** Human =pe/=me | `rule_SP1`–`rule_SP2` (2) | Human NP + Post_Pe ok; human NP + wrong postposition bad §5.1 |
| **SY** Sentence type/mood | `rule_SY1`, `rule_SY3` (2) | Declarative needs Indicative; YN needs particle §4.10.3 |
| **AC** Adverbial clauses | `rule_AC1`–`rule_AC13` (13) | All 16 clause types; correct/incorrect morphemes; counterfactual needs va'erã-mo'ã §12.2.3 |
| **CX** Complex sentences | `rule_CX1`–`rule_CX2`, `rule_TL1` (3) | Adverbial ok with correct morpheme; bad with wrong; simple lifts |

