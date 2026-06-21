From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import Syntax.


(* ============================================================ *)
(*  Verb.v                                                      *)
(*  Guaraní verb morphology: types, conjugation, voice,         *)
(*  negation, tense/aspect/mood, evidentiality, object pronouns,*)
(*  transitivity, person hierarchy, relational verbs,           *)
(*  imperative modalizers, affix ordering, well-formedness,     *)
(*  and rendering.                                              *)
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
(*  4. Chendal 3rd-person allomorphs                           *)
(*  §4.1.2: Chendal 3rd person has two oral variants:          *)
(*    hi- (most common, e.g. "hi'ã" = s/he is heavy)           *)
(*    ij- (before vowel-initial roots, e.g. "ijexa" = s/he     *)
(*         sees in some varieties)                              *)
(*  Nasal allomorph: iñ- for both (same as before)             *)
(*  The verb record carries which variant to use.               *)
(* ============================================================ *)

Inductive chendal_3sg_form : Type :=
  | C3sg_I    (* plain i-/iñ-: previous default, kept for compat *)
  | C3sg_Hi   (* hi-/hiñ-: the common allomorph for most roots   *)
  | C3sg_Ij.  (* ij-/iñ-: allomorph before vowel-initial roots   *)

(* ============================================================ *)
(*  5. Voice                                                    *)
(*  §6: Added Objective_Guero for the guero- variant (§17.2)    *)
(*  causative voice from the paradigm list.                    *)
(*  Objective   = ro-  (first person singular agent in          *)
(*                       sociative causative)                   *)
(*  Obj_Guero   = guero- (variant of sociative causative with   *)
(*                        3rd person possessor relational root) *)
(* ============================================================ *)

Inductive voice : Type :=
  | Active
  | Passive
  | Reciprocal
  | Coactive
  | Objective
  | Obj_Guero    (* §17.2: guero- variant of Objective/sociative causative *)
  | Subsuntive.

Definition voice_prefix (vc : voice) (o : orality) : string :=
  match vc with
  | Active      => ""
  | Passive     => passive_prefix o
  | Reciprocal  => reciprocal_prefix o
  | Coactive    => coactive_prefix o
  | Objective   => "ro"
  | Obj_Guero   => "guero"
  | Subsuntive  => "poro"
  end.

(* ============================================================ *)
(*  6. Mood                                                     *)
(* ============================================================ *)

Inductive mood : Type :=
  | Indicative
  | Imperative
  | Optative
  | Prohibitive.

(* ============================================================ *)
(*  7. Polarity                                                 *)
(* ============================================================ *)

Inductive polarity : Type :=
  | Positive
  | Negative.

(* ============================================================ *)
(*  8. Evidential markers                                       *)
(*  §7: Evidentiality is grammatically important in Guaraní.    *)
(*  Most evidential markers are clitics with free distribution  *)
(*  in the clause; they are modeled as a single optional field  *)
(*  on conjugated_verb rather than as verbal suffixes.          *)
(*  Exception: -je is an unstressed verb suffix (§7.2, §17.3); *)
(*  it is modeled as VS_HearsayJe in the verbal suffix system.  *)
(*                                                              *)
(*  The four niko variants (=niko/=ko/=ngo/=ningo) are in       *)
(*  free variation per §7.1; we model them as one constructor   *)
(*  with a sub-type for rendering.                              *)
(* ============================================================ *)

(* Surface variants of the veridical emphatic clitic §7.1 *)
Inductive niko_variant : Type :=
  | NK_Niko    (* =niko (also pronounced nio) *)
  | NK_Ko      (* =ko *)
  | NK_Ngo     (* =ngo *)
  | NK_Ningo.  (* =ningo *)

Inductive evidential_marker : Type :=
  | Ev_Voi          (* §7.1: emphatic "voi" *)
  | Ev_Niko         (* §7.1: veridical emphatic =niko/=ko/=ngo/=ningo *)
                    (*        takes a niko_variant for rendering       *)
  | Ev_Ndaje        (* §7.2: hearsay "ndaje" *)
  | Ev_Jeko         (* §7.2: hearsay "jeko" *)
  | Ev_NandEko      (* §7.2: hearsay "ñandeko" *)
  | Ev_Kuri         (* §7.3: direct evidence / recent past "kuri" *)
  | Ev_Rae          (* §7.4: recent inference / mirative "ra'e" *)
  | Ev_Rakae        (* §7.4: distant inference "raka'e" *)
  | Ev_MboRae       (* §7.4: uncertain inference "mbora'e" (mbo + ra'e) *)
  | Ev_Nipo         (* §7.4: uncertainty / counterfact "nipo" *)
  | Ev_Hina.        (* §4.10.2/§7.1: progressive; emphatic function *)

(* Packed form: evidential + (for niko) its surface variant *)
Record evidential : Type := mkEvidential {
  ev_marker  : evidential_marker;
  ev_niko_v  : option niko_variant  (* Some v when ev_marker = Ev_Niko *)
}.

Definition render_evidential (e : evidential) : string :=
  match ev_marker e with
  | Ev_Voi     => "voi"
  | Ev_Niko    =>
      match ev_niko_v e with
      | Some NK_Ko    => "ko"
      | Some NK_Ngo   => "ngo"
      | Some NK_Ningo => "ningo"
      | _             => "niko"
      end
  | Ev_Ndaje   => "ndaje"
  | Ev_Jeko    => "jeko"
  | Ev_NandEko => "ñandeko"
  | Ev_Kuri    => "kuri"
  | Ev_Rae     => "ra'e"
  | Ev_Rakae   => "raka'e"
  | Ev_MboRae  => "mbora'e"
  | Ev_Nipo    => "nipo"
  | Ev_Hina    => "hína"
  end.

(* §7.1: voi and niko are emphatic/veridical — compatible with any mood.
   §7.3: kuri marks direct evidence; typically used with Indicative.
   §7.4: ra'e and raka'e are inferential; compatible with declarative/interrog.
   We enforce: kuri requires Indicative mood. *)
Definition ev_mood_ok (e : option evidential) (md : mood) : bool :=
  match e with
  | None => true
  | Some ev =>
      match ev_marker ev with
      | Ev_Kuri =>
          match md with Indicative => true | _ => false end
      | _ => true
      end
  end.

(* ============================================================ *)
(*  9. Verbal suffixes                                          *)
(*  Added VS_HearsayJe (-je, unstressed suffix §7.2, §17.3)    *)
(*  Added VS_Simultaneous (-vo, simultaneous aspect §12.2.3.1) *)
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
  | VS_Desiderative
  | VS_Simultaneous   (* -vo: simultaneous subordinator §12.2.3.1, §17.3 *)
  | VS_HearsayJe.     (* -je: hearsay evidential suffix §7.2, §17.3 *)

(* ============================================================ *)
(*  9a. Suffix classification predicates                        *)
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
(*  9b. Suffix rendering                                        *)
(* ============================================================ *)

Definition render_verbal_suffix (s : verbal_suffix) (o : orality) : string :=
  match s with
  | VS_CausUka      => "uka"
  | VS_AbilKuaa     => "kuaa"
  | VS_TotalPa      => totalitative_suffix o
  | VS_ImpForce     => "ke"
  | VS_ImpRequest   => "na"
  | VS_ImpPlead     => "mi"
  | VS_ImpUrge      => "py"
  | VS_Volitive     => "se"
  | VS_ComparVe     => "ve"
  | VS_FutTa        => "ta"
  | VS_FutNe        => "ne"
  | VS_FutNegMoa    => "mo'ã"
  | VS_ImmFutPota   => match o with Oral => "pota" | Nasal => "mbota" end
  | VS_ObligVaera   => "va'erã"
  | VS_PastVaekue   => "va'ekue"
  | VS_NegI         => "i"
  | VS_NegRi        => "ri"
  | VS_NegTei       => "tei"
  | VS_Privative    => "'ỹ"
  | VS_Intensifier  => match o with Oral => "ite" | Nasal => "ete" end
  | VS_NomVa        => "va"
  | VS_NomHa        => "ha"
  | VS_AspectMa     => "ma"
  | VS_IterJevy     => "jevy"
  | VS_HabitMi      => "mi"
  | VS_HabitVa      => "va"
  | VS_FrustrRei    => "rei"
  | VS_InterrogPa   => "pa"
  | VS_Desiderative => "nga'u"
  | VS_Simultaneous => "vo"
  | VS_HearsayJe    => "je"
  end.

(* ============================================================ *)
(*  10. Affix ordering §14                                      *)
(*  VS_Simultaneous: slot 11 (aspect/mood group)                *)
(*  VS_HearsayJe: slot 13 (after all other suffixes, §17.3     *)
(*    lists it as a suffix; it attaches rightmost)              *)
(* ============================================================ *)

Definition suffix_slot (s : verbal_suffix) : nat :=
  match s with
  | VS_CausUka      =>  1
  | VS_AbilKuaa     =>  2
  | VS_TotalPa      =>  3
  | VS_ImpForce
  | VS_ImpRequest
  | VS_ImpPlead
  | VS_ImpUrge      =>  4
  | VS_Volitive     =>  5
  | VS_ComparVe     =>  6
  | VS_FutTa
  | VS_FutNe
  | VS_FutNegMoa
  | VS_ImmFutPota
  | VS_ObligVaera
  | VS_PastVaekue   =>  7
  | VS_NegI
  | VS_NegRi
  | VS_NegTei
  | VS_Privative    =>  8
  | VS_Intensifier  =>  9
  | VS_NomVa
  | VS_NomHa        => 10
  | VS_AspectMa
  | VS_IterJevy
  | VS_HabitMi
  | VS_HabitVa
  | VS_FrustrRei
  | VS_Desiderative
  | VS_Simultaneous => 11
  | VS_InterrogPa   => 12
  | VS_HearsayJe    => 13
  end.

Fixpoint suffixes_ordered (ss : list verbal_suffix) : bool :=
  match ss with
  | nil => true
  | _ :: nil => true
  | s1 :: ((s2 :: _) as rest) =>
      Nat.leb (suffix_slot s1) (suffix_slot s2) && suffixes_ordered rest
  end.

(* ============================================================ *)
(*  11. Person hierarchy for transitive verbs §4.2              *)
(* ============================================================ *)

Definition person_rank (p : person) : nat :=
  match p with First => 1 | Second => 2 | Third => 3 end.

Definition subj_outranks_obj (subj_p obj_p : person) : bool :=
  Nat.leb (person_rank subj_p) (person_rank obj_p).

Inductive portmanteau_config : Type :=
  | Port_1to2sg
  | Port_1to2pl.

Definition render_portmanteau (pc : portmanteau_config) : string :=
  match pc with Port_1to2sg => "ro" | Port_1to2pl => "po" end.

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
(*  12. Object pronouns                                         *)
(* ============================================================ *)

Inductive obj_pron_post : Type :=
  | ObjPost_Chupe | ObjPost_Ichupe
  | ObjPost_ChupeKuera | ObjPost_IchupeKuera.

Definition render_obj_post (p : obj_pron_post) : string :=
  match p with
  | ObjPost_Chupe       => "chupe"
  | ObjPost_Ichupe      => "ichupe"
  | ObjPost_ChupeKuera  => "chupe kuéra"
  | ObjPost_IchupeKuera => "ichupe kuéra"
  end.

(* obj_indirect kept for backward compat in rendering; Sentences.v
   now uses guarani_np for the IO slot, but we keep this for
   stand-alone rendering utilities. *)
Inductive obj_indirect : Type :=
  | ObjInd_Cheve | ObjInd_Ndeve | ObjInd_Chupe
  | ObjInd_Nandeve | ObjInd_Oreve | ObjInd_Peeme | ObjInd_ChupeKuera.

Definition render_obj_indirect (p : obj_indirect) : string :=
  match p with
  | ObjInd_Cheve      => "chéve"
  | ObjInd_Ndeve      => "ndéve"
  | ObjInd_Chupe      => "chupe"
  | ObjInd_Nandeve    => "ñandéve"
  | ObjInd_Oreve      => "oréve"
  | ObjInd_Peeme      => "peẽme"
  | ObjInd_ChupeKuera => "chupe kuéra"
  end.

(* ============================================================ *)
(*  13. Verb record and verb_form dispatch                      *)
(* ============================================================ *)

Record verb : Type := mkVerb {
  v_class         : verb_class;
  v_orality       : orality;
  v_root          : string;
  v_transitivity  : transitivity;
  v_root_class    : verb_root_class;
  v_chendal_3sg   : chendal_3sg_form  (* only relevant for Chendal; use C3sg_I for others *)
}.

(* §4.5: Irregular verbs *)
Inductive irregular_verb : Type :=
  | Irreg_Ju | Irreg_Ho | Irreg_E.

Inductive verb_form : Type :=
  | VF_Regular   : verb -> verb_form
  | VF_Irregular : irregular_verb -> verb_form.

(* ============================================================ *)
(*  14. Agreement prefix selection                              *)
(* ============================================================ *)

Definition areal_ind_prefix (p : person) (n : number)
                            (incl : option inclusivity)
                            (o : orality) : string :=
  match p, n, incl with
  | First,  Singular, _ => "a"
  | Second, Singular, _ => "re"
  | Third,  _,        _ => "o"
  | First,  Plural, Some Inclusive =>
      match o with Oral => "ja" | Nasal => "ña" end
  | First,  Plural, Some Exclusive => "ro"
  | First,  Plural, None           => "ro"
  | Second, Plural, _              => "pe"
  end.

Definition aireal_ind_prefix (p : person) (n : number)
                             (incl : option inclusivity)
                             (o : orality) : string :=
  match p, n, incl with
  | First,  Singular, _ => "ai"
  | Second, Singular, _ => "rei"
  | Third,  _,        _ => "oi"
  | First,  Plural, Some Inclusive =>
      match o with Oral => "jai" | Nasal => "ñai" end
  | First,  Plural, Some Exclusive => "roi"
  | First,  Plural, None           => "roi"
  | Second, Plural, _              => "pei"
  end.

(* §4.1.2: Chendal 3rd person allomorphs.
   hi-/hiñ- is the most common form.
   ij- (oral) / iñ- (nasal) appears before vowel-initial roots.
   i-/iñ- is kept as C3sg_I for compatibility.
   Non-3rd-person forms are unaffected. *)
Definition chendal_ind_prefix (p : person) (n : number)
                              (incl : option inclusivity)
                              (o : orality)
                              (f3 : chendal_3sg_form) : string :=
  match p, n, incl with
  | First,  Singular, _ => "che"
  | Second, Singular, _ =>
      match o with Oral => "nde" | Nasal => "ne" end
  | Third,  _,        _ =>
      match f3, o with
      | C3sg_I,  Oral  => "i"
      | C3sg_I,  Nasal => "iñ"
      | C3sg_Hi, Oral  => "hi"
      | C3sg_Hi, Nasal => "hiñ"
      | C3sg_Ij, Oral  => "ij"
      | C3sg_Ij, Nasal => "iñ"
      end
  | First,  Plural, Some Inclusive =>
      match o with Oral => "ñande" | Nasal => "ñane" end
  | First,  Plural, Some Exclusive => "ore"
  | First,  Plural, None           => "ore"
  | Second, Plural, _              =>
      match o with Oral => "pende" | Nasal => "pene" end
  end.

Definition imp_prefix (cls : verb_class) (p : person) (n : number)
                      (incl : option inclusivity) (o : orality)
                      (f3 : chendal_3sg_form) : string :=
  match cls, p, n with
  | Areal,  Second, Singular => "e"
  | Aireal, Second, Singular => "e"
  | _, _, _ =>
      match cls with
      | Areal   => areal_ind_prefix p n incl o
      | Aireal  => aireal_ind_prefix p n incl o
      | Chendal => chendal_ind_prefix p n incl o f3
      end
  end.

Definition opt_prefix (cls : verb_class) (p : person) (n : number)
                      (incl : option inclusivity) (o : orality)
                      (f3 : chendal_3sg_form) : string :=
  match cls with
  | Chendal =>
      "ta" ++ chendal_ind_prefix p n incl o f3
  | _ =>
      match p, n, incl with
      | First,  Singular, _ => "ta"
      | Second, Singular, _ => "te"
      | Third,  _,        _ => "to"
      | First,  Plural, Some Inclusive =>
          match o with Oral => "taja" | Nasal => "taña" end
      | First,  Plural, Some Exclusive => "toro"
      | First,  Plural, None           => "toro"
      | Second, Plural, _              => "tape"
      end
  end.

Definition agr_prefix (cls : verb_class) (md : mood)
                      (p : person) (n : number)
                      (incl : option inclusivity) (o : orality)
                      (f3 : chendal_3sg_form) : string :=
  match md with
  | Optative   => opt_prefix cls p n incl o f3
  | Imperative => imp_prefix cls p n incl o f3
  | Indicative | Prohibitive =>
      match cls with
      | Areal   => areal_ind_prefix p n incl o
      | Aireal  => aireal_ind_prefix p n incl o
      | Chendal => chendal_ind_prefix p n incl o f3
      end
  end.

(* ============================================================ *)
(*  15. Negation prefix §4.9                                    *)
(* ============================================================ *)

Definition neg_prefix_for (o : orality) : string := neg_prefix o.

Definition neg_eufonic (cls : verb_class) (p : person) (n : number)
                       (incl : option inclusivity) : string :=
  match cls with
  | Chendal => "a"
  | Areal | Aireal =>
      match p, n, incl with
      | First,  Singular, _ => "a"
      | Second, Singular, _ => "e"
      | Third,  _,        _ => "o"
      | First,  Plural, Some Inclusive => "a"
      | First,  Plural, Some Exclusive => "o"
      | First,  Plural, None           => "o"
      | Second, Plural, _              => "a"
      end
  end.

(* ============================================================ *)
(*  16. Irregular verb forms §4.5                               *)
(* ============================================================ *)

Definition irreg_form (iv : irregular_verb) (p : person) (n : number)
                      (incl : option inclusivity) : string :=
  match iv, p, n, incl with
  | Irreg_Ju, First,  Singular, _              => "aju"
  | Irreg_Ju, Second, Singular, _              => "reju"
  | Irreg_Ju, Third,  _,        _              => "ou"
  | Irreg_Ju, First,  Plural,   Some Inclusive => "jaju"
  | Irreg_Ju, First,  Plural,   _              => "roju"
  | Irreg_Ju, Second, Plural,   _              => "peju"
  | Irreg_Ho, First,  Singular, _              => "aha"
  | Irreg_Ho, Second, Singular, _              => "reho"
  | Irreg_Ho, Third,  _,        _              => "oho"
  | Irreg_Ho, First,  Plural,   Some Inclusive => "jaha"
  | Irreg_Ho, First,  Plural,   _              => "roho"
  | Irreg_Ho, Second, Plural,   _              => "peho"
  | Irreg_E,  First,  Singular, _              => "ha'e"
  | Irreg_E,  Second, Singular, _              => "ere"
  | Irreg_E,  Third,  _,        _              => "he'i"
  | Irreg_E,  First,  Plural,   Some Inclusive => "ja'e"
  | Irreg_E,  First,  Plural,   _              => "ro'e"
  | Irreg_E,  Second, Plural,   _              => "peje"
  end.

(* ============================================================ *)
(*  17. Conjugated verb structure                               *)
(*  cv_evidential: optional evidential clitic/marker §7         *)
(* ============================================================ *)

Record conjugated_verb : Type := mkConjVerb {
  cv_verb_form  : verb_form;
  cv_person     : person;
  cv_number     : number;
  cv_incl       : option inclusivity;
  cv_mood       : mood;
  cv_polarity   : polarity;
  cv_voice      : voice;
  cv_suffixes   : list verbal_suffix;
  cv_evidential : option evidential    (* §7: optional evidential marker *)
}.

Definition cv_orality (cv : conjugated_verb) : orality :=
  match cv_verb_form cv with
  | VF_Regular v   => v_orality v
  | VF_Irregular _ => Oral
  end.

(* ============================================================ *)
(*  18. Well-formedness: factored predicates                    *)
(* ============================================================ *)

Definition verbal_suffix_eqb (s1 s2 : verbal_suffix) : bool :=
  match s1, s2 with
  | VS_CausUka,      VS_CausUka      => true
  | VS_AbilKuaa,     VS_AbilKuaa     => true
  | VS_TotalPa,      VS_TotalPa      => true
  | VS_ImpForce,     VS_ImpForce     => true
  | VS_ImpRequest,   VS_ImpRequest   => true
  | VS_ImpPlead,     VS_ImpPlead     => true
  | VS_ImpUrge,      VS_ImpUrge      => true
  | VS_Volitive,     VS_Volitive     => true
  | VS_ComparVe,     VS_ComparVe     => true
  | VS_FutTa,        VS_FutTa        => true
  | VS_FutNe,        VS_FutNe        => true
  | VS_FutNegMoa,    VS_FutNegMoa    => true
  | VS_ImmFutPota,   VS_ImmFutPota   => true
  | VS_ObligVaera,   VS_ObligVaera   => true
  | VS_PastVaekue,   VS_PastVaekue   => true
  | VS_NegI,         VS_NegI         => true
  | VS_NegRi,        VS_NegRi        => true
  | VS_NegTei,       VS_NegTei       => true
  | VS_Privative,    VS_Privative    => true
  | VS_Intensifier,  VS_Intensifier  => true
  | VS_NomVa,        VS_NomVa        => true
  | VS_NomHa,        VS_NomHa        => true
  | VS_AspectMa,     VS_AspectMa     => true
  | VS_IterJevy,     VS_IterJevy     => true
  | VS_HabitMi,      VS_HabitMi      => true
  | VS_HabitVa,      VS_HabitVa      => true
  | VS_FrustrRei,    VS_FrustrRei    => true
  | VS_InterrogPa,   VS_InterrogPa   => true
  | VS_Desiderative, VS_Desiderative => true
  | VS_Simultaneous, VS_Simultaneous => true
  | VS_HearsayJe,    VS_HearsayJe    => true
  | _,               _               => false
  end.

Fixpoint has_verbal_suffix (ss : list verbal_suffix) (s : verbal_suffix) : bool :=
  match ss with
  | nil => false
  | h :: t => if verbal_suffix_eqb h s then true else has_verbal_suffix t s
  end.

Definition has_any_neg (ss : list verbal_suffix) : bool :=
  has_verbal_suffix ss VS_NegI || has_verbal_suffix ss VS_NegRi
  || has_verbal_suffix ss VS_NegTei || has_verbal_suffix ss VS_Privative.

Definition has_any_future (ss : list verbal_suffix) : bool :=
  has_verbal_suffix ss VS_FutTa || has_verbal_suffix ss VS_FutNe
  || has_verbal_suffix ss VS_FutNegMoa || has_verbal_suffix ss VS_ImmFutPota.

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

Definition cv_structure_ok (cv : conjugated_verb) : bool :=
  match cv_verb_form cv with
  | VF_Regular v =>
      match v_class v with
      | Chendal => match v_transitivity v with Intransitive => true | _ => false end
      | _ => true
      end
  | VF_Irregular _ => true
  end.

Definition cv_neg_ok (cv : conjugated_verb) : bool :=
  match cv_polarity cv with
  | Negative => has_any_neg (cv_suffixes cv)
  | Positive => negb (has_any_neg (cv_suffixes cv))
  end.

Definition cv_incl_ok (cv : conjugated_verb) : bool :=
  match cv_person cv, cv_number cv with
  | First, Plural =>
      match cv_incl cv with Some _ => true | None => false end
  | _, _ =>
      match cv_incl cv with None => true | Some _ => false end
  end.

Definition cv_tense_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  let fc :=
      (if has_verbal_suffix ss VS_FutTa      then 1 else 0)
    + (if has_verbal_suffix ss VS_FutNe      then 1 else 0)
    + (if has_verbal_suffix ss VS_FutNegMoa  then 1 else 0)
    + (if has_verbal_suffix ss VS_ImmFutPota then 1 else 0)
    + (if has_verbal_suffix ss VS_ObligVaera then 1 else 0)
    + (if has_verbal_suffix ss VS_PastVaekue then 1 else 0) in
  Nat.leb fc 1
  && (if has_verbal_suffix ss VS_FutNegMoa then
        match cv_polarity cv with Negative => true | Positive => false end
      else true).

Definition cv_neg_count_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  let nc :=
      (if has_verbal_suffix ss VS_NegI      then 1 else 0)
    + (if has_verbal_suffix ss VS_NegRi     then 1 else 0)
    + (if has_verbal_suffix ss VS_NegTei    then 1 else 0)
    + (if has_verbal_suffix ss VS_Privative then 1 else 0) in
  Nat.leb nc 1.

Definition cv_modalizer_ok (cv : conjugated_verb) : bool :=
  if Nat.ltb 0 (count_imp_modalizers (cv_suffixes cv)) then
    match cv_mood cv with Imperative | Optative => true | _ => false end
  else true.

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

Definition cv_class_mood_ok (cv : conjugated_verb) : bool :=
  match cv_verb_form cv with
  | VF_Regular v =>
      match v_class v with
      | Chendal => match cv_mood cv with Imperative | Optative => false | _ => true end
      | _ => true
      end
  | VF_Irregular _ => true
  end.

Definition cv_homophone_ok (cv : conjugated_verb) : bool :=
  let ss := cv_suffixes cv in
  negb (has_verbal_suffix ss VS_InterrogPa && has_verbal_suffix ss VS_TotalPa)
  && negb (has_verbal_suffix ss VS_HabitMi && has_verbal_suffix ss VS_ImpPlead).

(* §7: kuri requires Indicative mood *)
Definition cv_evidential_ok (cv : conjugated_verb) : bool :=
  ev_mood_ok (cv_evidential cv) (cv_mood cv).

Definition wf_conjugated_verb (cv : conjugated_verb) : bool :=
  cv_structure_ok   cv
  && cv_neg_ok       cv
  && cv_incl_ok      cv
  && cv_tense_ok     cv
  && cv_neg_count_ok cv
  && cv_modalizer_ok cv
  && cv_mood_neg_ok  cv
  && cv_class_mood_ok cv
  && cv_homophone_ok cv
  && no_dup_suffixes (cv_suffixes cv)
  && suffixes_ordered (cv_suffixes cv)
  && cv_evidential_ok cv.
  

  Ltac wf_is_false :=
  intros;
  unfold wf_conjugated_verb, cv_mood_neg_ok, cv_homophone_ok,
         cv_modalizer_ok, cv_tense_ok, cv_neg_count_ok,
         cv_neg_ok, cv_evidential_ok;
  repeat match goal with
         | [ |- context [cv_structure_ok ?x] ]  => destruct (cv_structure_ok x)
         | [ |- context [cv_neg_ok ?x] ]         => destruct (cv_neg_ok x)
         | [ |- context [cv_incl_ok ?x] ]        => destruct (cv_incl_ok x)
         | [ |- context [cv_class_mood_ok ?x] ]  => destruct (cv_class_mood_ok x)
         | [ |- context [cv_evidential_ok ?x] ]  => destruct (cv_evidential_ok x)
         | [ |- context [no_dup_suffixes ?x] ]   => destruct (no_dup_suffixes x)
         | [ |- context [suffixes_ordered ?x] ]  => destruct (suffixes_ordered x)
         | [ |- context [cv_homophone_ok ?x] ]   => destruct (cv_homophone_ok x)
         | [ |- context [cv_modalizer_ok ?x] ]   => destruct (cv_modalizer_ok x)
         | [ |- context [cv_tense_ok ?x] ]       => destruct (cv_tense_ok x)
         | [ |- context [cv_neg_count_ok ?x] ]   => destruct (cv_neg_count_ok x)
         end;
  reflexivity.
(* ============================================================ *)
(*  19. Rendering                                               *)
(* ============================================================ *)

Fixpoint render_suffixes (ss : list verbal_suffix) (o : orality) : string :=
  match ss with
  | nil => ""
  | s :: rest => render_verbal_suffix s o ++ render_suffixes rest o
  end.

Definition get_f3 (vf : verb_form) : chendal_3sg_form :=
  match vf with
  | VF_Regular v   => v_chendal_3sg v
  | VF_Irregular _ => C3sg_I
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
  let f3  := v_chendal_3sg v in
  let neg_pfx :=
      match pol with
      | Negative =>
          match md with
          | Prohibitive => ""
          | _ => neg_prefix_for o ++ neg_eufonic cls p n inc
          end
      | Positive => ""
      end in
  let agr_pfx := agr_prefix cls md p n inc o f3 in
  let vce_pfx := voice_prefix vc o in
  let rel_pfx :=
      match cls with
      | Chendal => verb_relational_prefix vrc PfxInactive
      | _ =>
          match md with
          | Imperative => verb_relational_prefix vrc PfxImperative
          | _          => verb_relational_prefix vrc PfxActive
          end
      end in
  let prohib := match md with Prohibitive => "ani " | _ => "" end in
  prohib ++ neg_pfx ++ agr_pfx ++ vce_pfx ++ rel_pfx ++ v_root v
         ++ render_suffixes ss o.

(* render_verb: dispatch on verb_form; append evidential clitic last.
   §7: evidential clitics have free distribution, but we model them
   as sentence-final for simplicity. -je is already a suffix in cv_suffixes. *)
Definition render_verb (cv : conjugated_verb) : string :=
  let base :=
    match cv_verb_form cv with
    | VF_Regular v    => render_regular_verb cv v
    | VF_Irregular iv =>
        irreg_form iv (cv_person cv) (cv_number cv) (cv_incl cv)
        ++ render_suffixes (cv_suffixes cv) Oral
    end in
  match cv_evidential cv with
  | None   => base
  | Some e => base ++ " " ++ render_evidential e
  end.

(* ============================================================ *)
(*  20. Theorems                                                *)
(* ============================================================ *)

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

Theorem rule_C1_chendal_1sg : forall incl o f3,
    chendal_ind_prefix First Singular incl o f3 = "che".
Proof. reflexivity. Qed.

Theorem rule_C2_chendal_2sg_oral : forall f3,
    chendal_ind_prefix Second Singular None Oral f3 = "nde".
Proof. reflexivity. Qed.

Theorem rule_C2_chendal_2sg_nasal : forall f3,
    chendal_ind_prefix Second Singular None Nasal f3 = "ne".
Proof. reflexivity. Qed.

(* §4.1.2: plain i- form *)
Theorem rule_C3_chendal_3rd_i_oral : forall n incl,
    chendal_ind_prefix Third n incl Oral C3sg_I = "i".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_C3_chendal_3rd_i_nasal : forall n incl,
    chendal_ind_prefix Third n incl Nasal C3sg_I = "iñ".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

(* §4.1.2: hi- allomorph *)
Theorem rule_C3b_chendal_3rd_hi_oral : forall n incl,
    chendal_ind_prefix Third n incl Oral C3sg_Hi = "hi".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_C3b_chendal_3rd_hi_nasal : forall n incl,
    chendal_ind_prefix Third n incl Nasal C3sg_Hi = "hiñ".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

(* §4.1.2: ij- allomorph (oral); nasal = iñ- *)
Theorem rule_C3c_chendal_3rd_ij_oral : forall n incl,
    chendal_ind_prefix Third n incl Oral C3sg_Ij = "ij".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_C3c_chendal_3rd_ij_nasal : forall n incl,
    chendal_ind_prefix Third n incl Nasal C3sg_Ij = "iñ".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_C4_chendal_1pl_incl_oral : forall f3,
    chendal_ind_prefix First Plural (Some Inclusive) Oral f3 = "ñande".
Proof. reflexivity. Qed.

Theorem rule_C5_chendal_1pl_excl : forall o f3,
    chendal_ind_prefix First Plural (Some Exclusive) o f3 = "ore".
Proof. reflexivity. Qed.

Theorem rule_C6_chendal_2pl_oral : forall f3,
    chendal_ind_prefix Second Plural None Oral f3 = "pende".
Proof. reflexivity. Qed.

Theorem rule_D1_imp_2sg_areal : forall incl o f3,
    imp_prefix Areal Second Singular incl o f3 = "e".
Proof. reflexivity. Qed.

Theorem rule_D1_imp_2sg_aireal : forall incl o f3,
    imp_prefix Aireal Second Singular incl o f3 = "e".
Proof. reflexivity. Qed.

Theorem rule_D2_imp_chendal_no_e : forall f3,
    imp_prefix Chendal Second Singular None Oral f3 = "nde".
Proof. reflexivity. Qed.

Theorem rule_D3_imp_2pl_areal : forall incl o f3,
    imp_prefix Areal Second Plural incl o f3 = "pe".
Proof. reflexivity. Qed.

Theorem rule_E1_opt_1sg_active : forall incl o f3,
    opt_prefix Areal First Singular incl o f3 = "ta".
Proof. reflexivity. Qed.

Theorem rule_E2_opt_3rd_active : forall n incl o f3,
    opt_prefix Areal Third n incl o f3 = "to".
Proof. intros n incl o f3. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_E3_opt_2pl_active : forall incl o f3,
    opt_prefix Areal Second Plural incl o f3 = "tape".
Proof. reflexivity. Qed.

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

(* §17.2: guero- is invariant across orality *)
Theorem rule_F5b_obj_guero_invariant : forall o,
    voice_prefix Obj_Guero o = "guero".
Proof. intros o; destruct o; reflexivity. Qed.

Theorem rule_F5b_obj_guero_ne_objective : forall o,
    voice_prefix Obj_Guero o <> voice_prefix Objective o.
Proof. intros o; destruct o; discriminate. Qed.

Theorem rule_F6_subsuntive_invariant : forall o, voice_prefix Subsuntive o = "poro".
Proof. intros o; destruct o; reflexivity. Qed.

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

Theorem rule_G6_neg_requires_suffix : forall cv,
    cv_polarity cv = Negative ->
    cv_suffixes cv = nil ->
    wf_conjugated_verb cv = false.
Proof.
  intros cv Hpol Hsuf.
  unfold wf_conjugated_verb, cv_neg_ok.
  rewrite Hpol, Hsuf. simpl.
  destruct (cv_structure_ok cv); reflexivity.
Qed.

Theorem rule_H1_ta_and_moa_exclusive : forall vf p n inc md vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc md Negative vc
                  (VS_FutTa :: VS_FutNegMoa :: VS_NegI :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb.
  destruct (cv_structure_ok _); destruct (cv_incl_ok _); reflexivity.
Qed.
Theorem rule_H2_moa_requires_negative : forall vf p n inc md vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc md Positive vc (VS_FutNegMoa :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb.
  destruct (cv_structure_ok _); destruct (cv_incl_ok _); reflexivity.
Qed.

Theorem rule_H3_moa_renders : forall o,
    render_verbal_suffix VS_FutNegMoa o = "mo'ã".
Proof. reflexivity. Qed.

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

Theorem rule_J1_relational_active_h :
    verb_relational_prefix VRoot_Relational PfxActive = "h".
Proof. reflexivity. Qed.

Theorem rule_J2_relational_inactive_r :
    verb_relational_prefix VRoot_Relational PfxInactive = "r".
Proof. reflexivity. Qed.

Theorem rule_J5_plain_always_empty : forall pt,
    verb_relational_prefix VRoot_Plain pt = "".
Proof. intros pt; destruct pt; reflexivity. Qed.

Theorem rule_K1_ju_3sg : forall n incl,
    irreg_form Irreg_Ju Third n incl = "ou".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K2_ho_3sg : forall n incl,
    irreg_form Irreg_Ho Third n incl = "oho".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K3_ho_1sg : forall incl,
    irreg_form Irreg_Ho First Singular incl = "aha".
Proof. intros incl. destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K4_e_2sg : forall incl,
    irreg_form Irreg_E Second Singular incl = "ere".
Proof. intros incl. destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_K5_e_3sg : forall n incl,
    irreg_form Irreg_E Third n incl = "he'i".
Proof. intros n incl. destruct n; destruct incl as [[]|]; reflexivity. Qed.

Theorem rule_L1_1pl_requires_inclusivity : forall vf md pol vc ss ev,
    wf_conjugated_verb
      (mkConjVerb vf First Plural None md pol vc ss ev) = false.
Proof.
  intros.
  unfold wf_conjugated_verb.
  simpl.
  rewrite andb_false_r.
  reflexivity.
Qed.
Theorem rule_L2_non_1pl_forbids_inclusivity : forall vf p n md pol vc ss ev,
    (p, n) <> (First, Plural) ->
    wf_conjugated_verb
      (mkConjVerb vf p n (Some Inclusive) md pol vc ss ev) = false.
Proof.
  intros vf p n md pol vc ss ev Hne.
  unfold wf_conjugated_verb, cv_incl_ok.
  destruct p; destruct n; simpl;
    try (destruct (cv_structure_ok _); destruct (cv_neg_ok _); reflexivity).
  exfalso; apply Hne; reflexivity.
Qed.
Theorem rule_M1_no_double_future : forall vf p n inc vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Indicative Positive vc
                  (VS_FutTa :: VS_FutNe :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb.
  destruct (cv_structure_ok _); destruct (cv_incl_ok _); reflexivity.
Qed.

Theorem rule_M2_habit_mi_plead_mi_exclusive : forall vf p n inc vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Imperative Positive vc
                  (VS_ImpPlead :: VS_HabitMi :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_homophone_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _);
  destruct (cv_incl_ok _); destruct (cv_class_mood_ok _); reflexivity.
Qed.

Theorem rule_M3_interrog_total_exclusive : forall vf p n inc vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Indicative Positive vc
                  (VS_TotalPa :: VS_InterrogPa :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_homophone_ok, cv_mood_neg_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _);
  destruct (cv_incl_ok _); destruct (cv_class_mood_ok _); reflexivity.
Qed.

Theorem rule_N1_prohibitive_requires_negative : forall vf p n inc vc ss ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Prohibitive Positive vc ss ev) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_mood_neg_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _);
  destruct (cv_incl_ok _); destruct (cv_tense_ok _);
  destruct (cv_neg_count_ok _); destruct (cv_modalizer_ok _);
  destruct (cv_class_mood_ok _); destruct (cv_homophone_ok _);
  destruct (no_dup_suffixes _); destruct (suffixes_ordered _);
  destruct (cv_evidential_ok _); reflexivity.
Qed.
Theorem rule_N2_prohibitive_no_regular_neg : forall vf p n inc vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Prohibitive Negative vc
                  (VS_NegI :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_mood_neg_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _);
  destruct (cv_incl_ok _); destruct (cv_tense_ok _);
  destruct (cv_neg_count_ok _); destruct (cv_modalizer_ok _);
  destruct (cv_class_mood_ok _); destruct (cv_homophone_ok _);
  destruct (cv_evidential_ok _); reflexivity.
Qed.

Theorem rule_O1_modalizer_only_imp_opt : forall vf p n inc pol vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Indicative pol vc
                  (VS_ImpForce :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_modalizer_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _);
  destruct (cv_incl_ok _); destruct (cv_tense_ok _);
  destruct (cv_neg_count_ok _); destruct (cv_mood_neg_ok _);
  destruct (cv_class_mood_ok _); destruct (cv_homophone_ok _);
  destruct (cv_evidential_ok _); reflexivity.
Qed.

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

(* VS_HearsayJe must follow everything else *)
Theorem rule_P11_hearsay_je_last :
    suffixes_ordered (VS_InterrogPa :: VS_HearsayJe :: nil) = true.
Proof. reflexivity. Qed.

Theorem rule_P12_je_before_interrog_rejected :
    suffixes_ordered (VS_HearsayJe :: VS_InterrogPa :: nil) = false.
Proof. reflexivity. Qed.

(* VS_Simultaneous (-vo) is in the aspect slot *)
Theorem rule_P13_simult_vo_renders : forall o,
    render_verbal_suffix VS_Simultaneous o = "vo".
Proof. reflexivity. Qed.

Theorem rule_P14_neg_before_simult :
    suffixes_ordered (VS_Simultaneous :: VS_NegI :: nil) = false.
Proof. reflexivity. Qed.
Theorem rule_Q1_chendal_no_transitive : forall o r f3,
    cv_structure_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Transitive VRoot_Plain f3))
                  First Singular None Indicative Positive Active nil None) = false.
Proof. reflexivity. Qed.

Theorem rule_Q2_chendal_intrans_ok : forall o r f3,
    cv_structure_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain f3))
                  First Singular None Indicative Positive Active nil None) = true.
Proof. reflexivity. Qed.

Theorem rule_Q3_areal_any_transitivity : forall o r t f3,
    cv_structure_ok
      (mkConjVerb (VF_Regular (mkVerb Areal o r t VRoot_Plain f3))
                  First Singular None Indicative Positive Active nil None) = true.
Proof. reflexivity. Qed.

Theorem rule_R1_chendal_no_imperative : forall o r p n inc pol vc ss f3 ev,
    cv_class_mood_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain f3))
                  p n inc Imperative pol vc ss ev) = false.
Proof. reflexivity. Qed.

Theorem rule_R2_chendal_no_optative : forall o r p n inc pol vc ss f3 ev,
    cv_class_mood_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain f3))
                  p n inc Optative pol vc ss ev) = false.
Proof. reflexivity. Qed.

Theorem rule_R3_chendal_indicative_ok : forall o r p n inc pol vc ss f3 ev,
    cv_class_mood_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain f3))
                  p n inc Indicative pol vc ss ev) = true.
Proof. reflexivity. Qed.
Theorem rule_R4_chendal_imperative_fails_wf : forall o r p n inc pol vc ss f3 ev,
    wf_conjugated_verb
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain f3))
                  p n inc Imperative pol vc ss ev) = false.
Proof.
  intros.
  assert (Hc : cv_class_mood_ok
      (mkConjVerb (VF_Regular (mkVerb Chendal o r Intransitive VRoot_Plain f3))
                  p n inc Imperative pol vc ss ev) = false) by reflexivity.
  unfold wf_conjugated_verb.
  rewrite Hc.
  repeat (rewrite Bool.andb_false_r || rewrite Bool.andb_false_l).
  reflexivity.
Qed.

Theorem rule_S1_no_ta_and_pota : forall vf p n inc md vc ev,
    wf_conjugated_verb
      (mkConjVerb vf p n inc md Positive vc
                  (VS_FutTa :: VS_ImmFutPota :: nil) ev) = false.
Proof.
  intros. unfold wf_conjugated_verb.
  destruct (cv_structure_ok _); destruct (cv_incl_ok _); reflexivity.
Qed.
Theorem rule_S2_single_future_ok : forall o r f3,
    wf_conjugated_verb
      (mkConjVerb (VF_Regular (mkVerb Areal o r Intransitive VRoot_Plain f3))
                  First Singular None Indicative Positive Active
                  (VS_FutTa :: nil) None) = true.
Proof. intros. unfold wf_conjugated_verb. simpl. reflexivity. Qed.

Theorem rule_T1_no_duplicate_suffixes : forall s,
    no_dup_suffixes (s :: s :: nil) = false.
Proof. intros s. destruct s; reflexivity. Qed.

Theorem rule_T2_bare_positive_verb_wf : forall o r f3,
    wf_conjugated_verb
      (mkConjVerb (VF_Regular (mkVerb Areal o r Intransitive VRoot_Plain f3))
                  First Singular None Indicative Positive Active nil None) = true.
Proof. intros. unfold wf_conjugated_verb. simpl. reflexivity. Qed.

Theorem rule_T3_no_suffixes_empty_render : forall o,
    render_suffixes nil o = "".
Proof. reflexivity. Qed.

(* §7: kuri requires Indicative mood *)
Theorem rule_EV1_kuri_requires_indicative : forall vf p n inc pol vc ss,
    wf_conjugated_verb
      (mkConjVerb vf p n inc Imperative pol vc ss
                  (Some (mkEvidential Ev_Kuri None))) = false.
Proof.
  intros. unfold wf_conjugated_verb, cv_evidential_ok, ev_mood_ok. simpl.
  destruct (cv_structure_ok _); destruct (cv_neg_ok _); destruct (cv_incl_ok _);
  destruct (cv_tense_ok _); destruct (cv_neg_count_ok _);
  destruct (cv_modalizer_ok _); destruct (cv_mood_neg_ok _);
  destruct (cv_class_mood_ok _); destruct (cv_homophone_ok _);
  destruct (no_dup_suffixes _); destruct (suffixes_ordered _);
  reflexivity.
Qed.

(* §7.1: voi is compatible with any mood *)
Theorem rule_EV2_voi_any_mood : forall vf p n inc md pol vc,
    cv_evidential_ok
      (mkConjVerb vf p n inc md pol vc nil
                  (Some (mkEvidential Ev_Voi None))) = true.
Proof. reflexivity. Qed.

(* §7.1: niko variants all render distinct strings *)
Theorem rule_EV3_niko_variants_distinct :
    render_evidential (mkEvidential Ev_Niko (Some NK_Niko)) = "niko" /\
    render_evidential (mkEvidential Ev_Niko (Some NK_Ko))   = "ko"   /\
    render_evidential (mkEvidential Ev_Niko (Some NK_Ngo))  = "ngo"  /\
    render_evidential (mkEvidential Ev_Niko (Some NK_Ningo)) = "ningo".
Proof. repeat split; reflexivity. Qed.

(* §7.3: kuri = direct evidence *)
Theorem rule_EV4_kuri_renders :
    render_evidential (mkEvidential Ev_Kuri None) = "kuri".
Proof. reflexivity. Qed.

(* §7.4: ra'e renders as "ra'e" *)
Theorem rule_EV5_rae_renders :
    render_evidential (mkEvidential Ev_Rae None) = "ra'e".
Proof. reflexivity. Qed.

(* §7.4: raka'e renders as "raka'e" *)
Theorem rule_EV6_rakae_renders :
    render_evidential (mkEvidential Ev_Rakae None) = "raka'e".
Proof. reflexivity. Qed.

(* §17.2: hearsay -je is a suffix, rightmost *)
Theorem rule_EV7_je_suffix_renders : forall o,
    render_verbal_suffix VS_HearsayJe o = "je".
Proof. reflexivity. Qed.

(*  Decidable equality *)

Scheme Equality for verb_class.
Scheme Equality for transitivity.
Scheme Equality for verb_root_class.
Scheme Equality for chendal_3sg_form.
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
Scheme Equality for niko_variant.
Scheme Equality for evidential_marker.