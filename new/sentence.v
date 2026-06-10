From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import Primitives.
Require Import NounPhrases.
Require Import Verb.

(* ============================================================ *)
(*  Sentences.v                                                 *)
(*  Guaraní sentence composition: how NPs and verbs combine     *)
(*  into well-formed sentences.                                 *)
(*                                                              *)
(*  Primary reference: "A Grammar of Paraguayan Guarani"        *)
(*  Chapter 8 (Basic Clauses), Chapter 12 (Complex Sentences)   *)
(*                                                              *)
(*  Scope: verbal sentences (intransitive, transitive,          *)
(*  ditransitive, postpositional complement). Non-verbal        *)
(*  sentences and complex/subordinate clauses are included as   *)
(*  lightweight wrappers but their morphology is not enforced.  *)
(* ============================================================ *)


(* ============================================================ *)
(*  1. Helpers bridging Verb.v and NounPhrases.v               *)
(* ============================================================ *)

(* Extract transitivity from the verb form regardless of regular
   or irregular dispatch. Irregular verbs ju/ho/'e are all
   intransitive in the grammar (§4.5). *)
Definition cv_transitivity (cv : conjugated_verb) : transitivity :=
  match cv_verb_form cv with
  | VF_Regular v   => v_transitivity v
  | VF_Irregular _ => Intransitive
  end.

(* Extract verb_class for hierarchy checks. Irregular verbs are
   treated as Areal for prefix-shape purposes. *)
Definition cv_class (cv : conjugated_verb) : verb_class :=
  match cv_verb_form cv with
  | VF_Regular v   => v_class v
  | VF_Irregular _ => Areal
  end.

(* §3.5.3: an NP counts as "negative" for double-negation purposes
   if it's a negative pronoun directly, or a negative indefinite
   (avave, mba'eve). *)
Definition is_negative_np (np : guarani_np) : bool :=
  match np with
  | NP_PronNeg _   => true
  | NP_PronIndef i => is_negative_pron i
  | _              => false
  end.

(* ============================================================ *)
(*  2. Word order                                               *)
(*  §8.1 "All six permutations are grammatical, though SVO and  *)
(*  VSO are most common. Order encodes information structure    *)
(*  (topic/focus), not grammatical relations."                  *)
(* ============================================================ *)

Inductive word_order : Type :=
  | WO_SVO | WO_SOV | WO_VSO | WO_VOS | WO_OSV | WO_OVS.

(* §4.1.1: hikuái must be postverbal — requires V-initial order *)
Definition is_v_initial (wo : word_order) : bool :=
  match wo with
  | WO_VSO | WO_VOS => true
  | _ => false
  end.

(* ============================================================ *)
(*  3. Sentence types                                           *)
(*  §8.5 "yes/no questions are marked with =pa or =piko"        *)
(* ============================================================ *)

Inductive sentence_type : Type :=
  | ST_Declarative
  | ST_Interrog_YN       (* yes/no question with =pa/=piko *)
  | ST_Interrog_Content  (* wh-question with interrogative NP *)
  | ST_Imperative
  | ST_Prohibitive.

Inductive interrog_particle : Type :=
  | IntP_Pa
  | IntP_Piko.

Definition render_interrog_particle (ip : interrog_particle) : string :=
  match ip with
  | IntP_Pa   => "pa"
  | IntP_Piko => "piko"
  end.

(* ============================================================ *)
(*  4. Simple verbal sentence                                   *)
(*                                                              *)
(*  §8.1 "Both subject drop and object drop are allowed and     *)
(*  very common." Subject and object are optional.              *)
(* ============================================================ *)

Record simple_sentence : Type := mkSentence {
  ss_subject   : option guarani_np;
  ss_verb      : conjugated_verb;
  ss_dir_obj   : option guarani_np;
  ss_indir_obj : option obj_indirect;
  ss_postp_obj : option (guarani_np * postposition);
  ss_order     : word_order;
  ss_type      : sentence_type;
  ss_interrog  : option interrog_particle;
  ss_hikuai    : bool
}.

(* ============================================================ *)
(*  5. Well-formedness predicates                               *)
(*                                                              *)
(*  Each predicate captures one orthogonal grammatical rule.    *)
(*  wf_sentence is their conjunction. Proofs about a single     *)
(*  constraint unfold only that predicate.                      *)
(* ============================================================ *)

(* --- 5.1: Subject-verb agreement (§8.1) --- *)
(* If a subject NP is present, person/number/inclusivity must
   match the verb. Null subjects always pass. *)

Definition ss_agree_ok (s : simple_sentence) : bool :=
  match ss_subject s with
  | None => true
  | Some subj =>
      let m := np_meta_of subj in
      person_eqb (np_person m) (cv_person (ss_verb s))
      && number_eqb (np_number m) (cv_number (ss_verb s))
      && (match np_person m, np_number m with
          | First, Plural =>
              (* inclusivity must match for 1pl *)
              match np_inclusivity m, cv_incl (ss_verb s) with
              | Some Inclusive, Some Inclusive => true
              | Some Exclusive, Some Exclusive => true
              | _, _ => false
              end
          | _, _ => true
          end)
  end.

(* --- 5.2: Transitivity matching (§4.1–4.4) --- *)
(* The verb's transitivity determines which argument slots
   may be filled. Direct objects may be dropped freely; we
   only check that the structural slots are consistent. *)

Definition ss_transitivity_ok (s : simple_sentence) : bool :=
  match cv_transitivity (ss_verb s) with
  | Intransitive =>
      match ss_dir_obj s, ss_indir_obj s, ss_postp_obj s with
      | None, None, None => true
      | _, _, _ => false
      end
  | Transitive =>
      match ss_indir_obj s, ss_postp_obj s with
      | None, None => true
      | _, _ => false
      end
  | Ditransitive =>
      match ss_postp_obj s with
      | None => true
      | Some _ => false
      end
  | PostpComplement =>
      match ss_postp_obj s, ss_dir_obj s, ss_indir_obj s with
      | Some _, None, None => true
      | _, _, _ => false
      end
  end.

(* --- 5.3: Person hierarchy for transitives (§4.2) --- *)
(* When both subject and object are explicit on a transitive
   verb, the prefix shape must follow 1 > 2 > 3. *)

Definition ss_hierarchy_ok (s : simple_sentence) : bool :=
  match cv_transitivity (ss_verb s) with
  | Transitive =>
      match ss_subject s, ss_dir_obj s with
      | Some subj, Some obj =>
          let sm := np_meta_of subj in
          let om := np_meta_of obj in
          let mode := trans_prefix_selection
                        (np_person sm) (np_number sm)
                        (np_person om) (np_number om) in
          match mode with
          | TPM_Active =>
              (* verb carries subject's features, non-Chendal class *)
              person_eqb (cv_person (ss_verb s)) (np_person sm)
              && number_eqb (cv_number (ss_verb s)) (np_number sm)
              && (match cv_class (ss_verb s) with
                  | Chendal => false
                  | _ => true
                  end)
          | TPM_Inactive =>
              (* verb carries object's features, Chendal class *)
              person_eqb (cv_person (ss_verb s)) (np_person om)
              && number_eqb (cv_number (ss_verb s)) (np_number om)
              && (match cv_class (ss_verb s) with
                  | Chendal => true
                  | _ => false
                  end)
          | TPM_Portmanteau _ =>
              (* portmanteau encodes both — verb shows 1st person *)
              person_eqb (cv_person (ss_verb s)) First
          | TPM_Reflexive =>
              (* reflexive uses passive/reciprocal voice *)
              match cv_voice (ss_verb s) with
              | Passive | Reciprocal => true
              | _ => false
              end
          end
      | _, _ => true  (* can't check without both args *)
      end
  | _ => true
  end.

(* --- 5.4: Double negation (§4.9, §3.5.3) --- *)
(* Negative pronouns require the verb to be negated. *)

Definition ss_neg_concord_ok (s : simple_sentence) : bool :=
  let has_neg :=
    (match ss_subject s with
     | Some np => is_negative_np np
     | None => false
     end)
    ||
    (match ss_dir_obj s with
     | Some np => is_negative_np np
     | None => false
     end) in
  if has_neg then
    match cv_polarity (ss_verb s) with
    | Negative => true
    | Positive => false
    end
  else true.

(* --- 5.5: Hikuái placement (§4.1.1) --- *)
(* hikuái 'they' must follow the verb: requires V-initial
   word order and a 3rd person verb. *)

Definition ss_hikuai_ok (s : simple_sentence) : bool :=
  if ss_hikuai s then
    person_eqb (cv_person (ss_verb s)) Third
    && is_v_initial (ss_order s)
  else true.

(* --- 5.6: Sentence type / mood consistency --- *)

Definition ss_type_ok (s : simple_sentence) : bool :=
  let md := cv_mood (ss_verb s) in
  match ss_type s with
  | ST_Declarative =>
      (match md with Indicative => true | _ => false end)
      && (match ss_interrog s with None => true | Some _ => false end)
  | ST_Interrog_YN =>
      (match md with Indicative => true | _ => false end)
      && (match ss_interrog s with Some _ => true | None => false end)
  | ST_Interrog_Content =>
      (match md with Indicative => true | _ => false end)
  | ST_Imperative =>
      (match md with Imperative | Optative => true | _ => false end)
      && (match ss_interrog s with None => true | Some _ => false end)
  | ST_Prohibitive =>
      (match md with Prohibitive => true | _ => false end)
      && (match ss_interrog s with None => true | Some _ => false end)
  end.

(* ============================================================ *)
(*  6. Master predicate                                         *)
(* ============================================================ *)

Definition wf_sentence (s : simple_sentence) : bool :=
  wf_conjugated_verb (ss_verb s)
  && ss_agree_ok        s
  && ss_transitivity_ok s
  && ss_hierarchy_ok    s
  && ss_neg_concord_ok  s
  && ss_hikuai_ok       s
  && ss_type_ok         s.

(* ============================================================ *)
(*  7. Decidable equality                                       *)
(* ============================================================ *)

Scheme Equality for word_order.
Scheme Equality for sentence_type.
Scheme Equality for interrog_particle.

(* ============================================================ *)
(*  8. Theorems                                                 *)
(*                                                              *)
(*  Organized by rule. With factored predicates, each proof     *)
(*  unfolds only the relevant constraint.                       *)
(* ============================================================ *)

(* ------------------------------------------------------------ *)
(*  RULE SA: Subject-verb agreement (§8.1)                     *)
(* ------------------------------------------------------------ *)

(* SA1: Null subjects are always fine. *)
Theorem rule_SA1_null_subject_ok : forall v dobj iobj pobj wo ty ip h,
    ss_agree_ok
      (mkSentence None v dobj iobj pobj wo ty ip h) = true.
Proof. reflexivity. Qed.

(* SA2: 1sg pronoun che agrees with 1sg verb. *)
Theorem rule_SA2_che_agrees_1sg : forall v dobj iobj pobj wo ty ip h,
    cv_person v = First ->
    cv_number v = Singular ->
    ss_agree_ok
      (mkSentence (Some (NP_PronSubj Subj1SG)) v dobj iobj pobj wo ty ip h)
      = true.
Proof.
  intros. unfold ss_agree_ok. simpl.
  rewrite H, H0. reflexivity.
Qed.

(* SA3: 1sg pronoun che does NOT agree with 2sg verb. *)
Theorem rule_SA3_che_2sg_disagree : forall v dobj iobj pobj wo ty ip h,
    cv_person v = Second ->
    ss_agree_ok
      (mkSentence (Some (NP_PronSubj Subj1SG)) v dobj iobj pobj wo ty ip h)
      = false.
Proof.
  intros. unfold ss_agree_ok. simpl. rewrite H. reflexivity.
Qed.

(* SA4: ñande (1pl.incl) does NOT agree with 1pl.excl verb. *)
Theorem rule_SA4_incl_excl_disagree : forall v dobj iobj pobj wo ty ip h,
    cv_person v = First ->
    cv_number v = Plural ->
    cv_incl v = Some Exclusive ->
    ss_agree_ok
      (mkSentence (Some (NP_PronSubj Subj1PL_INCL)) v dobj iobj pobj wo ty ip h)
      = false.
Proof.
  intros. unfold ss_agree_ok. simpl.
  rewrite H, H0, H1. reflexivity.
Qed.

(* ------------------------------------------------------------ *)
(*  RULE ST: Transitivity matching (§4.1–4.4)                  *)
(* ------------------------------------------------------------ *)

(* ST1: Intransitive with no objects is fine. *)
Theorem rule_ST1_intrans_no_args_ok : forall s v wo ty ip h,
    cv_transitivity v = Intransitive ->
    ss_transitivity_ok
      (mkSentence s v None None None wo ty ip h) = true.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

(* ST2: Intransitive with a direct object is ill-formed. *)
Theorem rule_ST2_intrans_with_obj_bad : forall s v obj wo ty ip h,
    cv_transitivity v = Intransitive ->
    ss_transitivity_ok
      (mkSentence s v (Some obj) None None wo ty ip h) = false.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

(* ST3: Transitive with a direct object is fine. *)
Theorem rule_ST3_trans_with_obj_ok : forall s v obj wo ty ip h,
    cv_transitivity v = Transitive ->
    ss_transitivity_ok
      (mkSentence s v (Some obj) None None wo ty ip h) = true.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

(* ST4: Transitive with an indirect object is ill-formed. *)
Theorem rule_ST4_trans_with_iobj_bad : forall s v obj iobj wo ty ip h,
    cv_transitivity v = Transitive ->
    ss_transitivity_ok
      (mkSentence s v obj (Some iobj) None wo ty ip h) = false.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H.
  destruct obj; reflexivity.
Qed.

(* ST5: PostpComplement verb without postpositional phrase is bad. *)
Theorem rule_ST5_postpcomp_no_phrase_bad : forall s v wo ty ip h,
    cv_transitivity v = PostpComplement ->
    ss_transitivity_ok
      (mkSentence s v None None None wo ty ip h) = false.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

(* ST6: PostpComplement verb with postpositional phrase is fine. *)
Theorem rule_ST6_postpcomp_with_phrase_ok : forall s v np pp wo ty ip h,
    cv_transitivity v = PostpComplement ->
    ss_transitivity_ok
      (mkSentence s v None None (Some (np, pp)) wo ty ip h) = true.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

(* ------------------------------------------------------------ *)
(*  RULE SH: Person hierarchy (§4.2)                           *)
(* ------------------------------------------------------------ *)

(* SH1: No subject or no object → hierarchy check passes. *)
Theorem rule_SH1_partial_args_ok : forall v dobj iobj pobj wo ty ip h,
    cv_transitivity v = Transitive ->
    ss_hierarchy_ok
      (mkSentence None v dobj iobj pobj wo ty ip h) = true.
Proof.
  intros. unfold ss_hierarchy_ok. rewrite H. reflexivity.
Qed.

(* SH2: Non-transitive verbs skip the hierarchy check. *)
Theorem rule_SH2_intrans_skips_check : forall s v dobj iobj pobj wo ty ip h,
    cv_transitivity v = Intransitive ->
    ss_hierarchy_ok
      (mkSentence s v dobj iobj pobj wo ty ip h) = true.
Proof.
  intros. unfold ss_hierarchy_ok. rewrite H. reflexivity.
Qed.

(* ------------------------------------------------------------ *)
(*  RULE SN: Double negation (§4.9, §3.5.3)                    *)
(* ------------------------------------------------------------ *)

(* SN1: avave subject + positive verb is ill-formed. *)
Theorem rule_SN1_avave_pos_bad : forall v dobj iobj pobj wo ty ip h,
    cv_polarity v = Positive ->
    ss_neg_concord_ok
      (mkSentence (Some (NP_PronNeg NegPron_Avave)) v
                  dobj iobj pobj wo ty ip h) = false.
Proof.
  intros. unfold ss_neg_concord_ok. simpl. rewrite H. reflexivity.
Qed.

(* SN2: avave subject + negative verb is fine. *)
Theorem rule_SN2_avave_neg_ok : forall v dobj iobj pobj wo ty ip h,
    cv_polarity v = Negative ->
    ss_neg_concord_ok
      (mkSentence (Some (NP_PronNeg NegPron_Avave)) v
                  dobj iobj pobj wo ty ip h) = true.
Proof.
  intros. unfold ss_neg_concord_ok. simpl. rewrite H. reflexivity.
Qed.

(* SN3: mba'eve object + positive verb is ill-formed. *)
Theorem rule_SN3_mbaeve_obj_pos_bad : forall s v iobj pobj wo ty ip h,
    cv_polarity v = Positive ->
    ss_neg_concord_ok
      (mkSentence s v (Some (NP_PronNeg NegPron_Mbaeve))
                  iobj pobj wo ty ip h) = false.
Proof.
  intros. unfold ss_neg_concord_ok. simpl. rewrite H.
  destruct s as [np|]; simpl; try reflexivity.
  destruct np; reflexivity.
Qed.

(* SN4: Non-negative subject + positive verb is fine. *)
Theorem rule_SN4_normal_pos_ok : forall v dobj iobj pobj wo ty ip h,
    cv_polarity v = Positive ->
    ss_neg_concord_ok
      (mkSentence (Some (NP_PronSubj Subj1SG)) v
                  dobj iobj pobj wo ty ip h) = true.
Proof.
  intros. unfold ss_neg_concord_ok. simpl.
  destruct dobj as [obj|]; simpl; try reflexivity.
  destruct obj; simpl; try reflexivity;
  try (rewrite H; reflexivity).
  (* indef pronoun case *)
  destruct i; reflexivity.
Qed.

(* ------------------------------------------------------------ *)
(*  RULE SK: Hikuái placement (§4.1.1)                         *)
(* ------------------------------------------------------------ *)

(* SK1: hikuái absent → no constraint. *)
Theorem rule_SK1_no_hikuai_ok : forall s v dobj iobj pobj wo ty ip,
    ss_hikuai_ok
      (mkSentence s v dobj iobj pobj wo ty ip false) = true.
Proof. reflexivity. Qed.

(* SK2: hikuái with 1st person verb is ill-formed. *)
Theorem rule_SK2_hikuai_1sg_bad : forall s v dobj iobj pobj wo ty ip,
    cv_person v = First ->
    ss_hikuai_ok
      (mkSentence s v dobj iobj pobj wo ty ip true) = false.
Proof.
  intros. unfold ss_hikuai_ok. simpl. rewrite H. reflexivity.
Qed.

(* SK3: hikuái with SVO order is ill-formed. *)
Theorem rule_SK3_hikuai_svo_bad : forall s v dobj iobj pobj ty ip,
    cv_person v = Third ->
    ss_hikuai_ok
      (mkSentence s v dobj iobj pobj WO_SVO ty ip true) = false.
Proof.
  intros. unfold ss_hikuai_ok. simpl. rewrite H. reflexivity.
Qed.

(* SK4: hikuái with VSO order and 3rd person verb is fine. *)
Theorem rule_SK4_hikuai_vso_ok : forall s v dobj iobj pobj ty ip,
    cv_person v = Third ->
    ss_hikuai_ok
      (mkSentence s v dobj iobj pobj WO_VSO ty ip true) = true.
Proof.
  intros. unfold ss_hikuai_ok. simpl. rewrite H. reflexivity.
Qed.

(* ------------------------------------------------------------ *)
(*  RULE SY: Sentence type / mood consistency                  *)
(* ------------------------------------------------------------ *)

(* SY1: Declarative requires Indicative mood. *)
Theorem rule_SY1_decl_needs_indicative : forall s v dobj iobj pobj wo ip h,
    cv_mood v = Imperative ->
    ss_type_ok
      (mkSentence s v dobj iobj pobj wo ST_Declarative ip h) = false.
Proof.
  intros. unfold ss_type_ok. simpl. rewrite H. reflexivity.
Qed.

(* SY2: Declarative with interrogative particle is ill-formed. *)
Theorem rule_SY2_decl_no_particle : forall s v dobj iobj pobj wo h,
    cv_mood v = Indicative ->
    ss_type_ok
      (mkSentence s v dobj iobj pobj wo ST_Declarative (Some IntP_Pa) h)
      = false.
Proof.
  intros. unfold ss_type_ok. simpl. rewrite H. reflexivity.
Qed.

(* SY3: Yes/no question without particle is ill-formed. *)
Theorem rule_SY3_yn_needs_particle : forall s v dobj iobj pobj wo h,
    cv_mood v = Indicative ->
    ss_type_ok
      (mkSentence s v dobj iobj pobj wo ST_Interrog_YN None h) = false.
Proof.
  intros. unfold ss_type_ok. simpl. rewrite H. reflexivity.
Qed.

(* SY4: Imperative with Indicative mood is ill-formed. *)
Theorem rule_SY4_imp_needs_imp_mood : forall s v dobj iobj pobj wo ip h,
    cv_mood v = Indicative ->
    ss_type_ok
      (mkSentence s v dobj iobj pobj wo ST_Imperative ip h) = false.
Proof.
  intros. unfold ss_type_ok. simpl. rewrite H. reflexivity.
Qed.

(* SY5: Prohibitive with Indicative mood is ill-formed. *)
Theorem rule_SY5_prohib_needs_prohib_mood : forall s v dobj iobj pobj wo ip h,
    cv_mood v = Indicative ->
    ss_type_ok
      (mkSentence s v dobj iobj pobj wo ST_Prohibitive ip h) = false.
Proof.
  intros. unfold ss_type_ok. simpl. rewrite H. reflexivity.
Qed.

(* ============================================================ *)
(*  9. Non-verbal sentences (§8.2, §8.3, §8.4)                 *)
(*                                                              *)
(*  Lightweight types — well-formedness just delegates to       *)
(*  wf_np on the constituent NPs. The juxtaposition morphology *)
(*  itself isn't enforced here.                                 *)
(* ============================================================ *)

Inductive nonverbal_sentence : Type :=
  | NVS_Equative    : guarani_np -> guarani_np -> nonverbal_sentence
  | NVS_Predicative : guarani_np -> guarani_np -> nonverbal_sentence
  | NVS_Existential : guarani_np -> nonverbal_sentence
  | NVS_Possessive  : option guarani_np -> guarani_np -> nonverbal_sentence.

Definition wf_nonverbal (nvs : nonverbal_sentence) : bool :=
  match nvs with
  | NVS_Equative a b    => wf_np a && wf_np b
  | NVS_Predicative a b => wf_np a && wf_np b
  | NVS_Existential a   => wf_np a
  | NVS_Possessive (Some p) q => wf_np p && wf_np q
  | NVS_Possessive None q     => wf_np q
  end.

(* ============================================================ *)
(*  10. Complex sentences (§12)                                *)
(*                                                              *)
(*  Lightweight wrappers. Subordination morphology              *)
(*  (-ramo, -haguã, -jave, etc.) is not checked here.           *)
(* ============================================================ *)

Inductive complex_sentence : Type :=
  | CS_Simple      : simple_sentence -> complex_sentence
  | CS_Coordinated : simple_sentence -> simple_sentence -> complex_sentence
  | CS_Conditional : simple_sentence -> simple_sentence -> complex_sentence
  | CS_Purposive   : simple_sentence -> simple_sentence -> complex_sentence
  | CS_Temporal    : simple_sentence -> simple_sentence -> complex_sentence.

Definition wf_complex (cs : complex_sentence) : bool :=
  match cs with
  | CS_Simple s                => wf_sentence s
  | CS_Coordinated s1 s2       => wf_sentence s1 && wf_sentence s2
  | CS_Conditional prot apod   => wf_sentence prot && wf_sentence apod
  | CS_Purposive main purp     => wf_sentence main && wf_sentence purp
  | CS_Temporal main temp      => wf_sentence main && wf_sentence temp
  end.

(* ============================================================ *)
(*  11. Unified top-level sentence type                         *)
(* ============================================================ *)

Inductive sentence : Type :=
  | Sent_Simple    : simple_sentence    -> sentence
  | Sent_Nonverbal : nonverbal_sentence -> sentence
  | Sent_Complex   : complex_sentence   -> sentence.

Definition wf_any_sentence (s : sentence) : bool :=
  match s with
  | Sent_Simple ss    => wf_sentence ss
  | Sent_Nonverbal nv => wf_nonverbal nv
  | Sent_Complex cs   => wf_complex cs
  end.

(* ============================================================ *)
(*  12. Additional theorems for non-verbal and complex          *)
(* ============================================================ *)

Theorem rule_NV1_equative_wf : forall a b,
    wf_np a = true -> wf_np b = true ->
    wf_nonverbal (NVS_Equative a b) = true.
Proof. intros a b Ha Hb. simpl. rewrite Ha, Hb. reflexivity. Qed.

Theorem rule_NV2_existential_wf : forall a,
    wf_np a = true -> wf_nonverbal (NVS_Existential a) = true.
Proof. intros. simpl. exact H. Qed.

Theorem rule_CX1_coord_both_wf : forall s1 s2,
    wf_sentence s1 = true -> wf_sentence s2 = true ->
    wf_complex (CS_Coordinated s1 s2) = true.
Proof. intros s1 s2 H1 H2. simpl. rewrite H1, H2. reflexivity. Qed.

Theorem rule_CX2_coord_bad_first : forall s1 s2,
    wf_sentence s1 = false ->
    wf_complex (CS_Coordinated s1 s2) = false.
Proof. intros s1 s2 H. simpl. rewrite H. reflexivity. Qed.

Theorem rule_TL1_simple_lifts : forall s,
    wf_sentence s = true ->
    wf_any_sentence (Sent_Simple s) = true.
Proof. intros. simpl. exact H. Qed.

(* ============================================================ *)
(*  13. Examples                                                *)
(*                                                              *)
(*  All examples use generic verb variables — they assert the   *)
(*  shape of well-formedness, not specific lexical items.       *)
(* ============================================================ *)

(* A bare intransitive declarative is well-formed if the verb is. *)
Example ex_bare_intrans : forall v,
    wf_conjugated_verb v = true ->
    cv_transitivity v = Intransitive ->
    cv_mood v = Indicative ->
    cv_person v = First ->
    cv_number v = Singular ->
    cv_incl v = None ->
    wf_sentence
      (mkSentence None v None None None
                  WO_SVO ST_Declarative None false) = true.
Proof.
  intros v Hv Ht Hm Hp Hn Hi.
  unfold wf_sentence. rewrite Hv. simpl.
  unfold ss_transitivity_ok. simpl. rewrite Ht. simpl.
  unfold ss_hierarchy_ok. rewrite Ht. simpl.
  unfold ss_type_ok. simpl. rewrite Hm. reflexivity.
Qed.

(* Intransitive verb with a stray direct object is ill-formed. *)
Example ex_intrans_with_obj_bad : forall v obj,
    cv_transitivity v = Intransitive ->
    wf_sentence
      (mkSentence None v (Some obj) None None
                  WO_SVO ST_Declarative None false) = false.
Proof.
  intros v obj Ht.
  unfold wf_sentence. simpl.
  unfold ss_transitivity_ok. simpl. rewrite Ht. simpl.
  destruct (wf_conjugated_verb v); reflexivity.
Qed.

(* avave + positive verb is ill-formed (double negation violation). *)
Example ex_avave_pos_bad : forall v,
    cv_polarity v = Positive ->
    wf_sentence
      (mkSentence (Some (NP_PronNeg NegPron_Avave)) v None None None
                  WO_SVO ST_Declarative None false) = false.
Proof.
  intros v Hp.
  unfold wf_sentence. simpl.
  unfold ss_neg_concord_ok. simpl. rewrite Hp. simpl.
  destruct (wf_conjugated_verb v); simpl;
  destruct (ss_agree_ok _); simpl;
  destruct (ss_transitivity_ok _); simpl;
  destruct (ss_hierarchy_ok _); reflexivity.
Qed.

(* hikuái requires V-initial order. *)
Example ex_hikuai_svo_bad : forall v,
    cv_person v = Third ->
    wf_sentence
      (mkSentence None v None None None
                  WO_SVO ST_Declarative None true) = false.
Proof.
  intros v Hp.
  unfold wf_sentence. simpl.
  unfold ss_hikuai_ok. simpl. rewrite Hp. simpl.
  destruct (wf_conjugated_verb v); simpl;
  destruct (ss_agree_ok _); simpl;
  destruct (ss_transitivity_ok _); simpl;
  destruct (ss_hierarchy_ok _); simpl;
  destruct (ss_neg_concord_ok _); reflexivity.
Qed.