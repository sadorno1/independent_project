From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import Primitives.

(* ============================================================ *)
(*  Verb.v                                                      *)
(*  Guaraní verb morphology: types, conjugation, voice,         *)
(*  negation, tense/aspect/mood, object pronouns, transitivity, *)
(*  person hierarchy, relational verbs, imperative modalizers,  *)
(*  affix ordering, well-formedness, and rendering.             *)
(*                                                              *)
(*  Primary reference: "A Grammar of Paraguayan Guarani"        *)
(*  Chapters 4 (Verbs), 6 (Voice), 14 (Affix ordering)         *)
(* ============================================================ *)


(* ============================================================ *)
(*  1. Verb classification                                      *)
(* ============================================================ *)

Inductive verb_class : Type :=
  | Areal
  | Aireal
  | Chendal.

(* ============================================================ *)
(*  2. Transitivity                                             *)
(* ============================================================ *)

Inductive transitivity : Type :=
  | Intransitive
  | Transitive
  | Ditransitive
  | PostpComplement.

(* ============================================================ *)
(*  3. Root class for verbs                                     *)
(* ============================================================ *)

Inductive verb_root_class : Type :=
  | VRoot_Plain
  | VRoot_Relational.

Inductive prefix_type : Type :=
  | PfxActive
  | PfxInactive
  | PfxImperative
  | PfxPortmanteau.

Definition verb_relational_prefix (rc : verb_root_class)
                                  (pt : prefix_type) : string :=
  match rc with
  | VRoot_Plain => ""
  | VRoot_Relational =>
      match pt with
      | PfxActive      => "h"
      | PfxInactive    => "r"
      | PfxImperative  => "h"
      | PfxPortmanteau => "h"
      end
  end.

(* ============================================================ *)
(*  4. Voice                                                    *)
(* ============================================================ *)

Inductive voice : Type :=
  | Active
  | Passive
  | Reciprocal
  | Coactive
  | Objective
  | Subsuntive.

Definition voice_prefix (vc : voice) (o : orality) : string :=
  match vc with
  | Active     => ""
  | Passive    => passive_prefix o
  | Reciprocal => reciprocal_prefix o
  | Coactive   => coactive_prefix o
  | Objective  => "ro"
  | Subsuntive => "poro"
  end.

(* ============================================================ *)
(*  5. Mood                                                     *)
(* ============================================================ *)

Inductive mood : Type :=
  | Indicative
  | Imperative
  | Optative
  | Prohibitive.

(* ============================================================ *)
(*  6. Polarity                                                 *)
(* ============================================================ *)

Inductive polarity : Type :=
  | Positive
  | Negative.

(* ============================================================ *)
(*  7. Verbal suffixes                                          *)
(* ============================================================ *)

Inductive verbal_suffix : Type :=
  | VS_CausUka
  | VS_AbilKuaa
  | VS_TotalPa
  | VS_ImpForce
  | VS_ImpRequest
  | VS_ImpPlead
  | VS_ImpUrge
  | VS_Volitive
  | VS_ComparVe
  | VS_FutTa
  | VS_FutNe
  | VS_FutNegMoa
  | VS_ImmFutPota
  | VS_ObligVaera
  | VS_PastVaekue
  | VS_NegI
  | VS_NegRi
  | VS_NegTei
  | VS_Privative
  | VS_Intensifier
  | VS_NomVa
  | VS_NomHa
  | VS_AspectMa
  | VS_IterJevy
  | VS_HabitMi
  | VS_HabitVa
  | VS_FrustrRei
  | VS_InterrogPa
  | VS_Desiderative.

(* ============================================================ *)
(*  7a. Suffix classification predicates                        *)
(* ============================================================ *)

Definition is_neg_suffix (s : verbal_suffix) : bool :=
  match s with
  | VS_NegI | VS_NegRi | VS_NegTei | VS_Privative => true
  | _ => false
  end.

Definition is_future_suffix (s : verbal_suffix) : bool :=
  match s with
  | VS_FutTa | VS_FutNe | VS_FutNegMoa | VS_ImmFutPota => true
  | _ => false
  end.

Definition is_imp_modalizer (s : verbal_suffix) : bool :=
  match s with
  | VS_ImpForce | VS_ImpRequest | VS_ImpPlead | VS_ImpUrge => true
  | _ => false
  end.

Definition is_tense_suffix (s : verbal_suffix) : bool :=
  match s with
  | VS_FutTa | VS_FutNe | VS_FutNegMoa | VS_ImmFutPota
  | VS_ObligVaera | VS_PastVaekue => true
  | _ => false
  end.

Definition is_nominalizer (s : verbal_suffix) : bool :=
  match s with
  | VS_NomVa | VS_NomHa => true
  | _ => false
  end.

(* ============================================================ *)
(*  7b. Suffix rendering                                        *)
(* ============================================================ *)

Definition render_verbal_suffix (s : verbal_suffix) (o : orality) : string :=
  match s with
  | VS_CausUka    => "uka"
  | VS_AbilKuaa   => "kuaa"
  | VS_TotalPa    => totalitative_suffix o
  | VS_ImpForce   => "ke"
  | VS_ImpRequest => "na"
  | VS_ImpPlead   => "mi"
  | VS_ImpUrge    => "py"
  | VS_Volitive   => "se"
  | VS_ComparVe   => "ve"
  | VS_FutTa      => "ta"
  | VS_FutNe      => "ne"
  | VS_FutNegMoa  => "mo'ã"
  | VS_ImmFutPota => match o with Oral => "pota" | Nasal => "mbota" end
  | VS_ObligVaera  => "va'erã"
  | VS_PastVaekue => "va'ekue"
  | VS_NegI       => "i"
  | VS_NegRi      => "ri"
  | VS_NegTei     => "tei"
  | VS_Privative  => "'ỹ"
  | VS_Intensifier => match o with Oral => "ite" | Nasal => "ete" end
  | VS_NomVa      => "va"
  | VS_NomHa      => "ha"
  | VS_AspectMa   => "ma"
  | VS_IterJevy   => "jevy"
  | VS_HabitMi    => "mi"
  | VS_HabitVa    => "va"
  | VS_FrustrRei  => "rei"
  | VS_InterrogPa => "pa"
  | VS_Desiderative => "nga'u"
  end.

(* ============================================================ *)
(*  8. Affix ordering                                           *)
(* ============================================================ *)

Definition suffix_slot (s : verbal_suffix) : nat :=
  match s with
  | VS_CausUka      =>  1
  | VS_AbilKuaa     =>  2
  | VS_TotalPa      =>  3
  | VS_ImpForce     =>  4
  | VS_ImpRequest   =>  4
  | VS_ImpPlead     =>  4
  | VS_ImpUrge      =>  4
  | VS_Volitive     =>  5
  | VS_ComparVe     =>  6
  | VS_FutTa        =>  7
  | VS_FutNe        =>  7
  | VS_FutNegMoa    =>  7
  | VS_ImmFutPota   =>  7
  | VS_ObligVaera   =>  7
  | VS_PastVaekue   =>  7
  | VS_NegI         =>  8
  | VS_NegRi        =>  8
  | VS_NegTei       =>  8
  | VS_Privative    =>  8
  | VS_Intensifier  =>  9
  | VS_NomVa        => 10
  | VS_NomHa        => 10
  | VS_AspectMa     => 11
  | VS_IterJevy     => 11
  | VS_HabitMi      => 11
  | VS_HabitVa      => 11
  | VS_FrustrRei    => 11
  | VS_InterrogPa   => 12
  | VS_Desiderative => 11
  end.

Fixpoint suffixes_ordered (ss : list verbal_suffix) : bool :=
  match ss with
  | nil => true
  | _ :: nil => true
  | s1 :: ((s2 :: _) as rest) =>
      Nat.leb (suffix_slot s1) (suffix_slot s2) && suffixes_ordered rest
  end.

(* ============================================================ *)
(*  9. Person hierarchy for transitive verbs                    *)
(* ============================================================ *)

Definition person_rank (p : person) : nat :=
  match p with
  | First  => 1
  | Second => 2
  | Third  => 3
  end.

Definition subj_outranks_obj (subj_p obj_p : person) : bool :=
  Nat.leb (person_rank subj_p) (person_rank obj_p).

Inductive portmanteau_config : Type :=
  | Port_1to2sg
  | Port_1to2pl.

Definition render_portmanteau (pc : portmanteau_config) : string :=
  match pc with
  | Port_1to2sg => "ro"
  | Port_1to2pl => "po"
  end.

Inductive trans_prefix_mode : Type :=
  | TPM_Active
  | TPM_Inactive
  | TPM_Portmanteau : portmanteau_config -> trans_prefix_mode
  | TPM_Reflexive.

Definition trans_prefix_selection (subj_p : person) (subj_n : number)
                                  (obj_p : person) (obj_n : number)
                                  : trans_prefix_mode :=
  match subj_p, obj_p with
  | First, First   => TPM_Reflexive
  | Second, Second => TPM_Reflexive
  | Third, Third   => TPM_Active
  | First, Second  =>
      match obj_n with
      | Singular => TPM_Portmanteau Port_1to2sg
      | Plural   => TPM_Portmanteau Port_1to2pl
      end
  | First, Third   => TPM_Active
  | Second, First  => TPM_Inactive
  | Second, Third  => TPM_Active
  | Third, First   => TPM_Inactive
  | Third, Second  => TPM_Inactive
  end.

(* ============================================================ *)
(*  10. Object pronouns                                         *)
(* ============================================================ *)

Inductive obj_pron_post : Type :=
  | ObjPost_Chupe
  | ObjPost_Ichupe
  | ObjPost_ChupeKuera
  | ObjPost_IchupeKuera.

Definition render_obj_post (p : obj_pron_post) : string :=
  match p with
  | ObjPost_Chupe       => "chupe"
  | ObjPost_Ichupe      => "ichupe"
  | ObjPost_ChupeKuera  => "chupe kuéra"
  | ObjPost_IchupeKuera => "ichupe kuéra"
  end.

Inductive obj_indirect : Type :=
  | ObjInd_Cheve
  | ObjInd_Ndeve
  | ObjInd_Chupe
  | ObjInd_Nandeve
  | ObjInd_Oreve
  | ObjInd_Peeme
  | ObjInd_ChupeKuera.

Definition render_obj_indirect (p : obj_indirect) : string :=
  match p with
  | ObjInd_Cheve       => "chéve"
  | ObjInd_Ndeve       => "ndéve"
  | ObjInd_Chupe       => "chupe"
  | ObjInd_Nandeve     => "ñandéve"
  | ObjInd_Oreve       => "oréve"
  | ObjInd_Peeme       => "peẽme"
  | ObjInd_ChupeKuera  => "chupe kuéra"
  end.

(* ============================================================ *)
(*  11. Verb record and verb_form dispatch                      *)
(* ============================================================ *)

Record verb : Type := mkVerb {
  v_class        : verb_class;
  v_orality      : orality;
  v_root         : string;
  v_transitivity : transitivity;
  v_root_class   : verb_root_class
}.

(* §4.5: Irregular verbs with root allomorphs *)
Inductive irregular_verb : Type :=
  | Irreg_Ju
  | Irreg_Ho
  | Irreg_E.

(* verb_form: regular verbs carry a verb record;
   irregular verbs are fully enumerated.
   Sentences.v calls render_verb without needing to
   know about the regular/irregular distinction. *)
Inductive verb_form : Type :=
  | VF_Regular   : verb -> verb_form
  | VF_Irregular : irregular_verb -> verb_form.

(* ============================================================ *)
(*  12. Agreement prefix selection                              *)
(* ============================================================ *)

Definition areal_ind_prefix (p : person) (n : number)
                            (incl : option inclusivity)
                            (o : orality) : string :=
  match p, n, incl with
  | First,  Singular, _             => "a"
  | Second, Singular, _             => "re"
  | Third,  _,        _             => "o"
  | First,  Plural,   Some Inclusive =>
      match o with Oral => "ja" | Nasal => "ña" end
  | First,  Plural,   Some Exclusive => "ro"
  | First,  Plural,   None          => "ro"
  | Second, Plural,   _             => "pe"
  end.

Definition aireal_ind_prefix (p : person) (n : number)
                             (incl : option inclusivity)
                             (o : orality) : string :=
  match p, n, incl with
  | First,  Singular, _             => "ai"
  | Second, Singular, _             => "rei"
  | Third,  _,        _             => "oi"
  | First,  Plural,   Some Inclusive =>
      match o with Oral => "jai" | Nasal => "ñai" end
  | First,  Plural,   Some Exclusive => "roi"
  | First,  Plural,   None          => "roi"
  | Second, Plural,   _             => "pei"
  end.

Definition chendal_ind_prefix (p : person) (n : number)
                              (incl : option inclusivity)
                              (o : orality) : string :=
  match p, n, incl with
  | First,  Singular, _             => "che"
  | Second, Singular, _             =>
      match o with Oral => "nde" | Nasal => "ne" end
  | Third,  Singular, _             =>
      match o with Oral => "i" | Nasal => "iñ" end
  | Third,  Plural,   _             =>
      match o with Oral => "i" | Nasal => "iñ" end
  | First,  Plural,   Some Inclusive =>
      match o with Oral => "ñande" | Nasal => "ñane" end
  | First,  Plural,   Some Exclusive => "ore"
  | First,  Plural,   None          => "ore"
  | Second, Plural,   _             =>
      match o with Oral => "pende" | Nasal => "pene" end
  end.

Definition imp_prefix (cls : verb_class) (p : person) (n : number)
                      (incl : option inclusivity) (o : orality) : string :=
  match cls, p, n with
  | Areal,  Second, Singular => "e"
  | Aireal, Second, Singular => "e"
  | _, _, _ =>
      match cls with
      | Areal   => areal_ind_prefix p n incl o
      | Aireal  => aireal_ind_prefix p n incl o
      | Chendal => chendal_ind_prefix p n incl o
      end
  end.

Definition opt_prefix (cls : verb_class) (p : person) (n : number)
                      (incl : option inclusivity)
                      (o : orality) : string :=
  match cls with
  | Chendal =>
      "ta" ++ chendal_ind_prefix p n incl o
  | _ =>
      match p, n, incl with
      | First,  Singular, _             => "ta"
      | Second, Singular, _             => "te"
      | Third,  _,        _             => "to"
      | First,  Plural,   Some Inclusive =>
          match o with Oral => "taja" | Nasal => "taña" end
      | First,  Plural,   Some Exclusive => "toro"
      | First,  Plural,   None          => "toro"
      | Second, Plural,   _             => "tape"
      end
  end.

Definition agr_prefix (cls : verb_class) (md : mood)
                       (p : person) (n : number)
                       (incl : option inclusivity)
                       (o : orality) : string :=
  match md with
  | Optative    => opt_prefix cls p n incl o
  | Imperative  => imp_prefix cls p n incl o
  | Indicative | Prohibitive =>
      match cls with
      | Areal   => areal_ind_prefix p n incl o
      | Aireal  => aireal_ind_prefix p n incl o
      | Chendal => chendal_ind_prefix p n incl o
      end
  end.

(* ============================================================ *)
(*  13. Negation prefix                                         *)
(* ============================================================ *)

Definition neg_prefix_for (o : orality) : string :=
  neg_prefix o.

Definition neg_eufonic (cls : verb_class) (p : person) (n : number)
                       (incl : option inclusivity) : string :=
  match cls with
  | Chendal => "a"
  | Areal | Aireal =>
      match p, n, incl with
      | First,  Singular, _             => "a"
      | Second, Singular, _             => "e"
      | Third,  _,        _             => "o"
      | First,  Plural,   Some Inclusive => "a"
      | First,  Plural,   Some Exclusive => "o"
      | First,  Plural,   None          => "o"
      | Second, Plural,   _             => "a"
      end
  end.

(* ============================================================ *)
(*  14. Irregular verb forms                                    *)
(* ============================================================ *)

Definition irreg_form (iv : irregular_verb) (p : person) (n : number)
                      (incl : option inclusivity) : string :=
  match iv, p, n, incl with
  | Irreg_Ju, First,  Singular, _             => "aju"
  | Irreg_Ju, Second, Singular, _             => "reju"
  | Irreg_Ju, Third,  Singular, _             => "ou"
  | Irreg_Ju, Third,  Plural,   _             => "ou"
  | Irreg_Ju, First,  Plural,   Some Inclusive => "jaju"
  | Irreg_Ju, First,  Plural,   Some Exclusive => "roju"
  | Irreg_Ju, First,  Plural,   None          => "roju"
  | Irreg_Ju, Second, Plural,   _             => "peju"
  | Irreg_Ho, First,  Singular, _             => "aha"
  | Irreg_Ho, Second, Singular, _             => "reho"
  | Irreg_Ho, Third,  Singular, _             => "oho"
  | Irreg_Ho, Third,  Plural,   _             => "oho"
  | Irreg_Ho, First,  Plural,   Some Inclusive => "jaha"
  | Irreg_Ho, First,  Plural,   Some Exclusive => "roho"
  | Irreg_Ho, First,  Plural,   None          => "roho"
  | Irreg_Ho, Second, Plural,   _             => "peho"
  | Irreg_E, First,  Singular, _             => "ha'e"
  | Irreg_E, Second, Singular, _             => "ere"
  | Irreg_E, Third,  Singular, _             => "he'i"
  | Irreg_E, Third,  Plural,   _             => "he'i"
  | Irreg_E, First,  Plural,   Some Inclusive => "ja'e"
  | Irreg_E, First,  Plural,   Some Exclusive => "ro'e"
  | Irreg_E, First,  Plural,   None          => "ro'e"
  | Irreg_E, Second, Plural,   _             => "peje"
  end.

(* ============================================================ *)
(*  15. Conjugated verb structure                               *)
(*                                                              *)
(*  cv_verb_form holds a verb_form (regular or irregular).      *)
(*  Sentences.v and callers use render_verb without needing     *)
(*  to case-split on regularity.                                *)
(* ============================================================ *)

Record conjugated_verb : Type := mkConjVerb {
  cv_verb_form : verb_form;
  cv_person    : person;
  cv_number    : number;
  cv_incl      : option inclusivity;
  cv_mood      : mood;
  cv_polarity  : polarity;
  cv_voice     : voice;
  cv_suffixes  : list verbal_suffix
}.

(* Convenience accessor: orality of the verb form.
   Irregular verbs are all oral (§4.5). *)
Definition cv_orality (cv : conjugated_verb) : orality :=
  match cv_verb_form cv with
  | VF_Regular v  => v_orality v
  | VF_Irregular _ => Oral
  end.

(* ============================================================ *)
(*  16. Well-formedness: factored predicates                    *)
(*                                                              *)
(*  Each predicate captures one orthogonal grammatical          *)
(*  constraint. wf_conjugated_verb is their conjunction.        *)
(*  Proofs about individual constraints use only the relevant   *)
(*  predicate — no need to destruct through the full product.   *)
(* ============================================================ *)

(* --- Suffix list utilities --- *)

Definition verbal_suffix_eqb (s1 s2 : verbal_suffix) : bool :=
  match s1, s2 with
  | VS_CausUka,     VS_CausUka     => true
  | VS_AbilKuaa,    VS_AbilKuaa    => true
  | VS_TotalPa,     VS_TotalPa     => true
  | VS_ImpForce,    VS_ImpForce    => true
  | VS_ImpRequest,  VS_ImpRequest  => true
  | VS_ImpPlead,    VS_ImpPlead    => true
  | VS_ImpUrge,     VS_ImpUrge     => true
  | VS_Volitive,    VS_Volitive    => true
  | VS_ComparVe,    VS_ComparVe    => true
  | VS_FutTa,       VS_FutTa       => true
  | VS_FutNe,       VS_FutNe       => true
  | VS_FutNegMoa,   VS_FutNegMoa   => true
  | VS_ImmFutPota,  VS_ImmFutPota  => true
  | VS_ObligVaera,  VS_ObligVaera  => true
  | VS_PastVaekue,  VS_PastVaekue  => true
  | VS_NegI,        VS_NegI        => true
  | VS_NegRi,       VS_NegRi       => true
  | VS_NegTei,      VS_NegTei      => true
  | VS_Privative,   VS_Privative   => true
  | VS_Intensifier, VS_Intensifier => true
  | VS_NomVa,       VS_NomVa       => true
  | VS_NomHa,       VS_NomHa       => true
  | VS_AspectMa,    VS_AspectMa    => true
  | VS_IterJevy,    VS_IterJevy    => true
  | VS_HabitMi,     VS_HabitMi     => true
  | VS_HabitVa,     VS_HabitVa     => true
  | VS_FrustrRei,   VS_FrustrRei   => true
  | VS_InterrogPa,  VS_InterrogPa  => true
  | VS_Desiderative,VS_Desiderative=> true
  | _,              _              => false
  end.

Fixpoint has_verbal_suffix (ss : list verbal_suffix) (s : verbal_suffix) : bool :=
  match ss with
  | nil => false
  | h :: t => if verbal_suffix_eqb h s then true
              else has_verbal_suffix t s
  end.

Definition has_any_neg (ss : list verbal_suffix) : bool :=
  has_verbal_suffix ss VS_NegI
  || has_verbal_suffix ss VS_NegRi
  || has_verbal_suffix ss VS_NegTei
  || has_verbal_suffix ss VS_Privative.

Definition has_any_future (ss : list verbal_suffix) : bool :=
  has_verbal_suffix ss VS_FutTa
  || has_verbal_suffix ss VS_FutNe
  || has_verbal_suffix ss VS_FutNegMoa
  || has_verbal_suffix ss VS_ImmFutPota.

Fixpoint no_dup_suffixes (ss : list verbal_suffix) : bool :=
  match ss with
  | nil => true
  | h :: t => negb (has_verbal_suffix t h) && no_dup_suffixes t
  end.

Fixpoint count_imp_modalizers (ss : list verbal_suffix) : nat :=
  match ss with
  | nil => 0
  | h :: t => (if is_imp_modalizer h then 1 else 0) + count_imp_modalizers t
  end.

(* --- Named well-formedness predicates --- *)

(* §4.1.2: Chendal verbs must be intransitive *)
Definition cv_structure_ok (cv : conjugated_verb) : bool :=
  match cv_verb_form cv with
  | VF_Regular v =>
      match v_class v with
      | Chendal =>
          match v_transitivity v with
          | Intransitive => true
          | _            => false
          end
      | Areal | Aireal => true
      end
  | VF_Irregular _ => true   (* irregular verbs are all intransitive active *)
  end.

(* §4.9: polarity and negation suffix must agree *)
Definition cv_neg_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  match cv_polarity cv with
  | Negative => has_any_neg ss
  | Positive => negb (has_any_neg ss)
  end.

(* §4.1.1: 1st plural requires Some inclusivity; others require None *)
Definition cv_incl_ok (cv : conjugated_verb) : bool :=
  match cv_person cv, cv_number cv with
  | First, Plural =>
      match cv_incl cv with Some _ => true | None => false end
  | _, _ =>
      match cv_incl cv with None => true | Some _ => false end
  end.

(* §4.10.1: at most one future tense marker; -ta and -mo'ã mutually exclusive;
   -mo'ã requires Negative polarity *)
Definition cv_tense_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  let future_count :=
      (if has_verbal_suffix ss VS_FutTa      then 1 else 0)
    + (if has_verbal_suffix ss VS_FutNe      then 1 else 0)
    + (if has_verbal_suffix ss VS_FutNegMoa  then 1 else 0)
    + (if has_verbal_suffix ss VS_ImmFutPota then 1 else 0)
    + (if has_verbal_suffix ss VS_ObligVaera  then 1 else 0)
    + (if has_verbal_suffix ss VS_PastVaekue then 1 else 0) in
  Nat.leb future_count 1
  && (if has_verbal_suffix ss VS_FutNegMoa then
        match cv_polarity cv with Negative => true | Positive => false end
      else true).

(* §4.9: at most one negation suffix *)
Definition cv_neg_count_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  let neg_count :=
      (if has_verbal_suffix ss VS_NegI      then 1 else 0)
    + (if has_verbal_suffix ss VS_NegRi     then 1 else 0)
    + (if has_verbal_suffix ss VS_NegTei    then 1 else 0)
    + (if has_verbal_suffix ss VS_Privative then 1 else 0) in
  Nat.leb neg_count 1.

(* §4.10.3.1.2: imperative modalizers only with Imperative or Optative mood *)
Definition cv_modalizer_ok (cv : conjugated_verb) : bool :=
  if Nat.ltb 0 (count_imp_modalizers (cv_suffixes cv)) then
    match cv_mood cv with
    | Imperative | Optative => true
    | _ => false
    end
  else true.

(* §4.10.3.1.3: prohibitive constraints:
   - requires Negative polarity
   - uses -tei or -'ỹ, NOT -i or -ri
   §4.10.3.4.2: regular negation (-i/-ri) only for Indicative/Imperative *)
Definition cv_mood_neg_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  match cv_mood cv with
  | Prohibitive =>
      match cv_polarity cv with Negative => true | Positive => false end
      && negb (has_verbal_suffix ss VS_NegI)
      && negb (has_verbal_suffix ss VS_NegRi)
  | Indicative | Imperative => true
  | Optative =>
      negb (has_verbal_suffix ss VS_NegI)
      && negb (has_verbal_suffix ss VS_NegRi)
  end.

(* §4.1.2: Chendal verbs cannot use Imperative or Optative mood *)
Definition cv_class_mood_ok (cv : conjugated_verb) : bool :=
  match cv_verb_form cv with
  | VF_Regular v =>
      match v_class v with
      | Chendal =>
          match cv_mood cv with
          | Imperative | Optative => false
          | _                     => true
          end
      | _ => true
      end
  | VF_Irregular _ => true
  end.

(* Suffix surface-form conflicts:
   - interrogative -pa and totalitative -pa cannot co-occur
   - habitual -mi and pleading -mi cannot co-occur *)
Definition cv_homophone_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  negb (has_verbal_suffix ss VS_InterrogPa && has_verbal_suffix ss VS_TotalPa)
  && negb (has_verbal_suffix ss VS_HabitMi && has_verbal_suffix ss VS_ImpPlead).

(* ============================================================ *)
(*  16b. Master well-formedness predicate                       *)
(*                                                              *)
(*  Conjunction of all named predicates above.                  *)
(*  To prove a verb ill-formed, unfold just the relevant        *)
(*  predicate and rewrite; the others follow by reflexivity.    *)
(* ============================================================ *)

Definition wf_conjugated_verb (cv : conjugated_verb) : bool :=
  cv_structure_ok   cv   (* Chendal must be intransitive          *)
  && cv_neg_ok       cv   (* polarity <-> neg suffix agreement     *)
  && cv_incl_ok      cv   (* 1pl requires inclusivity              *)
  && cv_tense_ok     cv   (* at most one future; -mo'ã constraints *)
  && cv_neg_count_ok cv   (* at most one neg suffix                *)
  && cv_modalizer_ok cv   (* modalizers only in imp/opt            *)
  && cv_mood_neg_ok  cv   (* prohibitive/optative neg rules        *)
  && cv_class_mood_ok cv  (* Chendal no imp/opt                    *)
  && cv_homophone_ok cv   (* no same-surface suffix pairs          *)
  && no_dup_suffixes (cv_suffixes cv)
  && suffixes_ordered (cv_suffixes cv).

(* ============================================================ *)
(*  17. Rendering                                               *)
(* ============================================================ *)

Fixpoint render_suffixes (ss : list verbal_suffix) (o : orality) : string :=
  match ss with
  | nil => ""
  | s :: rest => render_verbal_suffix s o ++ render_suffixes rest o
  end.

Definition render_regular_verb (cv : conjugated_verb) (v : verb) : string :=
  let o   := v_orality v in
  let cls := v_class v in
  let p   := cv_person cv in
  let n   := cv_number cv in
  let inc := cv_incl cv in
  let md  := cv_mood cv in
  let pol := cv_polarity cv in
  let vc  := cv_voice cv in
  let ss  := cv_suffixes cv in
  let vrc := v_root_class v in

  let neg_pfx := match pol with
                 | Negative =>
                     match md with
                     | Prohibitive => ""
                     | _ => neg_prefix_for o ++ neg_eufonic cls p n inc
                     end
                 | Positive => ""
                 end in
  let agr_pfx := agr_prefix cls md p n inc o in
  let vce_pfx := voice_prefix vc o in
  let rel_pfx := match cls with
                 | Chendal => verb_relational_prefix vrc PfxInactive
                 | _ =>
                     match md with
                     | Imperative => verb_relational_prefix vrc PfxImperative
                     | _ => verb_relational_prefix vrc PfxActive
                     end
                 end in
  let prohib  := match md with Prohibitive => "ani " | _ => "" end in

  prohib ++ neg_pfx ++ agr_pfx ++ vce_pfx ++ rel_pfx ++ v_root v
         ++ render_suffixes ss o.

(* Unified render_verb: dispatch on verb_form.
   Sentences.v calls this function only. *)
Definition render_verb (cv : conjugated_verb) : string :=
  match cv_verb_form cv with
  | VF_Regular v    => render_regular_verb cv v
  | VF_Irregular iv => irreg_form iv (cv_person cv) (cv_number cv) (cv_incl cv)
                       ++ render_suffixes (cv_suffixes cv) Oral
  end.

(*  18. Theorems                                                *)
(*  With factored predicates, each theorem unfolds only the     *)
(*  relevant check. No more destructing through 17 conjuncts.   *)

(*  RULE A: Areal prefixes §4.1.1                              *)

Theorem rule_A1_areal_1sg : forall incl o,
    areal_ind_prefix First Singular incl o = "a".
Proof. reflexivity. Qed.

Theorem rule_A2_areal_2sg : forall incl o,
    areal_ind_prefix Second Singular incl o = "re".
Proof. reflexivity. Qed.

Theorem rule_A3_areal_3rd : forall n incl o,
    areal_ind_prefix Third n incl o = "o".
Proof. intros n incl o. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_A4_areal_1pl_incl_oral :
    areal_ind_prefix First Plural (Some Inclusive) Oral = "ja".
Proof. reflexivity. Qed.

Theorem rule_A4_areal_1pl_incl_nasal :
    areal_ind_prefix First Plural (Some Inclusive) Nasal = "ña".
Proof. reflexivity. Qed.

Theorem rule_A5_areal_1pl_excl : forall o,
    areal_ind_prefix First Plural (Some Exclusive) o = "ro".
Proof. reflexivity. Qed.

Theorem rule_A6_areal_2pl : forall incl o,
    areal_ind_prefix Second Plural incl o = "pe".
Proof. reflexivity. Qed.

(*  RULE B: Aireal prefixes §4.2                               *)

Theorem rule_B1_aireal_1sg : forall incl o,
    aireal_ind_prefix First Singular incl o = "ai".
Proof. reflexivity. Qed.

Theorem rule_B2_aireal_3rd : forall n incl o,
    aireal_ind_prefix Third n incl o = "oi".
Proof. intros n incl o. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_B3_aireal_2sg : forall incl o,
    aireal_ind_prefix Second Singular incl o = "rei".
Proof. reflexivity. Qed.

Theorem rule_B4_aireal_1pl_incl_oral :
    aireal_ind_prefix First Plural (Some Inclusive) Oral = "jai".
Proof. reflexivity. Qed.

Theorem rule_B4_aireal_1pl_incl_nasal :
    aireal_ind_prefix First Plural (Some Inclusive) Nasal = "ñai".
Proof. reflexivity. Qed.

Theorem rule_B5_aireal_1pl_excl : forall o,
    aireal_ind_prefix First Plural (Some Exclusive) o = "roi".
Proof. reflexivity. Qed.

Theorem rule_B6_aireal_2pl : forall incl o,
    aireal_ind_prefix Second Plural incl o = "pei".
Proof. reflexivity. Qed.

(*  RULE C: Chendal prefixes §4.1.2                            *)

Theorem rule_C1_chendal_1sg : forall incl o,
    chendal_ind_prefix First Singular incl o = "che".
Proof. reflexivity. Qed.

Theorem rule_C2_chendal_2sg_oral :
    chendal_ind_prefix Second Singular None Oral = "nde".
Proof. reflexivity. Qed.

Theorem rule_C2_chendal_2sg_nasal :
    chendal_ind_prefix Second Singular None Nasal = "ne".
Proof. reflexivity. Qed.

Theorem rule_C3_chendal_3rd_oral : forall n incl,
    chendal_ind_prefix Third n incl Oral = "i".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_C3_chendal_3rd_nasal : forall n incl,
    chendal_ind_prefix Third n incl Nasal = "iñ".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_C4_chendal_1pl_incl_oral :
    chendal_ind_prefix First Plural (Some Inclusive) Oral = "ñande".
Proof. reflexivity. Qed.

Theorem rule_C5_chendal_1pl_excl : forall o,
    chendal_ind_prefix First Plural (Some Exclusive) o = "ore".
Proof. reflexivity. Qed.

Theorem rule_C6_chendal_2pl_oral :
    chendal_ind_prefix Second Plural None Oral = "pende".
Proof. reflexivity. Qed.

(*  RULE D: Imperative prefix §4.10.3.1.1                      *)

Theorem rule_D1_imp_2sg_areal : forall incl o,
    imp_prefix Areal Second Singular incl o = "e".
Proof. reflexivity. Qed.

Theorem rule_D1_imp_2sg_aireal : forall incl o,
    imp_prefix Aireal Second Singular incl o = "e".
Proof. reflexivity. Qed.

Theorem rule_D2_imp_chendal_no_e :
    imp_prefix Chendal Second Singular None Oral = "nde".
Proof. reflexivity. Qed.

Theorem rule_D3_imp_2pl_areal : forall incl o,
    imp_prefix Areal Second Plural incl o = "pe".
Proof. reflexivity. Qed.

(*  RULE E: Optative prefix §4.10.3.4.2                        *)

Theorem rule_E1_opt_1sg_active : forall incl o,
    opt_prefix Areal First Singular incl o = "ta".
Proof. reflexivity. Qed.

Theorem rule_E2_opt_3rd_active : forall n incl o,
    opt_prefix Areal Third n incl o = "to".
Proof. intros n incl o. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_E3_opt_2pl_active : forall incl o,
    opt_prefix Areal Second Plural incl o = "tape".
Proof. reflexivity. Qed.

(*  RULE F: Voice prefixes §6                                   *)

Theorem rule_F1_active_no_prefix : forall o, voice_prefix Active o = "".
Proof. reflexivity. Qed.

Theorem rule_F2_passive_je_oral : voice_prefix Passive Oral = "je".
Proof. reflexivity. Qed.

Theorem rule_F2_passive_ne_nasal : voice_prefix Passive Nasal = "ñe".
Proof. reflexivity. Qed.

Theorem rule_F3_reciprocal_jo_oral : voice_prefix Reciprocal Oral = "jo".
Proof. reflexivity. Qed.

Theorem rule_F4_coactive_mbo_oral : voice_prefix Coactive Oral = "mbo".
Proof. reflexivity. Qed.

Theorem rule_F5_objective_invariant : forall o, voice_prefix Objective o = "ro".
Proof. intros o; destruct o; reflexivity. Qed.

Theorem rule_F6_subsuntive_invariant : forall o, voice_prefix Subsuntive o = "poro".
Proof. intros o; destruct o; reflexivity. Qed.

(*  RULE G: Negation circumfix §4.9                             *)

Theorem rule_G1_neg_prefix_oral : neg_prefix_for Oral = "nd".
Proof. reflexivity. Qed.

Theorem rule_G1_neg_prefix_nasal : neg_prefix_for Nasal = "n".
Proof. reflexivity. Qed.

Theorem rule_G2_neg_prefix_distinct :
    neg_prefix_for Oral <> neg_prefix_for Nasal.
Proof. discriminate. Qed.

Theorem rule_G3_neg_prefix_nonempty : forall o, neg_prefix_for o <> "".
Proof. intros o; destruct o; discriminate. Qed.

Theorem rule_G4_eufonic_2pl_is_a :
    neg_eufonic Areal Second Plural None = "a".
Proof. reflexivity. Qed.

Theorem rule_G5_eufonic_chendal_always_a : forall p n incl,
    neg_eufonic Chendal p n incl = "a".
Proof. reflexivity. Qed.

(* Negative polarity with no suffixes is always ill-formed.
   Proof by cv_neg_ok: Negative requires has_any_neg. *)
Theorem rule_G6_neg_requires_suffix : forall cv,
    cv_polarity cv = Negative ->
    cv_suffixes cv = nil ->
    wf_conjugated_verb cv = false.
Proof.
  intros cv Hpol Hsuf.
  unfold wf_conjugated_verb, cv_neg_ok.
  rewrite Hpol, Hsuf. simpl.
  (* cv_neg_ok = has_any_neg nil with Negative = false *)
  destruct (cv_structure_ok cv); reflexivity.
Qed.

(*  RULE H: Future negation §4.9                                *)

(* -ta and -mo'ã cannot co-occur — violates cv_tense_ok *)
Theorem rule_H1_ta_and_moa_exclusive : forall vf p n inc md vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc md Negative vc
                  (VS_FutTa :: VS_FutNegMoa :: VS_NegI :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_tense_ok. simpl. reflexivity.
Qed.

(* -mo'ã requires Negative polarity *)
Theorem rule_H2_moa_requires_negative : forall vf p n inc md vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc md Positive vc
                  (VS_FutNegMoa :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_tense_ok, cv_neg_ok. simpl. reflexivity.
Qed.

Theorem rule_H3_moa_renders : forall o,
    render_verbal_suffix VS_FutNegMoa o = "mo'ã".
Proof. reflexivity. Qed.

(*  RULE I: Person hierarchy §4.2                               *)

Theorem rule_I1_first_subj_third_obj_active :
    trans_prefix_selection First Singular Third Singular = TPM_Active.
Proof. reflexivity. Qed.

Theorem rule_I2_third_subj_first_obj_inactive :
    trans_prefix_selection Third Singular First Singular = TPM_Inactive.
Proof. reflexivity. Qed.

Theorem rule_I4_first_to_2sg_portmanteau :
    trans_prefix_selection First Singular Second Singular
    = TPM_Portmanteau Port_1to2sg.
Proof. reflexivity. Qed.

Theorem rule_I5_first_to_2pl_portmanteau :
    trans_prefix_selection First Singular Second Plural
    = TPM_Portmanteau Port_1to2pl.
Proof. reflexivity. Qed.

Theorem rule_I9_same_person_reflexive :
    trans_prefix_selection First Singular First Singular = TPM_Reflexive.
Proof. reflexivity. Qed.

(*  RULE J: Relational verb root §4.6                           *)

Theorem rule_J1_relational_active_h :
    verb_relational_prefix VRoot_Relational PfxActive = "h".
Proof. reflexivity. Qed.

Theorem rule_J2_relational_inactive_r :
    verb_relational_prefix VRoot_Relational PfxInactive = "r".
Proof. reflexivity. Qed.

Theorem rule_J5_plain_always_empty : forall pt,
    verb_relational_prefix VRoot_Plain pt = "".
Proof. intros pt; destruct pt; reflexivity. Qed.

(*  RULE K: Irregular verbs §4.5                                *)

Theorem rule_K1_ju_3sg : forall incl,
    irreg_form Irreg_Ju Third Singular incl = "ou".
Proof. intros incl. destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K2_ho_3sg : forall incl,
    irreg_form Irreg_Ho Third Singular incl = "oho".
Proof. intros incl. destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K3_ho_1sg : forall incl,
    irreg_form Irreg_Ho First Singular incl = "aha".
Proof. intros incl. destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K4_e_2sg : forall incl,
    irreg_form Irreg_E Second Singular incl = "ere".
Proof. intros incl. destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K5_e_3sg : forall incl,
    irreg_form Irreg_E Third Singular incl = "he'i".
Proof. intros incl. destruct incl as [[]|]; reflexivity. Qed.

(*  RULE L: Inclusivity §4.1.1 — proof via cv_incl_ok           *)

Theorem rule_L1_1pl_requires_inclusivity : forall vf md pol vc ss,
    wf_conjugated_verb
      (mkConjVerb vf First Plural None md pol vc ss) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_incl_ok. simpl.
  destruct (cv_structure_ok _); reflexivity.
Qed.

Theorem rule_L2_non_1pl_forbids_inclusivity : forall vf p n md pol vc ss,
    (p, n) <> (First, Plural) ->
    wf_conjugated_verb
      (mkConjVerb vf p n (Some Inclusive) md pol vc ss) = false.
Proof.
  intros vf p n md pol vc ss Hne.
  unfold wf_conjugated_verb, cv_incl_ok.
  destruct p; destruct n; simpl; try reflexivity.
  exfalso; apply Hne; reflexivity.
Qed.

(*  RULE M: Suffix mutual exclusion — proof via cv_homophone_ok *)

Theorem rule_M1_no_double_future : forall vf p n inc vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Indicative Positive vc
                  (VS_FutTa :: VS_FutNe :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_tense_ok. simpl. reflexivity.
Qed.

Theorem rule_M2_habit_mi_plead_mi_exclusive : forall vf p n inc vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Imperative Positive vc
                  (VS_ImpPlead :: VS_HabitMi :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_homophone_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _); reflexivity.
Qed.

Theorem rule_M3_interrog_total_exclusive : forall vf p n inc vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Indicative Positive vc
                  (VS_TotalPa :: VS_InterrogPa :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_homophone_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _); reflexivity.
Qed.

(*  RULE N: Prohibitive §4.10.3.1.3 — proof via cv_mood_neg_ok *)

Theorem rule_N1_prohibitive_requires_negative : forall vf p n inc vc ss,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Prohibitive Positive vc ss) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_mood_neg_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _); reflexivity.
Qed.

Theorem rule_N2_prohibitive_no_regular_neg : forall vf p n inc vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Prohibitive Negative vc
                  (VS_NegI :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_mood_neg_ok. simpl.
  destruct (cv_structure_ok _); reflexivity.
Qed.

(*  RULE O: Imperative modalizers §4.10.3.1.2                   *)
(*  Proof via cv_modalizer_ok — no need to touch other checks   *)

Theorem rule_O1_modalizer_only_imp_opt : forall vf p n inc pol vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Indicative pol vc
                  (VS_ImpForce :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_modalizer_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _); reflexivity.
Qed.

(*  RULE P: Affix ordering §14                                  *)

Theorem rule_P1_total_before_modalizer :
    suffixes_ordered (VS_TotalPa :: VS_ImpForce :: VS_ImpRequest :: nil) = true.
Proof. reflexivity. Qed.

Theorem rule_P4_future_before_neg :
    suffixes_ordered (VS_FutNegMoa :: VS_NegI :: nil) = true.
Proof. reflexivity. Qed.

Theorem rule_P8_interrog_rightmost :
    suffixes_ordered (VS_AspectMa :: VS_InterrogPa :: nil) = true.
Proof. reflexivity. Qed.

Theorem rule_P9_wrong_order_rejected :
    suffixes_ordered (VS_NegI :: VS_TotalPa :: nil) = false.
Proof. reflexivity. Qed.

Theorem rule_P10_long_valid_chain :
    suffixes_ordered
      (VS_TotalPa :: VS_ImpForce :: VS_ImpRequest ::
       VS_Volitive :: VS_FutTa :: VS_NegI ::
       VS_Intensifier :: VS_NomVa :: VS_AspectMa ::
       VS_InterrogPa :: nil) = true.
Proof. reflexivity. Qed.

(*  RULE Q: Chendal structure constraints                       *)
(*  Proof via cv_structure_ok       *)

Theorem rule_Q1_chendal_no_transitive : forall o r,
    cv_structure_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Transitive VRoot_Plain))
                  First Singular None Indicative Positive Active nil) = false.
Proof. reflexivity. Qed.

Theorem rule_Q2_chendal_intrans_ok : forall o r,
    cv_structure_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain))
                  First Singular None Indicative Positive Active nil) = true.
Proof. reflexivity. Qed.

Theorem rule_Q3_areal_any_transitivity : forall o r t,
    cv_structure_ok
      (mkConjVerb (VF_Regular (mkVerb Areal o r t VRoot_Plain))
                  First Singular None Indicative Positive Active nil) = true.
Proof. reflexivity. Qed.

(*  RULE R: Chendal mood constraints                            *)

Theorem rule_R1_chendal_no_imperative : forall o r p n inc pol vc ss,
    cv_class_mood_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain))
                  p n inc Imperative pol vc ss) = false.
Proof. reflexivity. Qed.

Theorem rule_R2_chendal_no_optative : forall o r p n inc pol vc ss,
    cv_class_mood_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain))
                  p n inc Optative pol vc ss) = false.
Proof. reflexivity. Qed.

Theorem rule_R3_chendal_indicative_ok : forall o r p n inc pol vc ss,
    cv_class_mood_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain))
                  p n inc Indicative pol vc ss) = true.
Proof. reflexivity. Qed.

(* Full wf fails for Chendal+Imperative.
   Only cv_class_mood_ok needs to be false. *)
Theorem rule_R4_chendal_imperative_fails_wf : forall o r p n inc pol vc ss,
    wf_conjugated_verb
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain))
                  p n inc Imperative pol vc ss) = false.
Proof.
  intros.
  unfold wf_conjugated_verb.
  (* cv_class_mood_ok is false; the whole conjunction is false *)
  rewrite Bool.andb_false_iff.
  right. unfold cv_class_mood_ok. simpl. reflexivity.
Qed.

(*  RULE S: Future marker exclusivity §4.10.1                   *)
(*  Proof via cv_tense_ok                                       *)

Theorem rule_S1_no_ta_and_pota : forall vf p n inc md vc,
    wf_conjugated_verb
      (mkConjVerb vf p n inc md Positive vc
                  (VS_FutTa :: VS_ImmFutPota :: nil)) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_tense_ok. simpl. reflexivity.
Qed.

Theorem rule_S2_single_future_ok : forall o r,
    wf_conjugated_verb
      (mkConjVerb (VF_Regular (mkVerb Areal o r Intransitive VRoot_Plain))
                  First Singular None Indicative Positive Active
                  (VS_FutTa :: nil)) = true.
Proof. intros. unfold wf_conjugated_verb. simpl. reflexivity. Qed.

(*  RULE T: General well-formedness                             *)

Theorem rule_T1_no_duplicate_suffixes : forall s,
    no_dup_suffixes (s :: s :: nil) = false.
Proof. intros s. destruct s; reflexivity. Qed.

Theorem rule_T2_bare_positive_verb_wf : forall o r,
    wf_conjugated_verb
      (mkConjVerb (VF_Regular (mkVerb Areal o r Intransitive VRoot_Plain))
                  First Singular None Indicative Positive Active nil) = true.
Proof. intros. unfold wf_conjugated_verb. simpl. reflexivity. Qed.

Theorem rule_T3_no_suffixes_empty_render : forall o,
    render_suffixes nil o = "".
Proof. reflexivity. Qed.

(*  19. Decidable equality                                      *)

Scheme Equality for verb_class.
Scheme Equality for transitivity.
Scheme Equality for verb_root_class.
Scheme Equality for prefix_type.
Scheme Equality for voice.
Scheme Equality for mood.
Scheme Equality for polarity.
Scheme Equality for verbal_suffix.
Scheme Equality for portmanteau_config.
Scheme Equality for trans_prefix_mode.
Scheme Equality for obj_pron_post.
Scheme Equality for obj_indirect.
Scheme Equality for irregular_verb.