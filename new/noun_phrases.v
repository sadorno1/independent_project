From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import Primitives.
Require Import Numbers.

(* ============================================================ *)
(*  NounPhrases.v                                               *)
(*  Guaraní noun phrase grammar: nouns, adjectives, pronouns,   *)
(*  demonstratives, determiners, postpositions, nominalizing     *)
(*  suffixes, relative and complement clauses, well-formedness,  *)
(*  metadata inference, and rendering.                          *)
(*                                                              *)
(*  Primary reference: "A Grammar of Paraguayan Guarani"        *)
(*  Chapter 3 (Nominals), Chapter 5 (Postpositions)             *)
(* ============================================================ *)


(* ============================================================ *)
(*  1. Root classes                                             *)
(*  §3.1.3 "Relational (multiform) nominal roots"              *)
(*                                                              *)
(*  Many nouns (and some verbs/adjectives) have an initial      *)
(*  consonant that changes depending on possessive context:     *)
(*    t- = non-possessed / absolute                             *)
(*    r- = possessed by 1st/2nd person or a full NP possessor   *)
(*    h- = possessed by 3rd person pronominal possessor         *)
(*                                                              *)
(*  Example: tova (a face), rova (my/your/X's face),            *)
(*           hova (his/her/their face)                          *)
(* ============================================================ *)

Inductive root_class : Type :=
  | Uniform       (* no alternation: jagua is always jagua *)
  | Triform       (* t-/r-/h-: tova, rova, hova *)
  | TriformNoT    (* no t- form: óga, róga, hóga *)
  | Biform        (* túva/ru: kinship terms with i- for 3rd *)
  | Quadriform.   (* to'o/ro'o/ho'o/so'o: inalienable vs alienable *)

(* Possessive context determines which root form to use *)
Inductive poss_context : Type :=
  | PossCtx_None           (* non-possessed: uses t- form *)
  | PossCtx_FirstSecond    (* 1st/2nd person or NP possessor: uses r- form *)
  | PossCtx_Third.         (* 3rd person pronominal: uses h- form *)

(* Given a root class and possessive context, select the prefix.
   For Uniform roots this is always empty.
   For Triform: t- / r- / h-
   For TriformNoT: (none) / r- / h-
   For Biform: full absolute form is used differently (handled in rendering)
   For Quadriform: t- / r- / h- plus an irregular 4th form (not modeled here)

   §3.1.3: "tova (face) -> che rova (my face) -> hova (his face)"
   §3.1.3: "óga (house) -> che róga (my house) -> hóga (his house)"
   §3.1.3: "túva (father) -> che ru (my father) -> itúva (his father)" *)

Definition root_prefix (rc : root_class) (ctx : poss_context) : string :=
  match rc, ctx with
  | Uniform,    _                 => ""
  | Triform,    PossCtx_None      => "t"
  | Triform,    PossCtx_FirstSecond => "r"
  | Triform,    PossCtx_Third     => "h"
  | TriformNoT, PossCtx_None      => ""
  | TriformNoT, PossCtx_FirstSecond => "r"
  | TriformNoT, PossCtx_Third     => "h"
  | Biform,     PossCtx_None      => ""   (* absolute form is a separate word *)
  | Biform,     PossCtx_FirstSecond => "r"
  | Biform,     PossCtx_Third     => ""   (* uses i- prefix separately *)
  | Quadriform, PossCtx_None      => "t"
  | Quadriform, PossCtx_FirstSecond => "r"
  | Quadriform, PossCtx_Third     => "h"
  end.

(* ============================================================ *)
(*  2. Nouns                                                    *)
(*  §3.1 "Nouns are often defined as words that identify        *)
(*  people, places or things."                                  *)
(* ============================================================ *)

Record noun : Type := mkNoun {
  n_root       : string;     (* bare root without relational prefix *)
  n_orality    : orality;
  n_ending     : word_ending;
  n_root_class : root_class
}.

(* Convenience: surface form of a noun in a given possessive context *)
Definition noun_surface (n : noun) (ctx : poss_context) : string :=
  root_prefix (n_root_class n) ctx ++ n_root n.

(* ============================================================ *)
(*  3. Adjectives                                               *)
(*  §3.3 "Adjectival modifiers of the noun"                     *)
(*                                                              *)
(*  Adjectives follow the noun: "óga porã" = beautiful house    *)
(*  Some adjectives are relational roots and take r- when       *)
(*  modifying a noun: "tesa rovy" = blue eyes                   *)
(*  §3.3: "most roots that can be used as adjectives do so      *)
(*  without any specific marking"                               *)
(* ============================================================ *)

Record adjective : Type := mkAdj {
  a_form       : string;
  a_orality    : orality;
  a_root_class : root_class    (* some adjectives are relational *)
}.

(* ============================================================ *)
(*  4. Subject pronouns                                         *)
(*  §3.5.1 "Free-standing personal pronoun forms"               *)
(*                                                              *)
(*  che (I), nde (you.sg), ha'e (he/she),                       *)
(*  ñande (we.incl), ore (we.excl),                             *)
(*  peẽ (you.pl), ha'ekuéra (they)                              *)
(* ============================================================ *)

Inductive subj_pronoun : Type :=
  | Subj1SG | Subj2SG | Subj3SG
  | Subj1PL_INCL | Subj1PL_EXCL | Subj2PL | Subj3PL.

Definition render_subj_pronoun (p : subj_pronoun) : string :=
  match p with
  | Subj1SG      => "che"
  | Subj2SG      => "nde"
  | Subj3SG      => "ha'e"
  | Subj1PL_INCL => "ñande"
  | Subj1PL_EXCL => "ore"
  | Subj2PL      => "peẽ"
  | Subj3PL      => "ha'ekuéra"
  end.

(* ============================================================ *)
(*  5. Demonstratives                                           *)
(*  §3.4.2 "Demonstratives are morphemes that help to           *)
(*  identify a referent by locating it in space or time"         *)
(*                                                              *)
(*  Two sets: co-present (visible) and removed (absent).        *)
(*                                                              *)
(*  Co-present:                                                 *)
(*    ko / ko'ã  — proximal to speaker                          *)
(*    pe / upe   — proximal to hearer (medial)                  *)
(*    amo        — distal to both                               *)
(*                                                              *)
(*  Removed:                                                    *)
(*    ku         — shared knowledge, mainly persons              *)
(*    ako        — shared knowledge, distant events              *)
(*    aipo       — no direct knowledge, hearsay                  *)
(*                                                              *)
(*  Plural: ã/ko'ã (proximal), umi (all others)                 *)
(* ============================================================ *)

Inductive dem_set : Type :=
  | DemPresent     (* referent is visible / co-present *)
  | DemRemoved.    (* referent is absent / in memory *)

Inductive dem_proximity : Type :=
  (* Co-present *)
  | DemProxSpeaker     (* ko — this, near me *)
  | DemProxHearer      (* pe, upe — that, near you *)
  | DemDistal          (* amo — that, over there *)
  (* Removed *)
  | DemSharedPerson    (* ku — that person we both know *)
  | DemSharedEvent     (* ako — that event we both know *)
  | DemHearsay.        (* aipo — that thing I heard about *)

Definition dem_set_of (prox : dem_proximity) : dem_set :=
  match prox with
  | DemProxSpeaker  => DemPresent
  | DemProxHearer   => DemPresent
  | DemDistal       => DemPresent
  | DemSharedPerson => DemRemoved
  | DemSharedEvent  => DemRemoved
  | DemHearsay      => DemRemoved
  end.

(* §3.4.2: demonstrative adjective forms (precede the noun) *)
Definition dem_adj_form (prox : dem_proximity) (n : number) : string :=
  match prox, n with
  | DemProxSpeaker,  Singular => "ko"
  | DemProxSpeaker,  Plural   => "ko'ã"
  | DemProxHearer,   Singular => "pe"
  | DemProxHearer,   Plural   => "umi"
  | DemDistal,       Singular => "amo"
  | DemDistal,       Plural   => "umi"
  | DemSharedPerson, Singular => "ku"
  | DemSharedPerson, Plural   => "umi"
  | DemSharedEvent,  Singular => "ako"
  | DemSharedEvent,  Plural   => "umi"
  | DemHearsay,      Singular => "aipo"
  | DemHearsay,      Plural   => "umi"
  end.

(* §3.5.4: demonstrative pronoun forms (standalone, formed with -va)
   §3.2.1.1.3: "-va can also function as a nominalizer to create
   demonstrative pronouns kó(v)a, pé(v)a, upé(v)a" *)
Definition dem_pron_form (prox : dem_proximity) (n : number) : string :=
  match prox, n with
  | DemProxSpeaker,  Singular => "kóva"
  | DemProxSpeaker,  Plural   => "ko'ãva"
  | DemProxHearer,   Singular => "péva"
  | DemProxHearer,   Plural   => "umíva"
  | DemDistal,       Singular => "amóva"
  | DemDistal,       Plural   => "umíva"
  | DemSharedPerson, Singular => "ku"
  | DemSharedPerson, Plural   => "umíva"
  | DemSharedEvent,  Singular => "ako"
  | DemSharedEvent,  Plural   => "umíva"
  | DemHearsay,      Singular => "aipóva"
  | DemHearsay,      Plural   => "umíva"
  end.

(* ============================================================ *)
(*  6. Indefinite pronouns                                      *)
(*  §3.5.3 "Indefinite pronouns refer to non-specific objects,  *)
(*  people, events or places."                                  *)
(* ============================================================ *)

Inductive indef_pron : Type :=
  | Indef_Maymava     (* maymáva — everyone, everything *)
  | Indef_Opava       (* opáva — everyone, all *)
  | Indef_Avave       (* avave — nobody — requires double negation *)
  | Indef_Mbaeve      (* mba'eve — nothing — requires double negation *)
  | Indef_Oimeraeva   (* oimeraẽva — anyone, whatever *)
  | Indef_Mokoive     (* mokõive — both *)
  | Indef_Ambueva     (* ambuéva — other one *)
  | Indef_PeteiMbae.  (* peteĩ mba'e — something *)

Definition render_indef_pron (i : indef_pron) : string :=
  match i with
  | Indef_Maymava   => "maymáva"
  | Indef_Opava     => "opáva"
  | Indef_Avave     => "avave"
  | Indef_Mbaeve    => "mba'eve"
  | Indef_Oimeraeva => "oimeraẽva"
  | Indef_Mokoive   => "mokõive"
  | Indef_Ambueva   => "ambuéva"
  | Indef_PeteiMbae => "peteĩ mba'e"
  end.

(* §3.5.3: negative pronouns require double negation on the verb.
   This predicate identifies which indefinite pronouns are negative. *)
Definition is_negative_pron (i : indef_pron) : bool :=
  match i with
  | Indef_Avave  => true
  | Indef_Mbaeve => true
  | _            => false
  end.

(* ============================================================ *)
(*  7. Interrogative pronouns                                   *)
(*  §3.5.2 "Interrogative pronouns are used to ask a question   *)
(*  whose answer is not simply 'yes' or 'no'"                   *)
(*                                                              *)
(*  Most are compositional:                                     *)
(*    mba'éicha = mba'e + -icha (like what? = how?)             *)
(*    mba'erã   = mba'e + -rã (for what? = what for?)           *)
(*    mba'ére   = mba'e + =re (because of what? = why?)         *)
(*    mba'égui  = mba'e + =gui (from what? = why?)              *)
(*  They often co-occur with =pa or =piko.                      *)
(* ============================================================ *)

Inductive interrog_pron : Type :=
  | Interrog_Mbae       (* mba'e — what *)
  | Interrog_Mava       (* máva / ava — who *)
  | Interrog_Mbaeicha   (* mba'éicha — how *)
  | Interrog_Mamo       (* mamo / moõ — where *)
  | Interrog_Arakae     (* araka'e — when *)
  | Interrog_Mbaera     (* mba'erã — what for *)
  | Interrog_Mbaere     (* mba'ére — why (because of) *)
  | Interrog_Mbaegui    (* mba'égui — why (from) *)
  | Interrog_Mbovy      (* mbovy — how many *)
  | Interrog_Avambae.   (* avamba'e — whose *)

Definition render_interrog_pron (i : interrog_pron) : string :=
  match i with
  | Interrog_Mbae     => "mba'e"
  | Interrog_Mava     => "máva"
  | Interrog_Mbaeicha => "mba'éicha"
  | Interrog_Mamo     => "moõ"
  | Interrog_Arakae   => "araka'e"
  | Interrog_Mbaera   => "mba'erã"
  | Interrog_Mbaere   => "mba'ére"
  | Interrog_Mbaegui  => "mba'égui"
  | Interrog_Mbovy    => "mbovy"
  | Interrog_Avambae  => "avamba'e"
  end.

(* ============================================================ *)
(*  8. Negative pronouns and adverbial proforms                 *)
(*  §3.5.3 "Negative pronouns are indefinite pronouns that      *)
(*  include negation. Most carry the ending -ve."               *)
(*                                                              *)
(*  All negative pronouns require double negation on the verb.  *)
(*  E.g: "Avave ndoikuaái cheréra" = Nobody knows my name      *)
(*  (literally: nobody doesn't-know my name)                    *)
(* ============================================================ *)

Inductive neg_pron : Type :=
  | NegPron_Mbaeve     (* mba'eve — nothing *)
  | NegPron_Avave      (* avave — nobody *)
  | NegPron_NiPetei    (* ni peteĩ — not one, none *)
  | NegPron_Mamove     (* mamove — nowhere *)
  | NegPron_Arakeve    (* araka'eve — never *)
  | NegPron_Maramo.    (* máramo — never *)

Definition render_neg_pron (np : neg_pron) : string :=
  match np with
  | NegPron_Mbaeve  => "mba'eve"
  | NegPron_Avave   => "avave"
  | NegPron_NiPetei => "ni peteĩ"
  | NegPron_Mamove  => "mamove"
  | NegPron_Arakeve => "araka'eve"
  | NegPron_Maramo  => "máramo"
  end.

(* ============================================================ *)
(*  9. Nominal suffixes                                         *)
(*  §3.1.1 plural, §3.7 temporal-aspectual, §3.2.2 negation,   *)
(*  §3.2.3 diminutives and attenuatives, §2.2.1 degree          *)
(*                                                              *)
(*  SUFFIX ORDERING (§3.7):                                     *)
(*    -rã (destinative) + -kue (post-stative) is VALID          *)
(*      "cherogarãngue" = my former future house (frustrative)  *)
(*    -kue + -rã is ALWAYS INVALID                              *)
(*      *"cherogakuerã" does not exist                          *)
(*                                                              *)
(*  This means we must allow ordered pairs of suffixes,         *)
(*  not just "at most one."                                     *)
(* ============================================================ *)

Inductive nominal_suffix : Type :=
  (* Plural marking §3.1.1 *)
  | NS_Plural        (* =kuéra / =nguéra — countable plural *)
  | NS_Multitude     (* =eta / =ita — large quantity, uncountable *)
  | NS_Collective    (* -ty / -ndy — abundance of plants/objects *)
  (* Temporal-aspectual §3.7 *)
  | NS_PastKue       (* -kue / -ngue — post-stative: was-but-no-longer *)
  | NS_FutureRa      (* -rã — destinative: will-be, prospective *)
  (* Degree §2.2.1.d *)
  | NS_ComparVe      (* -ve — comparative *)
  | NS_Super         (* -ite / -ete — superlative *)
  (* Derivational §3.2.2, §3.2.3 *)
  | NS_Privative     (* -'ỹ — absence/negation: vy'a > vy'a'ỹ *)
  | NS_Diminutive    (* -'i / -mi — small size or affection *)
  | NS_Attenuative   (* -vy / -ngy — less intense *)
  (* Nominalizing §3.2.1.1 *)
  | NS_NomHA         (* -ha — general nominalizer / subordinator *)
  | NS_NomVA         (* -va — adjectivizer / relativizer *)
  | NS_NomPY         (* -py / -mby — passive nominalizer *)
  | NS_NomKue        (* -kue (abstract nominalizer, distinct from temporal) *)
  (* Ordinal §3.4.3 *)
  | NS_OrdinalHA.    (* -ha — ordinal suffix: peteĩha = first *)

(* Render nominal suffix surface form *)
Definition render_nom_suffix (s : nominal_suffix) (o : orality) : string :=
  match s with
  | NS_Plural     => match o with Oral => "kuéra" | Nasal => "nguéra" end
  | NS_Multitude  => "eta"     (* =eta/=ita chosen by vowel class, simplified *)
  | NS_Collective => match o with Oral => "ty" | Nasal => "ndy" end
  | NS_PastKue    => match o with Oral => "kue" | Nasal => "ngue" end
  | NS_FutureRa   => "rã"
  | NS_ComparVe   => "ve"
  | NS_Super      => super_suffix o   (* ite / ete from Primitives *)
  | NS_Privative  => "'ỹ"
  | NS_Diminutive => "'i"
  | NS_Attenuative => match o with Oral => "vy" | Nasal => "ngy" end
  | NS_NomHA      => "ha"
  | NS_NomVA      => "va"
  | NS_NomPY      => match o with Oral => "py" | Nasal => "mby" end
  | NS_NomKue     => match o with Oral => "kue" | Nasal => "ngue" end
  | NS_OrdinalHA  => "ha"
  end.

(* ============================================================ *)
(*  10. Suffix ordering predicate                               *)
(*  §3.7: -rã then -kue is valid (frustrative);                 *)
(*  -kue then -rã is always invalid.                            *)
(*  More generally: we define which suffix pairs are legal.     *)
(* ============================================================ *)

(* Can suffix s2 follow suffix s1? *)
Definition suffix_pair_ok (s1 s2 : nominal_suffix) : bool :=
  match s1, s2 with
  (* §3.7: -rã + -kue = frustrative, the ONLY valid two-suffix combo
     for temporal markers *)
  | NS_FutureRa, NS_PastKue => true
  (* §3.2.1.1: nominalizer -ha/-va can follow other derivational suffixes
     e.g. su'u-py-rã = snack (bite-pass.nom-dest) *)
  | NS_NomPY,    NS_FutureRa => true
  | NS_NomPY,    NS_PastKue  => true
  | NS_NomHA,    NS_PastKue  => true   (* -hare = past agentive *)
  | NS_NomHA,    NS_FutureRa => true   (* -harã = future agentive *)
  (* All other pairs are forbidden *)
  | _, _ => false
  end.

(* Is this suffix ordering invalid? Used for well-formedness. *)
Definition suffix_order_invalid (s1 s2 : nominal_suffix) : bool :=
  negb (suffix_pair_ok s1 s2).

(* ============================================================ *)
(*  11. Postpositions                                           *)
(*  §5 "Postpositions"                                          *)
(*                                                              *)
(*  Postpositions follow a noun phrase and mark its grammatical  *)
(*  role. Several alternate by orality (pe/me, gui/ndi, etc.)   *)
(* ============================================================ *)

Inductive postposition : Type :=
  | Post_Pe        (* =pe / =me — in, at, to *)
  | Post_Gui       (* =gui — from *)
  | Post_Gua       (* =gua — from, of origin *)
  | Post_Rehe      (* =rehe / =re — at, about, because of *)
  | Post_Ndive     (* =ndive / =ndie — with, accompaniment *)
  | Post_Guive     (* =guive — since *)
  | Post_Peve      (* =peve — until *)
  | Post_Rupi      (* =rupi — through, by means of *)
  | Post_Ari       (* ='ári — upon, on top of *)
  | Post_Guy       (* =guy — under, below *)
  | Post_Guara     (* =guarã — for (benefactive) *)
  | Post_Hagua.    (* =haguã — in order to, for (purposive) *)

Definition postposition_form (o : orality) (p : postposition) : string :=
  match p with
  | Post_Pe    => match o with Oral => "pe"    | Nasal => "me"    end
  | Post_Gui   => match o with Oral => "gui"   | Nasal => "gui"   end
  | Post_Gua   => "gua"
  | Post_Rehe  => match o with Oral => "rehe"  | Nasal => "rehe"  end
  | Post_Ndive => match o with Oral => "ndive" | Nasal => "ndie"  end
  | Post_Guive => "guive"
  | Post_Peve  => "peve"
  | Post_Rupi  => "rupi"
  | Post_Ari   => "'ári"
  | Post_Guy   => "guy"
  | Post_Guara => "guarã"
  | Post_Hagua => "haguã"
  end.

(* ============================================================ *)
(*  12. NP metadata for verb agreement                          *)
(* ============================================================ *)

Record np_meta : Type := mkNPMeta {
  np_orality     : orality;
  np_number      : number;
  np_person      : person;
  np_inclusivity : option inclusivity
}.
(* ============================================================ *)
(*  13. Noun phrase AST                                         *)
(*  §3.1 NP order:                                              *)
(*    (det/dem/num/quant) + (possessor) + head noun +           *)
(*    (adjective) + (relative clause)                           *)
(*                                                              *)
(*  Each constructor represents a way to build a noun phrase.   *)
(*  Relative and complement clauses use a forward-declared       *)
(*  verb_phrase type (from Verb.v) — for now we use a string    *)
(*  placeholder to avoid circular imports.                      *)
(* ============================================================ *)

(* Placeholder for embedded clauses until Verb.v is imported.
   In the full system, this would be a conjugated_verb or sentence. *)
Record embedded_clause : Type := mkEmbClause {
  ec_form    : string;
  ec_orality : orality;
  ec_person  : person;
  ec_number  : number
}.

Inductive guarani_np : Type :=

  (* --- Noun-headed phrases --- *)

  (* Bare noun: "jagua" = dog
     §3.1: "Bare nouns are enough to form a grammatical noun phrase." *)
  | NP_Bare    : noun -> guarani_np

  (* Demonstrative determiner + noun: "ko jagua" = this dog
     §3.4.2: demonstrative precedes noun *)
  | NP_Dem     : dem_proximity -> number -> noun -> guarani_np

  (* Article + noun: "la jagua" = the dog
     §3.4.1: la (singular), lo (plural) — borrowed from Spanish *)
  | NP_Art     : number -> noun -> guarani_np

  (* Noun + adjective: "jagua ñarõ" = ferocious dog
     §3.3: adjective follows noun *)
  | NP_Adj     : noun -> adjective -> guarani_np

  (* Possessive marker + noun: "che juru" = my mouth
     §3.6: possessive prefix + noun *)
  | NP_Poss    : poss_marker -> noun -> guarani_np

  (* Numeral + noun: "mbohapy ryguasu" = three chickens
     §3.4.3: cardinal number precedes noun
     §3.1.1: "plural number is generally not marked when the noun
     is accompanied by a numeral" *)
  | NP_Num     : GuaraniNum -> noun -> guarani_np

  (* Genitive: possessor NP + possessed noun
     §3.6: "possessor-possessum order, indicated by simple juxtaposition"
     "Maria ajaka" = Maria's basket
     "mitã sy" = the child's mother *)
  | NP_Gen     : guarani_np -> noun -> guarani_np

  (* Demonstrative + possessive + noun
     §3.4.2: "demonstratives can co-occur with possessive prefixes"
     "ko che irũ" = this friend of mine *)
  | NP_DemPoss : dem_proximity -> poss_marker -> noun -> guarani_np

  (* Noun + relative clause (verb + -va modifying a noun)
     §3.2.1.1.3 / §12.2.1: "kuña oikuaáva" = woman that knows
     "mayma kuña oikuaáva" = all the women that know *)
  | NP_Rel     : noun -> embedded_clause -> guarani_np

  (* Complement clause (verb + -ha functioning as a noun)
     §3.2.1.1.1 / §12.2.2: "-ha is also used as a subordinator"
     "Ha'e ndoikomo'ãiha" = I say that there will not be *)
  | NP_Comp    : embedded_clause -> guarani_np

  (* --- Suffix attachment --- *)

  (* Single nominal suffix on any noun-headed NP *)
  | NP_Suf     : guarani_np -> nominal_suffix -> guarani_np

  (* Two ordered suffixes (for valid combinations like -rã + -kue)
     §3.7: "cherogarãngue" = my former future house *)
  | NP_Suf2    : guarani_np -> nominal_suffix -> nominal_suffix -> guarani_np

  (* --- Pronouns (standalone, no noun head) --- *)

  (* Subject pronoun: "che" = I
     §3.5.1 *)
  | NP_PronSubj  : subj_pronoun -> guarani_np

  (* Possessive pronoun: poss_marker + mba'e
     §3.5.5: "chemba'e" = mine, "nemba'e" = yours *)
  | NP_PronPoss  : poss_marker -> guarani_np

  (* Demonstrative pronoun: "kóva" = this one
     §3.5.4: formed by adding -va to demonstrative determiners *)
  | NP_PronDem   : dem_proximity -> number -> guarani_np

  (* Indefinite pronoun: "maymáva" = everyone
     §3.5.3 *)
  | NP_PronIndef : indef_pron -> guarani_np

  (* Interrogative pronoun: "mba'e" = what, "máva" = who
     §3.5.2 *)
  | NP_PronInterrog : interrog_pron -> guarani_np

  (* Negative pronoun: "avave" = nobody, "mba'eve" = nothing
     §3.5.3: requires double negation on the verb *)
  | NP_PronNeg   : neg_pron -> guarani_np

  (* --- Coordination --- *)

  (* NP ha NP — and (always plural)
     §12.1 *)
  | NP_CoordHa   : guarani_np -> guarani_np -> guarani_np

  (* NP tera NP — or (inherits from left)
     §12.1 *)
  | NP_CoordTera : guarani_np -> guarani_np -> guarani_np.

(* ============================================================ *)
(*  14. Well-formedness predicate                               *)
(* ============================================================ *)

(* Can this NP take a nominal suffix? Only noun-headed NPs. *)
Fixpoint is_noun_headed (x : guarani_np) : bool :=
  match x with
  | NP_Bare _       => true
  | NP_Dem _ _ _    => true
  | NP_Art _ _      => true
  | NP_Adj _ _      => true
  | NP_Poss _ _     => true
  | NP_Num _ _      => true
  | NP_Gen _ _      => true
  | NP_DemPoss _ _ _ => true
  | NP_Rel _ _      => true
  | NP_Comp _       => true
  | NP_Suf inner _  => is_noun_headed inner
  | NP_Suf2 inner _ _ => is_noun_headed inner
  | _               => false
  end.

(* Does this NP already have a suffix? *)
Fixpoint has_suffix (x : guarani_np) : bool :=
  match x with
  | NP_Suf _ _    => true
  | NP_Suf2 _ _ _ => true
  | _             => false
  end.

(* Well-formed NP:
   - Suffix only on noun-headed NPs
   - At most one suffix via NP_Suf (no stacking via NP_Suf on NP_Suf)
   - NP_Suf2 requires a valid suffix pair
   - NP_Suf2 cannot wrap another suffixed NP
   - Recursive well-formedness for coordination and genitive *)
Fixpoint wf_np (x : guarani_np) : bool :=
  match x with
  (* Base noun-headed: always well-formed *)
  | NP_Bare _ | NP_Dem _ _ _ | NP_Art _ _ | NP_Adj _ _
  | NP_Poss _ _ | NP_Num _ _ | NP_DemPoss _ _ _ => true

  (* Genitive: possessor must be well-formed *)
  | NP_Gen poss _ => wf_np poss

  (* Relative clause: head noun is always ok, embedded clause assumed wf *)
  | NP_Rel _ _ => true

  (* Complement clause: always well-formed at NP level *)
  | NP_Comp _ => true

  (* Single suffix: must be on noun-headed, no prior suffix *)
  | NP_Suf inner _ =>
      is_noun_headed inner && negb (has_suffix inner) && wf_np inner

  (* Double suffix: must be on noun-headed, no prior suffix,
     and the pair must be a valid ordering *)
  | NP_Suf2 inner s1 s2 =>
      is_noun_headed inner && negb (has_suffix inner) && wf_np inner
      && suffix_pair_ok s1 s2

  (* Pronouns: always well-formed *)
  | NP_PronSubj _ | NP_PronPoss _ | NP_PronDem _ _
  | NP_PronIndef _ | NP_PronInterrog _ | NP_PronNeg _ => true

  (* Coordination: both conjuncts must be well-formed *)
  | NP_CoordHa x1 x2 => wf_np x1 && wf_np x2
  | NP_CoordTera x1 x2 => wf_np x1 && wf_np x2
  end.

(* ============================================================ *)
(*  15. Helper functions                                        *)
(* ============================================================ *)

Definition inclusivity_of_poss (p : poss_marker) : option inclusivity :=
  match p with
  | Poss1Incl => Some Inclusive
  | Poss1Excl => Some Exclusive
  | _ => None
  end.
 
Definition inclusivity_of_subj (p : subj_pronoun) : option inclusivity :=
  match p with
  | Subj1PL_INCL => Some Inclusive
  | Subj1PL_EXCL => Some Exclusive
  | _ => None
  end.

Definition person_of_subj (p : subj_pronoun) : person :=
  match p with
  | Subj1SG | Subj1PL_INCL | Subj1PL_EXCL => First
  | Subj2SG | Subj2PL                      => Second
  | Subj3SG | Subj3PL                      => Third
  end.

Definition number_of_subj (p : subj_pronoun) : number :=
  match p with
  | Subj1SG | Subj2SG | Subj3SG => Singular
  | _                            => Plural
  end.

Definition person_of_poss (p : poss_marker) : person :=
  match p with
  | Poss1 | Poss1Incl | Poss1Excl => First
  | Poss2 | Poss2Pl               => Second
  | Poss3 | Poss3Pl               => Third
  end.

Definition number_of_poss (p : poss_marker) : number :=
  match p with
  | Poss1 | Poss2 | Poss3 => Singular
  | _                     => Plural
  end.

Definition number_of_indef (i : indef_pron) : number :=
  match i with
  | Indef_Avave | Indef_Mbaeve | Indef_PeteiMbae => Singular
  | _                                             => Plural
  end.

Definition person_merge (p1 p2 : person) : person :=
  match p1, p2 with
  | First, _ | _, First   => First
  | Second, _ | _, Second => Second
  | Third, Third          => Third
  end.

(* ============================================================ *)
(*  16. Metadata inference                                      *)
(*  Infers person, number, and orality from NP structure         *)
(*  for use in verb agreement (Sentences.v)                     *)
(* ============================================================ *)

Fixpoint np_meta_of (x : guarani_np) : np_meta :=
  match x with
  | NP_Bare n =>
      mkNPMeta (n_orality n) Singular Third None
 
  | NP_Dem _ num n =>
      mkNPMeta (n_orality n) num Third None
 
  | NP_Art num n =>
      mkNPMeta (n_orality n) num Third None
 
  | NP_Adj n _ =>
      mkNPMeta (n_orality n) Singular Third None
 
  | NP_Poss pm n =>
      mkNPMeta (n_orality n) (number_of_poss pm) (person_of_poss pm)
               (inclusivity_of_poss pm)
 
  | NP_Num gn n =>
      let num := if is_one gn then Singular else Plural in
      mkNPMeta (n_orality n) num Third None
 
  | NP_Gen _ n =>
      mkNPMeta (n_orality n) Singular Third None
 
  | NP_DemPoss _ pm n =>
      mkNPMeta (n_orality n) (number_of_poss pm) (person_of_poss pm)
               (inclusivity_of_poss pm)
 
  | NP_Rel n _ =>
      mkNPMeta (n_orality n) Singular Third None
 
  | NP_Comp ec =>
      mkNPMeta (ec_orality ec) Singular Third None
 
  | NP_Suf inner NS_Plural =>
      let m := np_meta_of inner in
      mkNPMeta (np_orality m) Plural (np_person m) (np_inclusivity m)
  | NP_Suf inner NS_Multitude =>
      let m := np_meta_of inner in
      mkNPMeta (np_orality m) Plural (np_person m) (np_inclusivity m)
  | NP_Suf inner _ =>
      np_meta_of inner
 
  | NP_Suf2 inner _ _ =>
      np_meta_of inner
 
  | NP_PronSubj p =>
      mkNPMeta Oral (number_of_subj p) (person_of_subj p)
               (inclusivity_of_subj p)
 
  | NP_PronPoss pm =>
      mkNPMeta Oral (number_of_poss pm) (person_of_poss pm)
               (inclusivity_of_poss pm)
 
  | NP_PronDem _ n =>
      mkNPMeta Oral n Third None
 
  | NP_PronIndef i =>
      mkNPMeta Oral (number_of_indef i) Third None
 
  | NP_PronInterrog _ =>
      mkNPMeta Oral Singular Third None
 
  | NP_PronNeg _ =>
      mkNPMeta Oral Singular Third None
 
  | NP_CoordHa x1 x2 =>
      let m1 := np_meta_of x1 in
      let m2 := np_meta_of x2 in
      mkNPMeta (np_orality m1) Plural
               (person_merge (np_person m1) (np_person m2))
               None  (* coordination doesn't preserve inclusivity *)
 
  | NP_CoordTera x1 _ =>
      np_meta_of x1
  end.

Definition np_plural_suffix (x : guarani_np) : string :=
  plural_suffix_adj (np_orality (np_meta_of x)).

(* ============================================================ *)
(*  17. Decidable equality                                      *)
(* ============================================================ *)

Scheme Equality for root_class.
Scheme Equality for poss_context.
Scheme Equality for dem_set.
Scheme Equality for dem_proximity.
Scheme Equality for subj_pronoun.
Scheme Equality for indef_pron.
Scheme Equality for interrog_pron.
Scheme Equality for neg_pron.
Scheme Equality for nominal_suffix.
Scheme Equality for postposition.

(* ============================================================ *)
(*  18. Theorems                                                *)
(*                                                              *)
(*  Organized by grammatical rule with explicit naming and       *)
(*  grammar book section references.                            *)
(* ============================================================ *)

(* ------------------------------------------------------------ *)
(*  RULE NP-A: Root class prefix selection                      *)
(*  §3.1.3 "relational (multiform) nominal roots"               *)
(* ------------------------------------------------------------ *)

(* NP-A1: Triform nouns use t- in non-possessed context.
   §3.1.3: "tayhu" = love (non-possessed) *)
Theorem rule_NPA1_triform_nonposs_is_t :
    root_prefix Triform PossCtx_None = "t".
Proof. reflexivity. Qed.

(* NP-A2: Triform nouns use r- when possessed by 1st/2nd or NP.
   §3.1.3: "che rova" = my face *)
Theorem rule_NPA2_triform_firstsecond_is_r :
    root_prefix Triform PossCtx_FirstSecond = "r".
Proof. reflexivity. Qed.

(* NP-A3: Triform nouns use h- when possessed by 3rd person pronoun.
   §3.1.3: "hova" = his/her face *)
Theorem rule_NPA3_triform_third_is_h :
    root_prefix Triform PossCtx_Third = "h".
Proof. reflexivity. Qed.

(* NP-A4: All three triform prefixes are distinct. *)
Theorem rule_NPA4_triform_all_distinct :
    root_prefix Triform PossCtx_None <> root_prefix Triform PossCtx_FirstSecond /\
    root_prefix Triform PossCtx_FirstSecond <> root_prefix Triform PossCtx_Third /\
    root_prefix Triform PossCtx_None <> root_prefix Triform PossCtx_Third.
Proof. simpl. repeat split; discriminate. Qed.

(* NP-A5: TriformNoT nouns have no prefix in non-possessed context.
   §3.1.3: "óga" (not *"tóga") *)
Theorem rule_NPA5_triformNoT_nonposs_empty :
    root_prefix TriformNoT PossCtx_None = "".
Proof. reflexivity. Qed.

(* NP-A6: TriformNoT nouns still use r- and h- for possessed forms.
   §3.1.3: "che róga" (my house), "hóga" (his house) *)
Theorem rule_NPA6_triformNoT_firstsecond_is_r :
    root_prefix TriformNoT PossCtx_FirstSecond = "r".
Proof. reflexivity. Qed.

Theorem rule_NPA6_triformNoT_third_is_h :
    root_prefix TriformNoT PossCtx_Third = "h".
Proof. reflexivity. Qed.

(* NP-A7: Uniform nouns never get a prefix in any context. *)
Theorem rule_NPA7_uniform_always_empty : forall ctx,
    root_prefix Uniform ctx = "".
Proof. intros ctx; destruct ctx; reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-B: Well-formedness constraints                      *)
(* ------------------------------------------------------------ *)

(* NP-B1: All base noun-headed NPs are well-formed.
   §3.1: NPs can consist of a single noun. *)
Theorem rule_NPB1_bare_wf : forall n, wf_np (NP_Bare n) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_dem_wf : forall prox num n,
    wf_np (NP_Dem prox num n) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_adj_wf : forall n a,
    wf_np (NP_Adj n a) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_poss_wf : forall pm n,
    wf_np (NP_Poss pm n) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_num_wf : forall gn n,
    wf_np (NP_Num gn n) = true.
Proof. reflexivity. Qed.

(* NP-B2: A single suffix on a bare noun is well-formed.
   §3.1.1: "araikuéra" = clouds *)
Theorem rule_NPB2_single_suffix_wf : forall n suf,
    wf_np (NP_Suf (NP_Bare n) suf) = true.
Proof. reflexivity. Qed.

(* NP-B3: Double suffix via NP_Suf stacking is ill-formed.
   Must use NP_Suf2 instead.
   §3.7: at most two ordered suffixes allowed *)
Theorem rule_NPB3_double_suf_stacking_ill : forall n s1 s2,
    wf_np (NP_Suf (NP_Suf (NP_Bare n) s1) s2) = false.
Proof. reflexivity. Qed.

(* NP-B4: Suffix on pronoun is ill-formed.
   Pronouns are not noun-headed. *)
Theorem rule_NPB4_suffix_on_pronoun_ill : forall p suf,
    wf_np (NP_Suf (NP_PronSubj p) suf) = false.
Proof. reflexivity. Qed.

(* NP-B5: Genitive preserves well-formedness. *)
Theorem rule_NPB5_gen_preserves : forall poss n,
    wf_np poss = true -> wf_np (NP_Gen poss n) = true.
Proof. intros poss n H. simpl. exact H. Qed.

(* NP-B6: All pronoun NPs are well-formed. *)
Theorem rule_NPB6_subj_pron_wf : forall p, wf_np (NP_PronSubj p) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB6_interrog_pron_wf : forall i, wf_np (NP_PronInterrog i) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB6_neg_pron_wf : forall np, wf_np (NP_PronNeg np) = true.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-C: Suffix ordering                                  *)
(*  §3.7 "-rã then -kue is valid; -kue then -rã is invalid"     *)
(* ------------------------------------------------------------ *)

(* NP-C1: The frustrative -rã + -kue combination is well-formed.
   §3.7: "cherogarãngue" = my former future house *)
Theorem rule_NPC1_ra_then_kue_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_FutureRa NS_PastKue) = true.
Proof. reflexivity. Qed.

(* NP-C2: The reverse -kue + -rã is ill-formed.
   §3.7: "*cherogakuerã does not exist" *)
Theorem rule_NPC2_kue_then_ra_invalid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_PastKue NS_FutureRa) = false.
Proof. reflexivity. Qed.

(* NP-C3: Past agentive -ha + -kue (= -hare) is well-formed.
   §3.2.1.1.1: "hechahare" = witness (one who saw) *)
Theorem rule_NPC3_ha_then_kue_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomHA NS_PastKue) = true.
Proof. reflexivity. Qed.

(* NP-C4: Future agentive -ha + -rã (= -harã) is well-formed.
   §3.2.1.1.1: "apoharã" = future builder *)
Theorem rule_NPC4_ha_then_ra_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomHA NS_FutureRa) = true.
Proof. reflexivity. Qed.

(* NP-C5: Past passive -py + -kue (= -pyre) is well-formed.
   §3.2.1.1.2: "haipyre" = written (something that was written) *)
Theorem rule_NPC5_py_then_kue_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomPY NS_PastKue) = true.
Proof. reflexivity. Qed.

(* NP-C6: Future passive -py + -rã (= -pyrã) is well-formed.
   §3.2.1.1.2: "su'upyrã" = snack (thing destined to be bitten) *)
Theorem rule_NPC6_py_then_ra_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomPY NS_FutureRa) = true.
Proof. reflexivity. Qed.

(* NP-C7: Two plural suffixes is always ill-formed. *)
Theorem rule_NPC7_double_plural_invalid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_Plural NS_Plural) = false.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-D: Subject pronoun metadata                         *)
(*  §3.5.1                                                      *)
(* ------------------------------------------------------------ *)

Theorem rule_NPD1_subj_person_consistent : forall p,
    np_person (np_meta_of (NP_PronSubj p)) = person_of_subj p.
Proof. intros p; destruct p; reflexivity. Qed.

Theorem rule_NPD2_subj_number_consistent : forall p,
    np_number (np_meta_of (NP_PronSubj p)) = number_of_subj p.
Proof. intros p; destruct p; reflexivity. Qed.

(* §3.5.1: "these pronouns are never subject to pronunciation
   changes based on nasal harmony, unlike person prefixes" *)
Theorem rule_NPD3_subj_pron_always_oral : forall p,
    np_orality (np_meta_of (NP_PronSubj p)) = Oral.
Proof. intros p; destruct p; reflexivity. Qed.

(* §3.5.1: each pronoun renders to a unique string *)
Theorem rule_NPD4_subj_pron_injective : forall p1 p2,
    render_subj_pronoun p1 = render_subj_pronoun p2 -> p1 = p2.
Proof.
  intros p1 p2; destruct p1; destruct p2; simpl; intro H;
    try reflexivity; discriminate.
Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-E: Bare noun metadata                               *)
(*  §3.1: bare nouns are 3rd person, singular                   *)
(* ------------------------------------------------------------ *)

Theorem rule_NPE1_bare_always_third : forall n,
    np_person (np_meta_of (NP_Bare n)) = Third.
Proof. reflexivity. Qed.

Theorem rule_NPE2_bare_always_singular : forall n,
    np_number (np_meta_of (NP_Bare n)) = Singular.
Proof. reflexivity. Qed.

Theorem rule_NPE3_bare_orality_from_noun : forall n,
    np_orality (np_meta_of (NP_Bare n)) = n_orality n.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-F: Plural suffix allomorphy                         *)
(*  §3.1.1 "=kuéra with nasal variant =nguéra"                  *)
(* ------------------------------------------------------------ *)

Theorem rule_NPF1_nasal_noun_gets_nguera : forall n,
    n_orality n = Nasal -> np_plural_suffix (NP_Bare n) = "nguéra".
Proof.
  intros n H. unfold np_plural_suffix. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_NPF2_oral_noun_gets_kuera : forall n,
    n_orality n = Oral -> np_plural_suffix (NP_Bare n) = "kuéra".
Proof.
  intros n H. unfold np_plural_suffix. simpl. rewrite H. reflexivity.
Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-G: Demonstrative system                             *)
(*  §3.4.2                                                      *)
(* ------------------------------------------------------------ *)

(* NP-G1: Proximal singular demonstrative is "ko".
   §3.4.2: "ko jagua" = this dog *)
Theorem rule_NPG1_prox_singular :
    dem_adj_form DemProxSpeaker Singular = "ko".
Proof. reflexivity. Qed.

(* NP-G2: Non-proximal plural demonstratives all collapse to "umi".
   §3.4.2: "only umi is used [for plural], except proximal" *)
Theorem rule_NPG2_hearer_plural_is_umi :
    dem_adj_form DemProxHearer Plural = "umi".
Proof. reflexivity. Qed.

Theorem rule_NPG2_distal_plural_is_umi :
    dem_adj_form DemDistal Plural = "umi".
Proof. reflexivity. Qed.

Theorem rule_NPG2_shared_plural_is_umi :
    dem_adj_form DemSharedPerson Plural = "umi".
Proof. reflexivity. Qed.

(* NP-G3: Proximal plural is "ko'ã" (not "umi").
   §3.4.2: "ko'ã ta'anga" = these pictures *)
Theorem rule_NPG3_prox_plural_is_koa :
    dem_adj_form DemProxSpeaker Plural = "ko'ã".
Proof. reflexivity. Qed.

(* NP-G4: Demonstrative pronouns are formed with -va.
   §3.5.4: "kóva" from "ko", "péva" from "pe" *)
Theorem rule_NPG4_prox_pron_is_kova :
    dem_pron_form DemProxSpeaker Singular = "kóva".
Proof. reflexivity. Qed.

Theorem rule_NPG4_hearer_pron_is_peva :
    dem_pron_form DemProxHearer Singular = "péva".
Proof. reflexivity. Qed.

(* NP-G5: Hearsay demonstrative is "aipo".
   §3.4.2: "aipo Papá Noel" = that guy Santa Claus (no direct knowledge) *)
Theorem rule_NPG5_hearsay_is_aipo :
    dem_adj_form DemHearsay Singular = "aipo".
Proof. reflexivity. Qed.

(* NP-G6: Demonstrative NPs are always 3rd person. *)
Theorem rule_NPG6_dem_np_always_third : forall prox num n,
    np_person (np_meta_of (NP_Dem prox num n)) = Third.
Proof. reflexivity. Qed.

(* NP-G7: Demonstrative NP number matches the determiner number. *)
Theorem rule_NPG7_dem_np_number : forall prox num n,
    np_number (np_meta_of (NP_Dem prox num n)) = num.
Proof. intros prox num n; destruct num; reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-H: Suffix metadata effects                          *)
(*  §3.1.1, §3.7                                                *)
(* ------------------------------------------------------------ *)

(* NP-H1: Plural suffix forces plural number. *)
Theorem rule_NPH1_plural_forces_plural : forall x,
    np_number (np_meta_of (NP_Suf x NS_Plural)) = Plural.
Proof. reflexivity. Qed.

(* NP-H2: Multitude suffix forces plural number. *)
Theorem rule_NPH2_multitude_forces_plural : forall x,
    np_number (np_meta_of (NP_Suf x NS_Multitude)) = Plural.
Proof. reflexivity. Qed.

(* NP-H3: Plural suffix preserves person and orality. *)
Theorem rule_NPH3_plural_preserves_person : forall x,
    np_person (np_meta_of (NP_Suf x NS_Plural)) = np_person (np_meta_of x).
Proof. reflexivity. Qed.

Theorem rule_NPH3_plural_preserves_orality : forall x,
    np_orality (np_meta_of (NP_Suf x NS_Plural)) = np_orality (np_meta_of x).
Proof. reflexivity. Qed.

(* NP-H4: Temporal suffixes (-kue, -rã) are transparent to metadata.
   §3.7: these change the temporal reference, not person/number *)
Theorem rule_NPH4_kue_transparent : forall x,
    np_meta_of (NP_Suf x NS_PastKue) = np_meta_of x.
Proof. reflexivity. Qed.

Theorem rule_NPH4_ra_transparent : forall x,
    np_meta_of (NP_Suf x NS_FutureRa) = np_meta_of x.
Proof. reflexivity. Qed.

(* NP-H5: Degree suffixes are transparent to metadata. *)
Theorem rule_NPH5_compar_transparent : forall x,
    np_meta_of (NP_Suf x NS_ComparVe) = np_meta_of x.
Proof. reflexivity. Qed.

Theorem rule_NPH5_super_transparent : forall x,
    np_meta_of (NP_Suf x NS_Super) = np_meta_of x.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-I: Genitive NP metadata                             *)
(*  §3.6 "possessor-possessum order"                             *)
(* ------------------------------------------------------------ *)

(* NP-I1: Genitive NPs are always 3rd person.
   The possessor's person doesn't propagate. *)
Theorem rule_NPI1_gen_always_third : forall poss n,
    np_person (np_meta_of (NP_Gen poss n)) = Third.
Proof. reflexivity. Qed.

(* NP-I2: Genitive NPs are singular (the head noun is singular). *)
Theorem rule_NPI2_gen_always_singular : forall poss n,
    np_number (np_meta_of (NP_Gen poss n)) = Singular.
Proof. reflexivity. Qed.

(* NP-I3: Genitive NP orality comes from the head noun. *)
Theorem rule_NPI3_gen_orality_from_head : forall poss n,
    np_orality (np_meta_of (NP_Gen poss n)) = n_orality n.
Proof. reflexivity. Qed.

(* NP-I4: Genitive NPs are noun-headed (can take suffixes). *)
Theorem rule_NPI4_gen_is_noun_headed : forall poss n,
    is_noun_headed (NP_Gen poss n) = true.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-J: Possessive NP metadata                           *)
(*  §3.6, §3.5.1                                                *)
(* ------------------------------------------------------------ *)

Theorem rule_NPJ1_poss_person_from_marker : forall pm n,
    np_person (np_meta_of (NP_Poss pm n)) = person_of_poss pm.
Proof. intros pm n; destruct pm; reflexivity. Qed.

Theorem rule_NPJ2_poss_number_from_marker : forall pm n,
    np_number (np_meta_of (NP_Poss pm n)) = number_of_poss pm.
Proof. intros pm n; destruct pm; reflexivity. Qed.

Theorem rule_NPJ3_poss_orality_from_noun : forall pm n,
    np_orality (np_meta_of (NP_Poss pm n)) = n_orality n.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-K: Numeral NP metadata                              *)
(*  §3.4.3, §3.1.1                                              *)
(* ------------------------------------------------------------ *)

(* NP-K1: peteĩ (one) + noun = singular *)
Theorem rule_NPK1_one_is_singular : forall gn n,
    is_one gn = true -> np_number (np_meta_of (NP_Num gn n)) = Singular.
Proof. intros gn n H. simpl. rewrite H. reflexivity. Qed.

(* NP-K2: any numeral > 1 + noun = plural *)
Theorem rule_NPK2_not_one_is_plural : forall gn n,
    is_one gn = false -> np_number (np_meta_of (NP_Num gn n)) = Plural.
Proof. intros gn n H. simpl. rewrite H. reflexivity. Qed.

(* NP-K3: numeral NPs are always 3rd person *)
Theorem rule_NPK3_num_always_third : forall gn n,
    np_person (np_meta_of (NP_Num gn n)) = Third.
Proof. intros gn n. simpl. destruct (is_one gn); reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-L: Coordination metadata                            *)
(*  §12.1                                                       *)
(* ------------------------------------------------------------ *)

(* NP-L1: ha-coordination always yields plural.
   §12.1: "Mario ha Ana" → plural subject *)
Theorem rule_NPL1_ha_always_plural : forall x1 x2,
    np_number (np_meta_of (NP_CoordHa x1 x2)) = Plural.
Proof. reflexivity. Qed.

(* NP-L2: ha-coordination merges person (1st > 2nd > 3rd). *)
Theorem rule_NPL2_ha_first_dominates_left : forall x2,
    np_person (np_meta_of (NP_CoordHa (NP_PronSubj Subj1SG) x2)) = First.
Proof. reflexivity. Qed.

Theorem rule_NPL2_ha_first_dominates_right : forall x1,
    np_person (np_meta_of (NP_CoordHa x1 (NP_PronSubj Subj1SG))) = First.
Proof.
  intros x1. simpl. destruct (np_person (np_meta_of x1)); reflexivity.
Qed.

(* NP-L3: tera-coordination inherits metadata from left conjunct. *)
Theorem rule_NPL3_tera_inherits_left : forall x1 x2,
    np_meta_of (NP_CoordTera x1 x2) = np_meta_of x1.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-M: person_merge properties                          *)
(* ------------------------------------------------------------ *)

Theorem rule_NPM1_merge_commutative : forall p1 p2,
    person_merge p1 p2 = person_merge p2 p1.
Proof. intros p1 p2; destruct p1; destruct p2; reflexivity. Qed.

Theorem rule_NPM2_merge_idempotent : forall p,
    person_merge p p = p.
Proof. intros p; destruct p; reflexivity. Qed.

Theorem rule_NPM3_first_always_dominates : forall p,
    person_merge First p = First /\ person_merge p First = First.
Proof. intros p; destruct p; split; reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-N: Postposition allomorphy                          *)
(*  §5                                                          *)
(* ------------------------------------------------------------ *)

(* NP-N1: =pe becomes =me with nasal nouns.
   §1.2: "ñúme" (in the field), not *"ñúpe" *)
Theorem rule_NPN1_pe_me_oral :
    postposition_form Oral Post_Pe = "pe".
Proof. reflexivity. Qed.

Theorem rule_NPN1_pe_me_nasal :
    postposition_form Nasal Post_Pe = "me".
Proof. reflexivity. Qed.

Theorem rule_NPN1_pe_me_distinct :
    postposition_form Oral Post_Pe <> postposition_form Nasal Post_Pe.
Proof. discriminate. Qed.

(* NP-N2: =gua and =guive are invariant across orality. *)
Theorem rule_NPN2_gua_invariant : forall o,
    postposition_form o Post_Gua = "gua".
Proof. intros o; destruct o; reflexivity. Qed.

(* NP-N3: =ndive becomes =ndie with nasal nouns.
   §5: "with" postposition *)
Theorem rule_NPN3_ndive_oral :
    postposition_form Oral Post_Ndive = "ndive".
Proof. reflexivity. Qed.

Theorem rule_NPN3_ndie_nasal :
    postposition_form Nasal Post_Ndive = "ndie".
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-O: Negative pronoun properties                      *)
(*  §3.5.3 "negative pronouns require double negation"           *)
(* ------------------------------------------------------------ *)

(* NP-O1: avave and mba'eve are classified as negative.
   These require the verb to also be negated (double negation). *)
Theorem rule_NPO1_avave_is_negative :
    is_negative_pron Indef_Avave = true.
Proof. reflexivity. Qed.

Theorem rule_NPO1_mbaeve_is_negative :
    is_negative_pron Indef_Mbaeve = true.
Proof. reflexivity. Qed.

(* NP-O2: Non-negative indefinite pronouns are not marked negative. *)
Theorem rule_NPO2_maymava_not_negative :
    is_negative_pron Indef_Maymava = false.
Proof. reflexivity. Qed.

Theorem rule_NPO2_oimeraeva_not_negative :
    is_negative_pron Indef_Oimeraeva = false.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  RULE NP-P: Interrogative pronoun rendering                  *)
(*  §3.5.2                                                      *)
(* ------------------------------------------------------------ *)

(* NP-P1: Each interrogative renders to a distinct string. *)
Theorem rule_NPP1_mbae_renders :
    render_interrog_pron Interrog_Mbae = "mba'e".
Proof. reflexivity. Qed.

Theorem rule_NPP1_mava_renders :
    render_interrog_pron Interrog_Mava = "máva".
Proof. reflexivity. Qed.

Theorem rule_NPP1_mbovy_renders :
    render_interrog_pron Interrog_Mbovy = "mbovy".
Proof. reflexivity. Qed.

(* NP-P2: Interrogative pronouns are always 3rd person singular
   for agreement purposes. *)
Theorem rule_NPP2_interrog_always_third : forall i,
    np_person (np_meta_of (NP_PronInterrog i)) = Third.
Proof. reflexivity. Qed.

Theorem rule_NPP2_interrog_always_singular : forall i,
    np_number (np_meta_of (NP_PronInterrog i)) = Singular.
Proof. reflexivity. Qed.

(* ============================================================ *)
(*  19. Examples                                                *)
(* ============================================================ *)

(* --- Sample nouns --- *)

(* §3.1.3: "jagua" = dog, uniform (no alternation) *)
Definition n_jagua : noun := mkNoun "jagua" Oral EndAEO Uniform.

(* §3.1.3: tova/rova/hova = face, triform *)
Definition n_ova : noun := mkNoun "ova" Oral EndAEO Triform.

(* §3.1.3: óga/róga/hóga = house, triform without t- *)
Definition n_oga : noun := mkNoun "óga" Oral EndAEO TriformNoT.

(* §3.1.3: túva/ru = father, biform kinship *)
Definition n_u : noun := mkNoun "u" Oral EndIUY Biform.

(* §3.1: mitã = child, nasal *)
Definition n_mita : noun := mkNoun "mitã" Nasal EndAEO Uniform.

(* §3.1: sy = mother, nasal *)
Definition n_sy : noun := mkNoun "sy" Nasal EndIUY Uniform.

(* §3.1: ao = clothes, oral *)
Definition n_ao : noun := mkNoun "ao" Oral EndAEO Uniform.

(* §3.1: kuatia = paper/letter *)
Definition n_kuatia : noun := mkNoun "kuatia" Oral EndAEO Uniform.

(* --- Root alternation examples --- *)

(* §3.1.3: "tova" = a face (non-possessed) *)
Example ex_tova : noun_surface n_ova PossCtx_None = "tova".
Proof. reflexivity. Qed.

(* §3.1.3: "che rova" = my face (1st/2nd possessed) *)
Example ex_rova : noun_surface n_ova PossCtx_FirstSecond = "rova".
Proof. reflexivity. Qed.

(* §3.1.3: "hova" = his/her face (3rd possessed) *)
Example ex_hova : noun_surface n_ova PossCtx_Third = "hova".
Proof. reflexivity. Qed.

(* §3.1.3: "óga" = a house (non-possessed, no t-) *)
Example ex_oga : noun_surface n_oga PossCtx_None = "óga".
Proof. reflexivity. Qed.

(* §3.1.3: "che róga" = my house *)
Example ex_roga : noun_surface n_oga PossCtx_FirstSecond = "róga".
Proof. reflexivity. Qed.

(* §3.1.3: "hóga" = his/her house *)
Example ex_hoga : noun_surface n_oga PossCtx_Third = "hóga".
Proof. reflexivity. Qed.

(* §3.1: "jagua" is always "jagua" (uniform) *)
Example ex_jagua_uniform : forall ctx, noun_surface n_jagua ctx = "jagua".
Proof. intros ctx; destruct ctx; reflexivity. Qed.

(* --- Demonstrative examples --- *)

(* §3.4.2: "ko jagua" = this dog *)
Definition ex_ko_jagua : guarani_np :=
  NP_Dem DemProxSpeaker Singular n_jagua.

Example ex_ko_jagua_wf : wf_np ex_ko_jagua = true.
Proof. reflexivity. Qed.

(* §3.4.2: "umi guyra" = those birds *)
Example ex_umi_plural :
    dem_adj_form DemProxHearer Plural = "umi".
Proof. reflexivity. Qed.

(* §3.4.2: "aipo Papá Noel" = that Santa Claus (hearsay) *)
Example ex_aipo :
    dem_adj_form DemHearsay Singular = "aipo".
Proof. reflexivity. Qed.

(* --- Suffix ordering examples --- *)

(* §3.7: "cherogarãngue" — well-formed frustrative *)
Definition ex_oga_ra_kue : guarani_np :=
  NP_Suf2 (NP_Poss Poss1 n_oga) NS_FutureRa NS_PastKue.

Example ex_oga_ra_kue_wf : wf_np ex_oga_ra_kue = true.
Proof. reflexivity. Qed.

(* §3.7: "*cherogakuerã" — ill-formed, invalid order *)
Definition ex_oga_kue_ra : guarani_np :=
  NP_Suf2 (NP_Poss Poss1 n_oga) NS_PastKue NS_FutureRa.

Example ex_oga_kue_ra_bad : wf_np ex_oga_kue_ra = false.
Proof. reflexivity. Qed.

(* --- Genitive examples --- *)

(* §3.6: "Maria ajaka" = Maria's basket *)
Definition ex_maria_ajaka : guarani_np :=
  NP_Gen (NP_Bare (mkNoun "María" Oral EndAEO Uniform))
         (mkNoun "ajaka" Oral EndAEO Uniform).

Example ex_maria_ajaka_wf : wf_np ex_maria_ajaka = true.
Proof. reflexivity. Qed.

Example ex_maria_ajaka_third :
    np_person (np_meta_of ex_maria_ajaka) = Third.
Proof. reflexivity. Qed.

(* §3.6: "mitã sy" = the child's mother *)
Definition ex_mita_sy : guarani_np :=
  NP_Gen (NP_Bare n_mita) n_sy.

Example ex_mita_sy_nasal :
    np_orality (np_meta_of ex_mita_sy) = Nasal.
Proof. reflexivity. Qed.

(* --- Coordination examples --- *)

(* §12.1: "Mario ha Ana" = Mario and Ana → always plural *)
Definition ex_mario_ha_ana : guarani_np :=
  NP_CoordHa
    (NP_Bare (mkNoun "Mario" Oral EndAEO Uniform))
    (NP_Bare (mkNoun "Ana" Oral EndAEO Uniform)).

Example ex_mario_ha_ana_plural :
    np_number (np_meta_of ex_mario_ha_ana) = Plural.
Proof. reflexivity. Qed.

(* --- Negative pronoun examples --- *)

(* §3.5.3: "avave" = nobody (requires double negation) *)
Example ex_avave_is_neg :
    is_negative_pron Indef_Avave = true.
Proof. reflexivity. Qed.

(* --- Plural allomorphy examples --- *)

(* §3.1.1: nasal "mitã" gets "nguéra" *)
Example ex_mita_nguera :
    np_plural_suffix (NP_Bare n_mita) = "nguéra".
Proof. reflexivity. Qed.

(* §3.1.1: oral "óga" gets "kuéra" *)
Example ex_oga_kuera :
    np_plural_suffix (NP_Bare n_oga) = "kuéra".
Proof. reflexivity. Qed.

(* --- Possessive pronoun examples --- *)

(* §3.5.5: "chemba'e" = mine *)
Definition ex_chemba_e : guarani_np := NP_PronPoss Poss1.

Example ex_chemba_e_wf : wf_np ex_chemba_e = true.
Proof. reflexivity. Qed.

Example ex_chemba_e_first :
    np_person (np_meta_of ex_chemba_e) = First.
Proof. reflexivity. Qed.

(* --- Numeral examples --- *)

Definition gn_petei : GuaraniNum :=
  GN_Small (S1000Su_Small (S1000_Small (S100_Digit Peteĩ))).
Definition gn_mbohapy : GuaraniNum :=
  GN_Small (S1000Su_Small (S1000_Small (S100_Digit Mbohapy))).

(* §3.4.3: "peteĩ jagua" = one dog → singular *)
Example ex_petei_singular :
    np_number (np_meta_of (NP_Num gn_petei n_jagua)) = Singular.
Proof. reflexivity. Qed.

(* §3.4.3: "mbohapy ovecha" = three sheep → plural *)
Example ex_mbohapy_plural :
    np_number (np_meta_of (NP_Num gn_mbohapy n_jagua)) = Plural.
Proof. reflexivity. Qed.

(* --- DemPoss example --- *)

(* §3.4.2: "ko che irũ" = this friend of mine *)
Definition ex_ko_che_iru : guarani_np :=
  NP_DemPoss DemProxSpeaker Poss1
    (mkNoun "irũ" Nasal EndIUY Uniform).

Example ex_ko_che_iru_wf : wf_np ex_ko_che_iru = true.
Proof. reflexivity. Qed.

Example ex_ko_che_iru_first :
    np_person (np_meta_of ex_ko_che_iru) = First.
Proof. reflexivity. Qed.

(* --- Interrogative examples --- *)

(* §3.5.2: "mba'e" = what *)
Example ex_mbae_third :
    np_person (np_meta_of (NP_PronInterrog Interrog_Mbae)) = Third.
Proof. reflexivity. Qed.

(* §3.5.2: "mbovy" = how many *)
Example ex_mbovy_renders :
    render_interrog_pron Interrog_Mbovy = "mbovy".
Proof. reflexivity. Qed.