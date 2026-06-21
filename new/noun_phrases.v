From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import Syntax.
Require Import Numbers.
Require Import verb.

(* ============================================================ *)
(*  NounPhrases.v                                               *)
(*  Guaraní noun phrase grammar: nouns, adjectives, pronouns,   *)
(*  demonstratives, determiners, postpositions, nominalizing    *)
(*  suffixes, relative and complement clauses, well-formedness, *)
(*  metadata inference, and surface rendering.                  *)
(* ============================================================ *)


(* ============================================================ *)
(*  1. Root classes                                             *)
(*  §3.1.3 "Relational (multiform) nominal roots"               *)
(*    t- = non-possessed / absolute                             *)
(*    r- = possessed by 1st/2nd person or a full NP possessor   *)
(*    h- = possessed by 3rd person pronominal possessor         *)
(* ============================================================ *)

Inductive root_class : Type :=
  | Uniform       (* no alternation: jagua *)
  | Triform       (* t-/r-/h-: tova/rova/hova *)
  | TriformNoT    (* no t- form: óga/róga/hóga *)
  | Biform        (* túva/ru: kinship with i- for 3rd *)
  | Quadriform.   (* to'o/ro'o/ho'o/so'o *)

Inductive poss_context : Type :=
  | PossCtx_None           (* non-possessed: t- *)
  | PossCtx_FirstSecond    (* 1st/2nd person or NP possessor: r- *)
  | PossCtx_Third.         (* 3rd person pronominal: h- *)

(* §3.1.3: select root prefix from class + context *)
Definition root_prefix (rc : root_class) (ctx : poss_context) : string :=
  match rc, ctx with
  | Uniform,    _                   => ""
  | Triform,    PossCtx_None        => "t"
  | Triform,    PossCtx_FirstSecond => "r"
  | Triform,    PossCtx_Third       => "h"
  | TriformNoT, PossCtx_None        => ""
  | TriformNoT, PossCtx_FirstSecond => "r"
  | TriformNoT, PossCtx_Third       => "h"
  | Biform,     PossCtx_None        => ""
  | Biform,     PossCtx_FirstSecond => "r"
  | Biform,     PossCtx_Third       => ""
  | Quadriform, PossCtx_None        => "t"
  | Quadriform, PossCtx_FirstSecond => "r"
  | Quadriform, PossCtx_Third       => "h"
  end.

(* §3.6: which root context a possessive marker triggers.
   1st/2nd person and plurals -> r- form; 3rd pronominal -> h-. *)
Definition poss_context_of_marker (pm : poss_marker) : poss_context :=
  match pm with
  | Poss1 | Poss1Incl | Poss1Excl | Poss2 | Poss2Pl => PossCtx_FirstSecond
  | Poss3 | Poss3Pl => PossCtx_Third
  end.

(* ============================================================ *)
(*  2. Nouns                                                    *)
(*  §3.1                                                        *)
(* ============================================================ *)

(* §3.1.2: Gender marking. Most nouns are GendNone.
   Fem = kuña modifier; Masc = kuimba'e modifier. *)
Inductive noun_gender : Type :=
  | GendNone
  | GendFem
  | GendMasc.

Record noun : Type := mkNoun {
  n_root       : string;
  n_orality    : orality;
  n_ending     : word_ending;
  n_root_class : root_class;
  n_gender     : noun_gender;  (* §3.1.2 *)
  n_human      : bool           (* §5.1: [+human] -> =pe/=me *)
}.

(* Backward-compat constructor for non-human genderless nouns *)
Definition mkNoun' (r : string) (o : orality) (e : word_ending)
                   (rc : root_class) : noun :=
  mkNoun r o e rc GendNone false.

Definition noun_surface (n : noun) (ctx : poss_context) : string :=
  root_prefix (n_root_class n) ctx ++ n_root n.

(* ============================================================ *)
(*  3. Adjectives                                               *)
(*  §3.3                                                        *)
(* ============================================================ *)

Record adjective : Type := mkAdj {
  a_form       : string;
  a_orality    : orality;
  a_root_class : root_class
}.

(* ============================================================ *)
(*  4. Subject pronouns                                         *)
(*  §3.5.1                                                      *)
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
(*  §3.4.2                                                      *)
(* ============================================================ *)

Inductive dem_set : Type :=
  | DemPresent
  | DemRemoved.

Inductive dem_proximity : Type :=
  | DemProxSpeaker     (* ko *)
  | DemProxHearer      (* pe, upe *)
  | DemDistal          (* amo *)
  | DemSharedPerson    (* ku *)
  | DemSharedEvent     (* ako *)
  | DemHearsay.        (* aipo *)

Definition dem_set_of (prox : dem_proximity) : dem_set :=
  match prox with
  | DemProxSpeaker | DemProxHearer | DemDistal => DemPresent
  | _ => DemRemoved
  end.

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

(* §3.5.4 / §3.2.1.1.3: -va nominalizes demonstratives *)
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
(*  §3.5.3                                                      *)
(* ============================================================ *)

Inductive indef_pron : Type :=
  | Indef_Maymava
  | Indef_Opava
  | Indef_Avave         (* triggers double negation *)
  | Indef_Mbaeve        (* triggers double negation *)
  | Indef_Oimeraeva
  | Indef_Mokoive
  | Indef_Ambueva
  | Indef_PeteiMbae.

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

(* §3.5.3: indefinite pronouns that require double negation *)
Definition is_negative_pron (i : indef_pron) : bool :=
  match i with
  | Indef_Avave | Indef_Mbaeve => true
  | _ => false
  end.

(* ============================================================ *)
(*  7. Interrogative pronouns                                   *)
(*  §3.5.2                                                      *)
(* ============================================================ *)

Inductive interrog_pron : Type :=
  | Interrog_Mbae
  | Interrog_Mava
  | Interrog_Mbaeicha
  | Interrog_Mamo
  | Interrog_Arakae
  | Interrog_Mbaera
  | Interrog_Mbaere
  | Interrog_Mbaegui
  | Interrog_Mbovy
  | Interrog_Avambae.

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
(*  8. Negative pronouns                                        *)
(*  §3.5.3 "all require double negation on the verb"            *)
(* ============================================================ *)

Inductive neg_pron : Type :=
  | NegPron_Mbaeve
  | NegPron_Avave
  | NegPron_NiPetei
  | NegPron_Mamove
  | NegPron_Arakeve
  | NegPron_Maramo.

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
(*  §3.1.1 plural, §3.7 temporal-aspectual, §3.2.2 negation,    *)
(*  §3.2.3 diminutives and attenuatives, §2.2.1 degree          *)
(* ============================================================ *)

Inductive nominal_suffix : Type :=
  (* §3.1.1 *)
  | NS_Plural
  | NS_Multitude
  | NS_Collective
  (* §3.7 *)
  | NS_PastKue
  | NS_FutureRa
  (* §2.2.1.d *)
  | NS_ComparVe
  | NS_Super
  (* §3.2.2, §3.2.3 *)
  | NS_Privative
  | NS_Diminutive
  | NS_Attenuative
  (* §3.2.1.1 *)
  | NS_NomHA
  | NS_NomVA
  | NS_NomPY
  | NS_NomKue
  (* §3.4.3 *)
  | NS_OrdinalHA.

Definition render_nom_suffix (s : nominal_suffix) (o : orality) : string :=
  match s with
  | NS_Plural      => plural_suffix_adj o
  | NS_Multitude   => "eta"
  | NS_Collective  => match o with Oral => "ty" | Nasal => "ndy" end
  | NS_PastKue     => match o with Oral => "kue" | Nasal => "ngue" end
  | NS_FutureRa    => "rã"
  | NS_ComparVe    => "ve"
  | NS_Super       => super_suffix o
  | NS_Privative   => "'ỹ"
  | NS_Diminutive  => "'i"
  | NS_Attenuative => match o with Oral => "vy" | Nasal => "ngy" end
  | NS_NomHA       => "ha"
  | NS_NomVA       => "va"
  | NS_NomPY       => match o with Oral => "py" | Nasal => "mby" end
  | NS_NomKue      => match o with Oral => "kue" | Nasal => "ngue" end
  | NS_OrdinalHA   => "ha"
  end.

(* §3.7: which two-suffix combinations are valid *)
Definition suffix_pair_ok (s1 s2 : nominal_suffix) : bool :=
  match s1, s2 with
  | NS_FutureRa, NS_PastKue  => true     (* -rã + -kue = frustrative *)
  | NS_NomPY,    NS_FutureRa => true     (* -pyrã = future passive *)
  | NS_NomPY,    NS_PastKue  => true     (* -pyre = past passive *)
  | NS_NomHA,    NS_PastKue  => true     (* -hare = past agentive *)
  | NS_NomHA,    NS_FutureRa => true     (* -harã = future agentive *)
  | _, _ => false
  end.

(* ============================================================ *)
(*  10. Postpositions                                           *)
(*  §5                                                          *)
(* ============================================================ *)

Inductive postposition : Type :=
  | Post_Pe | Post_Gui | Post_Gua | Post_Rehe | Post_Ndive
  | Post_Guive | Post_Peve | Post_Rupi | Post_Ari | Post_Guy
  | Post_Guara | Post_Hagua.

Definition postposition_form (o : orality) (p : postposition) : string :=
  match p with
  | Post_Pe    => match o with Oral => "pe"    | Nasal => "me"    end
  | Post_Gui   => "gui"
  | Post_Gua   => "gua"
  | Post_Rehe  => "rehe"
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
(*  11. NP metadata for verb agreement                          *)
(* ============================================================ *)

Record np_meta : Type := mkNPMeta {
  np_orality     : orality;
  np_number      : number;
  np_person      : person;
  np_inclusivity : option inclusivity
}.

(* ============================================================ *)
(*  12. Embedded clauses                                        *)
(*  §3.2.1.1.3 / §12.2.1: relative clauses end in -va           *)
(*  §3.2.1.1.1 / §12.2.2: complement clauses end in -ha         *)
(* ============================================================ *)

Definition embedded_clause : Type := conjugated_verb.

Definition is_rel_clause (cv : conjugated_verb) : bool :=
  has_verbal_suffix (cv_suffixes cv) VS_NomVa.

Definition is_comp_clause (cv : conjugated_verb) : bool :=
  has_verbal_suffix (cv_suffixes cv) VS_NomHa.

(* ============================================================ *)
(*  13. Noun phrase AST                                         *)
(*  §3.1 NP order:                                              *)
(*    (det/dem/num/quant) + (possessor) + head noun +           *)
(*    (adjective) + (relative clause)                           *)
(* ============================================================ *)

Inductive guarani_np : Type :=
  (* --- Noun-headed --- *)
  | NP_Bare    : noun -> guarani_np
  | NP_Dem     : dem_proximity -> number -> noun -> guarani_np
  | NP_Art     : number -> noun -> guarani_np    (* la/lo; not rendered *)
  | NP_Adj     : noun -> adjective -> guarani_np
  | NP_Poss    : poss_marker -> noun -> guarani_np
  | NP_Num     : GuaraniNum -> noun -> guarani_np
  | NP_Gen     : guarani_np -> noun -> guarani_np
  | NP_DemPoss : dem_proximity -> poss_marker -> noun -> guarani_np
  | NP_Rel     : noun -> embedded_clause -> guarani_np
  | NP_Comp    : embedded_clause -> guarani_np

  (* --- Suffix attachment --- *)
  | NP_Suf     : guarani_np -> nominal_suffix -> guarani_np
  | NP_Suf2    : guarani_np -> nominal_suffix -> nominal_suffix -> guarani_np

  (* --- Standalone pronouns --- *)
  | NP_PronSubj     : subj_pronoun  -> guarani_np
  | NP_PronPoss     : poss_marker   -> guarani_np
  | NP_PronDem      : dem_proximity -> number -> guarani_np
  | NP_PronIndef    : indef_pron    -> guarani_np
  | NP_PronInterrog : interrog_pron -> guarani_np
  | NP_PronNeg      : neg_pron      -> guarani_np

  (* --- Coordination §12.1 --- *)
  | NP_CoordHa   : guarani_np -> guarani_np -> guarani_np
  | NP_CoordTera : guarani_np -> guarani_np -> guarani_np.

(* ============================================================ *)
(*  14. Well-formedness predicate                               *)
(* ============================================================ *)

Fixpoint is_noun_headed (x : guarani_np) : bool :=
  match x with
  | NP_Bare _ | NP_Dem _ _ _ | NP_Art _ _ | NP_Adj _ _
  | NP_Poss _ _ | NP_Num _ _ | NP_Gen _ _ | NP_DemPoss _ _ _
  | NP_Rel _ _ | NP_Comp _ => true
  | NP_Suf inner _     => is_noun_headed inner
  | NP_Suf2 inner _ _  => is_noun_headed inner
  | _ => false
  end.

Fixpoint has_suffix (x : guarani_np) : bool :=
  match x with
  | NP_Suf _ _    => true
  | NP_Suf2 _ _ _ => true
  | _             => false
  end.

(* Well-formed NP:
   - NP_Rel: clause is wf and ends in -va
   - NP_Comp: clause is wf and ends in -ha
   - NP_Suf only on noun-headed, no prior suffix
   - NP_Suf2: same, plus valid ordered pair §3.7
   - coordinands recursively wf *)
Fixpoint wf_np (x : guarani_np) : bool :=
  match x with
  | NP_Bare _ | NP_Dem _ _ _ | NP_Art _ _ | NP_Adj _ _
  | NP_Poss _ _ | NP_Num _ _ | NP_DemPoss _ _ _ => true

  | NP_Gen poss _ => wf_np poss

  | NP_Rel  _ cv => wf_conjugated_verb cv && is_rel_clause  cv
  | NP_Comp   cv => wf_conjugated_verb cv && is_comp_clause cv

  | NP_Suf inner _ =>
      is_noun_headed inner && negb (has_suffix inner) && wf_np inner

  | NP_Suf2 inner s1 s2 =>
      is_noun_headed inner && negb (has_suffix inner) && wf_np inner
      && suffix_pair_ok s1 s2

  | NP_PronSubj _ | NP_PronPoss _ | NP_PronDem _ _
  | NP_PronIndef _ | NP_PronInterrog _ | NP_PronNeg _ => true

  | NP_CoordHa   x1 x2
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

  | NP_Comp cv =>
      mkNPMeta (cv_orality cv) Singular Third None

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
               None

  | NP_CoordTera x1 _ =>
      np_meta_of x1
  end.

Definition np_plural_suffix (x : guarani_np) : string :=
  plural_suffix_adj (np_orality (np_meta_of x)).

(* ============================================================ *)
(*  17. Surface rendering                                                       *)
(* ============================================================ *)

Fixpoint render_np (x : guarani_np) : string :=
  match x with
  | NP_Bare n =>
      noun_surface n PossCtx_None

  | NP_Dem prox num n =>
      dem_adj_form prox num ++ " " ++ noun_surface n PossCtx_None

  | NP_Art _ n =>
      noun_surface n PossCtx_None

  | NP_Adj n a =>
      noun_surface n PossCtx_None ++ " " ++ a_form a

  | NP_Poss pm n =>
      poss_marker_form (n_orality n) pm
      ++ " "
      ++ noun_surface n (poss_context_of_marker pm)

  | NP_Num gn n =>
      render_num gn ++ " " ++ noun_surface n PossCtx_None

  | NP_Gen poss n =>
      render_np poss ++ " " ++ noun_surface n PossCtx_FirstSecond

  | NP_DemPoss prox pm n =>
      dem_adj_form prox Singular
      ++ " "
      ++ poss_marker_form (n_orality n) pm
      ++ " "
      ++ noun_surface n (poss_context_of_marker pm)

  | NP_Rel n cv =>
      noun_surface n PossCtx_None ++ " " ++ render_verb cv

  | NP_Comp cv =>
      render_verb cv

  | NP_Suf inner suf =>
      render_np inner
      ++ render_nom_suffix suf (np_orality (np_meta_of inner))

  | NP_Suf2 inner s1 s2 =>
      let o := np_orality (np_meta_of inner) in
      render_np inner
      ++ render_nom_suffix s1 o
      ++ render_nom_suffix s2 o

  | NP_PronSubj p =>
      render_subj_pronoun p

  | NP_PronPoss pm =>
      (* §3.5.5: poss_marker + mba'e — host word "mba'e" is oral *)
      poss_marker_form Oral pm ++ "mba'e"

  | NP_PronDem prox num =>
      dem_pron_form prox num

  | NP_PronIndef i =>
      render_indef_pron i

  | NP_PronInterrog i =>
      render_interrog_pron i

  | NP_PronNeg np =>
      render_neg_pron np

  | NP_CoordHa x1 x2 =>
      render_np x1 ++ " ha " ++ render_np x2

  | NP_CoordTera x1 x2 =>
      render_np x1 ++ " térã " ++ render_np x2
  end.

(* ============================================================ *)
(*  18. Decidable equality                                      *)
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
(*  19. Theorems                                                *)
(* ============================================================ *)

(* ---------- NP-A: Root-class prefix selection §3.1.3 ---------- *)

Theorem rule_NPA1_triform_nonposs_is_t :
    root_prefix Triform PossCtx_None = "t".
Proof. reflexivity. Qed.

Theorem rule_NPA2_triform_firstsecond_is_r :
    root_prefix Triform PossCtx_FirstSecond = "r".
Proof. reflexivity. Qed.

Theorem rule_NPA3_triform_third_is_h :
    root_prefix Triform PossCtx_Third = "h".
Proof. reflexivity. Qed.

Theorem rule_NPA4_triform_all_distinct :
    root_prefix Triform PossCtx_None <> root_prefix Triform PossCtx_FirstSecond /\
    root_prefix Triform PossCtx_FirstSecond <> root_prefix Triform PossCtx_Third /\
    root_prefix Triform PossCtx_None <> root_prefix Triform PossCtx_Third.
Proof. simpl. repeat split; discriminate. Qed.

Theorem rule_NPA5_triformNoT_nonposs_empty :
    root_prefix TriformNoT PossCtx_None = "".
Proof. reflexivity. Qed.

Theorem rule_NPA6_triformNoT_firstsecond_is_r :
    root_prefix TriformNoT PossCtx_FirstSecond = "r".
Proof. reflexivity. Qed.

Theorem rule_NPA6_triformNoT_third_is_h :
    root_prefix TriformNoT PossCtx_Third = "h".
Proof. reflexivity. Qed.

Theorem rule_NPA7_uniform_always_empty : forall ctx,
    root_prefix Uniform ctx = "".
Proof. intros ctx; destruct ctx; reflexivity. Qed.

(* ---------- NP-B: Well-formedness ---------- *)

Theorem rule_NPB1_bare_wf : forall n, wf_np (NP_Bare n) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_dem_wf : forall prox num n,
    wf_np (NP_Dem prox num n) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_adj_wf : forall n a, wf_np (NP_Adj n a) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_poss_wf : forall pm n, wf_np (NP_Poss pm n) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB1_num_wf : forall gn n, wf_np (NP_Num gn n) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB2_single_suffix_wf : forall n suf,
    wf_np (NP_Suf (NP_Bare n) suf) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB3_double_suf_stacking_ill : forall n s1 s2,
    wf_np (NP_Suf (NP_Suf (NP_Bare n) s1) s2) = false.
Proof. reflexivity. Qed.

Theorem rule_NPB4_suffix_on_pronoun_ill : forall p suf,
    wf_np (NP_Suf (NP_PronSubj p) suf) = false.
Proof. reflexivity. Qed.

Theorem rule_NPB5_gen_preserves : forall poss n,
    wf_np poss = true -> wf_np (NP_Gen poss n) = true.
Proof. intros poss n H. simpl. exact H. Qed.

Theorem rule_NPB6_subj_pron_wf : forall p, wf_np (NP_PronSubj p) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB6_interrog_pron_wf : forall i, wf_np (NP_PronInterrog i) = true.
Proof. reflexivity. Qed.

Theorem rule_NPB6_neg_pron_wf : forall np, wf_np (NP_PronNeg np) = true.
Proof. reflexivity. Qed.

(* NP-B7: relative/complement clause wf delegates to the embedded
   conjugated_verb plus a suffix shape check. *)
Theorem rule_NPB7_rel_wf_iff : forall n cv,
    wf_np (NP_Rel n cv) = wf_conjugated_verb cv && is_rel_clause cv.
Proof. reflexivity. Qed.

Theorem rule_NPB7_comp_wf_iff : forall cv,
    wf_np (NP_Comp cv) = wf_conjugated_verb cv && is_comp_clause cv.
Proof. reflexivity. Qed.

(* §3.2.1.1.3: a relative clause without -va is ill-formed *)
Theorem rule_NPB8_rel_needs_va : forall n cv,
    is_rel_clause cv = false ->
    wf_np (NP_Rel n cv) = false.
Proof.
  intros n cv H. simpl. rewrite H.
  destruct (wf_conjugated_verb cv); reflexivity.
Qed.

(* §3.2.1.1.1: a complement clause without -ha is ill-formed *)
Theorem rule_NPB8_comp_needs_ha : forall cv,
    is_comp_clause cv = false ->
    wf_np (NP_Comp cv) = false.
Proof.
  intros cv H. simpl. rewrite H.
  destruct (wf_conjugated_verb cv); reflexivity.
Qed.

(* ---------- NP-C: Suffix ordering §3.7 ---------- *)

Theorem rule_NPC1_ra_then_kue_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_FutureRa NS_PastKue) = true.
Proof. reflexivity. Qed.

Theorem rule_NPC2_kue_then_ra_invalid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_PastKue NS_FutureRa) = false.
Proof. reflexivity. Qed.

Theorem rule_NPC3_ha_then_kue_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomHA NS_PastKue) = true.
Proof. reflexivity. Qed.

Theorem rule_NPC4_ha_then_ra_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomHA NS_FutureRa) = true.
Proof. reflexivity. Qed.

Theorem rule_NPC5_py_then_kue_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomPY NS_PastKue) = true.
Proof. reflexivity. Qed.

Theorem rule_NPC6_py_then_ra_valid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_NomPY NS_FutureRa) = true.
Proof. reflexivity. Qed.

Theorem rule_NPC7_double_plural_invalid : forall n,
    wf_np (NP_Suf2 (NP_Bare n) NS_Plural NS_Plural) = false.
Proof. reflexivity. Qed.

(* ---------- NP-D / E / F / G / H / I / J / K / L / M / N / O / P ---------- *)

Theorem rule_NPD1_subj_person_consistent : forall p,
    np_person (np_meta_of (NP_PronSubj p)) = person_of_subj p.
Proof. intros p; destruct p; reflexivity. Qed.

Theorem rule_NPD3_subj_pron_always_oral : forall p,
    np_orality (np_meta_of (NP_PronSubj p)) = Oral.
Proof. intros p; destruct p; reflexivity. Qed.

Theorem rule_NPE1_bare_always_third : forall n,
    np_person (np_meta_of (NP_Bare n)) = Third.
Proof. reflexivity. Qed.

Theorem rule_NPE2_bare_always_singular : forall n,
    np_number (np_meta_of (NP_Bare n)) = Singular.
Proof. reflexivity. Qed.

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

Theorem rule_NPG1_prox_singular :
    dem_adj_form DemProxSpeaker Singular = "ko".
Proof. reflexivity. Qed.

Theorem rule_NPG3_prox_plural_is_koa :
    dem_adj_form DemProxSpeaker Plural = "ko'ã".
Proof. reflexivity. Qed.

Theorem rule_NPG6_dem_np_always_third : forall prox num n,
    np_person (np_meta_of (NP_Dem prox num n)) = Third.
Proof. reflexivity. Qed.

Theorem rule_NPH1_plural_forces_plural : forall x,
    np_number (np_meta_of (NP_Suf x NS_Plural)) = Plural.
Proof. reflexivity. Qed.

Theorem rule_NPH4_kue_transparent : forall x,
    np_meta_of (NP_Suf x NS_PastKue) = np_meta_of x.
Proof. reflexivity. Qed.

Theorem rule_NPI1_gen_always_third : forall poss n,
    np_person (np_meta_of (NP_Gen poss n)) = Third.
Proof. reflexivity. Qed.

Theorem rule_NPJ1_poss_person_from_marker : forall pm n,
    np_person (np_meta_of (NP_Poss pm n)) = person_of_poss pm.
Proof. intros pm n; destruct pm; reflexivity. Qed.

Theorem rule_NPK1_one_is_singular : forall gn n,
    is_one gn = true -> np_number (np_meta_of (NP_Num gn n)) = Singular.
Proof. intros gn n H. simpl. rewrite H. reflexivity. Qed.

Theorem rule_NPK2_not_one_is_plural : forall gn n,
    is_one gn = false -> np_number (np_meta_of (NP_Num gn n)) = Plural.
Proof. intros gn n H. simpl. rewrite H. reflexivity. Qed.

Theorem rule_NPL1_ha_always_plural : forall x1 x2,
    np_number (np_meta_of (NP_CoordHa x1 x2)) = Plural.
Proof. reflexivity. Qed.

Theorem rule_NPM1_merge_commutative : forall p1 p2,
    person_merge p1 p2 = person_merge p2 p1.
Proof. intros p1 p2; destruct p1; destruct p2; reflexivity. Qed.

Theorem rule_NPM3_first_always_dominates : forall p,
    person_merge First p = First /\ person_merge p First = First.
Proof. intros p; destruct p; split; reflexivity. Qed.

Theorem rule_NPN1_pe_me_oral :
    postposition_form Oral Post_Pe = "pe".
Proof. reflexivity. Qed.

Theorem rule_NPN1_pe_me_nasal :
    postposition_form Nasal Post_Pe = "me".
Proof. reflexivity. Qed.

Theorem rule_NPO1_avave_is_negative :
    is_negative_pron Indef_Avave = true.
Proof. reflexivity. Qed.

Theorem rule_NPO2_maymava_not_negative :
    is_negative_pron Indef_Maymava = false.
Proof. reflexivity. Qed.

Theorem rule_NPP2_interrog_always_third : forall i,
    np_person (np_meta_of (NP_PronInterrog i)) = Third.
Proof. reflexivity. Qed.

(* ---------- NP-Q: Rendering sanity checks ---------- *)

Theorem rule_NPQ1_uniform_bare_is_root : forall n,
    n_root_class n = Uniform ->
    render_np (NP_Bare n) = n_root n.
Proof.
  intros n H. unfold render_np, noun_surface.
  rewrite H. simpl. reflexivity.
Qed.

Theorem rule_NPQ2_art_drops_article : forall num n,
    render_np (NP_Art num n) = render_np (NP_Bare n).
Proof. reflexivity. Qed.

Theorem rule_NPQ3_pron_subj_renders : forall p,
    render_np (NP_PronSubj p) = render_subj_pronoun p.
Proof. intros p; destruct p; reflexivity. Qed.

Theorem rule_NPQ4_coord_ha_joins_with_ha : forall x1 x2,
    render_np (NP_CoordHa x1 x2)
    = render_np x1 ++ " ha " ++ render_np x2.
Proof. reflexivity. Qed.

Theorem rule_NPQ5_rel_concats_with_verb : forall n cv,
    render_np (NP_Rel n cv)
    = noun_surface n PossCtx_None ++ " " ++ render_verb cv.
Proof. reflexivity. Qed.

Theorem rule_NPQ6_comp_is_verb : forall cv,
    render_np (NP_Comp cv) = render_verb cv.
Proof. reflexivity. Qed.

