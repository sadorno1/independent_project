From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import Syntax.
Require Import noun_phrases.
Require Import verb.
From Stdlib Require Import Ascii.
(* ============================================================ *)
(*  Sentences.v                                                 *)
(*  How NPs and verbs combine into well-formed sentences.       *)
(* ============================================================ *)


(* ============================================================ *)
(*  1. Helpers                                                  *)
(* ============================================================ *)

Definition cv_transitivity (cv : conjugated_verb) : transitivity :=
  match cv_verb_form cv with
  | VF_Regular v   => v_transitivity v
  | VF_Irregular _ => Intransitive
  end.

Definition cv_class (cv : conjugated_verb) : verb_class :=
  match cv_verb_form cv with
  | VF_Regular v   => v_class v
  | VF_Irregular _ => Areal
  end.

Definition is_negative_np (np : guarani_np) : bool :=
  match np with
  | NP_PronNeg _   => true
  | NP_PronIndef i => is_negative_pron i
  | _              => false
  end.

(* §5.1: is this NP headed by a [+human] noun? Used for =pe/=me check. *)
Fixpoint np_is_human (np : guarani_np) : bool :=
  match np with
  | NP_Bare n           => n_human n
  | NP_Dem _ _ n        => n_human n
  | NP_Art _ n          => n_human n
  | NP_Adj n _          => n_human n
  | NP_Poss _ n         => n_human n
  | NP_Num _ n          => n_human n
  | NP_Gen _ n          => n_human n
  | NP_DemPoss _ _ n    => n_human n
  | NP_Rel n _          => n_human n
  | NP_Comp _           => false   (* complement clause referent is abstract *)
  | NP_Suf inner _      => np_is_human inner
  | NP_Suf2 inner _ _   => np_is_human inner
  | NP_PronSubj _       => true    (* subject pronouns are always human *)
  | NP_PronPoss _       => true
  | NP_PronDem _ _      => false   (* demonstrative pronouns: no inherent humanness *)
  | NP_PronIndef i      =>
      match i with
      | Indef_Avave | Indef_Maymava | Indef_Opava => true
      | _ => false
      end
  | NP_PronInterrog i   =>
      match i with Interrog_Mava | Interrog_Avambae => true | _ => false end
  | NP_PronNeg np       =>
      match np with NegPron_Avave => true | _ => false end
  | NP_CoordHa x1 _    => np_is_human x1
  | NP_CoordTera x1 _  => np_is_human x1
  end.

(* ============================================================ *)
(*  2. Word order §8.1                                          *)
(* ============================================================ *)

Inductive word_order : Type :=
  | WO_SVO | WO_SOV | WO_VSO | WO_VOS | WO_OSV | WO_OVS.

Definition is_v_initial (wo : word_order) : bool :=
  match wo with WO_VSO | WO_VOS => true | _ => false end.

(* ============================================================ *)
(*  3. Sentence types §8.5                                      *)
(* ============================================================ *)

Inductive sentence_type : Type :=
  | ST_Declarative
  | ST_Interrog_YN
  | ST_Interrog_Content
  | ST_Imperative
  | ST_Prohibitive.

Inductive interrog_particle : Type :=
  | IntP_Pa | IntP_Piko.

Definition render_interrog_particle (ip : interrog_particle) : string :=
  match ip with IntP_Pa => "pa" | IntP_Piko => "piko" end.

(* ============================================================ *)
(*  4. Simple verbal sentence                                   *)
(*  ss_indir_obj is now option guarani_np, not option           *)
(*  obj_indirect. This lets neg-concord and human-pe checks     *)
(*  scan the IO NP directly.                                    *)
(* ============================================================ *)

Record simple_sentence : Type := mkSentence {
  ss_subject   : option guarani_np;
  ss_verb      : conjugated_verb;
  ss_dir_obj   : option guarani_np;
  ss_indir_obj : option guarani_np;   (* changed: was option obj_indirect *)
  ss_postp_obj : option (guarani_np * postposition);
  ss_order     : word_order;
  ss_type      : sentence_type;
  ss_interrog  : option interrog_particle;
  ss_hikuai    : bool
}.

Definition person_eqb (p1 p2 : person) : bool :=
  match p1, p2 with
  | First, First => true
  | Second, Second => true
  | Third, Third => true
  | _, _ => false
  end.

Definition number_eqb (n1 n2 : number) : bool :=
  match n1, n2 with
  | Singular, Singular => true
  | Plural, Plural => true
  | _, _ => false
  end.
(* ============================================================ *)
(*  5. Factored well-formedness predicates                      *)
(* ============================================================ *)

(* --- 5.1: Subject-verb agreement §8.1 --- *)
Definition ss_agree_ok (s : simple_sentence) : bool :=
  match ss_subject s with
  | None => true
  | Some subj =>
      let m := np_meta_of subj in
      person_eqb (np_person m) (cv_person (ss_verb s))
      && number_eqb (np_number m) (cv_number (ss_verb s))
      && (match np_person m, np_number m with
          | First, Plural =>
              match np_inclusivity m, cv_incl (ss_verb s) with
              | Some Inclusive, Some Inclusive => true
              | Some Exclusive, Some Exclusive => true
              | _, _ => false
              end
          | _, _ => true
          end)
  end.

(* --- 5.2: Transitivity matching §4.1-§4.4 --- *)
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
      | Some _ => false
      | None =>
          match ss_dir_obj s, ss_indir_obj s with
          | None, Some _ => false   (* IO without DO — Option B *)
          | _, _ => true
          end
      end
  | PostpComplement =>
      match ss_postp_obj s, ss_dir_obj s, ss_indir_obj s with
      | Some _, None, None => true
      | _, _, _ => false
      end
  end.

(* --- 5.3: Person hierarchy for transitives §4.2 --- *)
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
              person_eqb (cv_person (ss_verb s)) (np_person sm)
              && number_eqb (cv_number (ss_verb s)) (np_number sm)
              && (match cv_class (ss_verb s) with Chendal => false | _ => true end)
          | TPM_Inactive =>
              person_eqb (cv_person (ss_verb s)) (np_person om)
              && number_eqb (cv_number (ss_verb s)) (np_number om)
              && (match cv_class (ss_verb s) with Chendal => true | _ => false end)
          | TPM_Portmanteau _ =>
              person_eqb (cv_person (ss_verb s)) First
          | TPM_Reflexive =>
              match cv_voice (ss_verb s) with
              | Passive | Reciprocal => true
              | _ => false
              end
          end
      | _, _ => true
      end
  | _ => true
  end.

(* --- 5.4: Double negation §4.9, §3.5.3 ---
   Now scans subject, direct object, AND indirect object (since IO
   is now a full guarani_np). *)
Definition ss_neg_concord_ok (s : simple_sentence) : bool :=
  let has_neg :=
    (match ss_subject s with Some np => is_negative_np np | None => false end)
    || (match ss_dir_obj s with Some np => is_negative_np np | None => false end)
    || (match ss_indir_obj s with Some np => is_negative_np np | None => false end)
  in
  if has_neg then
    match cv_polarity (ss_verb s) with
    | Negative => true
    | Positive => false
    end
  else true.

(* --- 5.5: Hikuái placement §4.1.1 --- *)
Definition ss_hikuai_ok (s : simple_sentence) : bool :=
  if ss_hikuai s then
    person_eqb (cv_person (ss_verb s)) Third && is_v_initial (ss_order s)
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

(* --- 5.7: Human direct object requires =pe/=me §5.1 ---
   When the verb is PostpComplement and the postposition object NP is
   [+human], the postposition must be Post_Pe (which renders as pe/me
   by orality). This enforces the [+human] → =pe/=me marking.
   §5.1: "postposition =pe/=me is used to mark human direct objects"
   Note: this applies to PostpComplement verbs where the postpositional
   complement is the [+human] direct object. Non-human objects use
   other postpositions freely. *)
Definition ss_human_pe_ok (s : simple_sentence) : bool :=
  match ss_postp_obj s with
  | None => true
  | Some (np, pp) =>
      if np_is_human np then
        match pp with
        | Post_Pe => true
        | _ => false
        end
      else true
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
  && ss_type_ok         s
  && ss_human_pe_ok     s.

(* ============================================================ *)
(*  7. Adverbial clause types §12.2.3                          *)
(*                                                              *)
(*  Each constructor carries the surface subordinating morpheme *)
(*  as a string. The wf predicate checks that the morpheme      *)
(*  matches the expected form for its type.                     *)
(*                                                              *)
(*  Morpheme canonicals:                                        *)
(*   Purposive:          =haguã (post-verb)                     *)
(*   PurpNeg:            ani haguã (pre-verb)                   *)
(*   PurpSimult:         -vo (movement-verb context)            *)
(*   Concessive:         ramo jepe                              *)
(*   ConcessPotential:   jepe (with optative on subord clause)  *)
(*   Causal_Gui/Rehe/Rupi: =gui / =rehe / =rupi                *)
(*   Causal_Porque:      porque (Spanish borrowing)             *)
(*   Cond_Hyp:           =rõ or =ramo (free variation)         *)
(*   Cond_Counter:       =rire on subord + -va'erã-mo'ã on main *)
(*   Manner:             -ha-icha or -hague-icha (past)         *)
(*   Temp_Simult:        =ramo/=rõ (stressed, = "when") or     *)
(*                       -vo or aja or jave                     *)
(*   Temp_Ant:           mboyve                                 *)
(*   Temp_Post:          rire (stressed) or vove                *)
(*   Locative:           -ha + postposition                     *)
(* ============================================================ *)

Inductive adv_clause_type : Type :=
  | AC_Purposive          (* haguã — purpose §12.2.3.1 *)
  | AC_PurpNeg            (* ani haguã — negative purpose §12.2.3.1 *)
  | AC_PurpSimult         (* -vo — purpose with movement verb §12.2.3.1 *)
  | AC_Concessive         (* ramo jepe — concessive §12.2.3.2 *)
  | AC_ConcessPotential   (* jepe + optative — potential concessive §12.2.3.2 *)
  | AC_Causal_Gui         (* =gui — causal §12.2.3.3 *)
  | AC_Causal_Rehe        (* =rehe — causal §12.2.3.3 *)
  | AC_Causal_Rupi        (* =rupi — causal §12.2.3.3 *)
  | AC_Causal_Porque      (* porque — causal (Spanish borrowing) §12.2.3.3 *)
  | AC_Cond_Hyp           (* =rõ/=ramo — hypothetical conditional §12.2.3.4 *)
  | AC_Cond_Counter       (* =rire on subord — counterfactual §12.2.3.4 *)
  | AC_Manner             (* -ha-icha / -hague-icha — manner §12.2.3.5 *)
  | AC_Temp_Simult        (* =ramo/=rõ (stressed) / -vo / aja / jave §12.2.3.6 *)
  | AC_Temp_Ant           (* mboyve — before §12.2.3.6 *)
  | AC_Temp_Post          (* rire (stressed) / vove — after §12.2.3.6 *)
  | AC_Locative.          (* -ha + postposition §12.2.3.7 *)

(* Expected morpheme surface forms for each adverbial clause type *)
Definition adv_morpheme_ok (t : adv_clause_type) (m : string) : bool :=
      match t with
  | AC_Purposive        => if string_dec m "haguã"     then true else false
  | AC_PurpNeg          => if string_dec m "ani haguã" then true else false
  | AC_PurpSimult       => if string_dec m "vo"        then true else false
  | AC_Concessive       => if string_dec m "ramo jepe" then true else false
  | AC_ConcessPotential => if string_dec m "jepe"      then true else false
  | AC_Causal_Gui       => if string_dec m "gui"       then true else false
  | AC_Causal_Rehe      =>
      if string_dec m "rehe" then true
      else if string_dec m "re" then true else false
  | AC_Causal_Rupi      => if string_dec m "rupi"      then true else false
  | AC_Causal_Porque    => if string_dec m "porque"    then true else false
  | AC_Cond_Hyp         =>
      if string_dec m "rõ"   then true
      else if string_dec m "ramo" then true else false
  | AC_Cond_Counter     => if string_dec m "rire"      then true else false
  | AC_Manner           =>
      if string_dec m "ha-icha"    then true
      else if string_dec m "hague-icha" then true else false
  | AC_Temp_Simult      =>
      if string_dec m "ramo" then true
      else if string_dec m "rõ"   then true
      else if string_dec m "vo"   then true
      else if string_dec m "aja"  then true
      else if string_dec m "jave" then true else false
  | AC_Temp_Ant         => if string_dec m "mboyve"    then true else false
  | AC_Temp_Post        =>
      if string_dec m "rire" then true
      else if string_dec m "vove" then true else false
  | AC_Locative         =>
      (* -ha + any postposition; we check it starts with "ha" *)
      match m with
      | String h (String a _) =>
          if (Ascii.ascii_dec h "h"%char) then
            if (Ascii.ascii_dec a "a"%char) then true else false
          else false
      | _ => false
      end
  end.

Record adv_clause : Type := mkAdvClause {
  ac_type   : adv_clause_type;
  ac_subord : string    (* surface subordinating morpheme *)
}.

Definition wf_adv_clause (ac : adv_clause) : bool :=
  adv_morpheme_ok (ac_type ac) (ac_subord ac).

(* Counterfactual conditional: the main clause verb must carry
   both VS_ObligVaera and VS_FutNegMoa §12.2.3.4 *)
Definition wf_counterfactual_main (cv : conjugated_verb) : bool :=
  has_verbal_suffix (cv_suffixes cv) VS_ObligVaera
  && has_verbal_suffix (cv_suffixes cv) VS_FutNegMoa.

(* ============================================================ *)
(*  8. Non-verbal sentences §8.2-§8.4                          *)
(* ============================================================ *)

Inductive nonverbal_sentence : Type :=
  | NVS_Equative    : guarani_np -> guarani_np -> nonverbal_sentence
  | NVS_Predicative : guarani_np -> guarani_np -> nonverbal_sentence
  | NVS_Existential : guarani_np -> nonverbal_sentence
  | NVS_Possessive  : option guarani_np -> guarani_np -> nonverbal_sentence.

Definition wf_nonverbal (nvs : nonverbal_sentence) : bool :=
  match nvs with
  | NVS_Equative a b          => wf_np a && wf_np b
  | NVS_Predicative a b       => wf_np a && wf_np b
  | NVS_Existential a         => wf_np a
  | NVS_Possessive (Some p) q => wf_np p && wf_np q
  | NVS_Possessive None q     => wf_np q
  end.

(* ============================================================ *)
(*  9. Complex sentences §12                                    *)
(*  CS_Adverbial replaces CS_Conditional/CS_Purposive/          *)
(*  CS_Temporal with a unified constructor carrying the         *)
(*  adverbial clause descriptor.                                *)
(*  CS_Coordinated and CS_Simple kept as-is.                    *)
(*  CS_Counterfactual separated out because it has an extra     *)
(*  wf condition on the main clause morphology.                 *)
(* ============================================================ *)

Inductive complex_sentence : Type :=
  | CS_Simple         : simple_sentence -> complex_sentence
  | CS_Coordinated    : simple_sentence -> simple_sentence -> complex_sentence
  | CS_Adverbial      : simple_sentence (* main *)
                      -> adv_clause
                      -> simple_sentence (* subordinate *)
                      -> complex_sentence
  | CS_Counterfactual : simple_sentence (* main — must have va'erã-mo'ã *)
                      -> simple_sentence (* subord — =rire *)
                      -> complex_sentence.

Definition wf_complex (cs : complex_sentence) : bool :=
  match cs with
  | CS_Simple s =>
      wf_sentence s

  | CS_Coordinated s1 s2 =>
      wf_sentence s1 && wf_sentence s2

  | CS_Adverbial main ac subord =>
      wf_sentence main
      && wf_sentence subord
      && wf_adv_clause ac

  | CS_Counterfactual main subord =>
      wf_sentence main
      && wf_sentence subord
      && wf_counterfactual_main (ss_verb main)
  end.

(* ============================================================ *)
(*  10. Unified top-level sentence type                         *)
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
(*  11. Decidable equality                                      *)
(* ============================================================ *)

Scheme Equality for word_order.
Scheme Equality for sentence_type.
Scheme Equality for interrog_particle.
Scheme Equality for adv_clause_type.

(* ============================================================ *)
(*  12. Theorems                                                *)
(* ============================================================ *)

(* ---------- SA: subject-verb agreement §8.1 ---------- *)

Theorem rule_SA1_null_subject_ok : forall v dobj iobj pobj wo ty ip h,
    ss_agree_ok (mkSentence None v dobj iobj pobj wo ty ip h) = true.
Proof. reflexivity. Qed.

Theorem rule_SA2_che_agrees_1sg : forall v dobj iobj pobj wo ty ip h,
    cv_person v = First ->
    cv_number v = Singular ->
    ss_agree_ok
      (mkSentence (Some (NP_PronSubj Subj1SG)) v dobj iobj pobj wo ty ip h)
      = true.
Proof.
  intros. unfold ss_agree_ok. simpl. rewrite H, H0. reflexivity.
Qed.

Theorem rule_SA3_che_2sg_disagree : forall v dobj iobj pobj wo ty ip h,
    cv_person v = Second ->
    ss_agree_ok
      (mkSentence (Some (NP_PronSubj Subj1SG)) v dobj iobj pobj wo ty ip h)
      = false.
Proof.
  intros. unfold ss_agree_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_SA4_incl_excl_disagree : forall v dobj iobj pobj wo ty ip h,
    cv_person v = First ->
    cv_number v = Plural ->
    cv_incl v = Some Exclusive ->
    ss_agree_ok
      (mkSentence (Some (NP_PronSubj Subj1PL_INCL)) v dobj iobj pobj wo ty ip h)
      = false.
Proof.
  intros. unfold ss_agree_ok. simpl. rewrite H, H0, H1. reflexivity.
Qed.

(* ---------- ST: transitivity §4.1-§4.4 ---------- *)

Theorem rule_ST1_intrans_no_args_ok : forall s v wo ty ip h,
    cv_transitivity v = Intransitive ->
    ss_transitivity_ok
      (mkSentence s v None None None wo ty ip h) = true.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_ST2_intrans_with_obj_bad : forall s v obj wo ty ip h,
    cv_transitivity v = Intransitive ->
    ss_transitivity_ok
      (mkSentence s v (Some obj) None None wo ty ip h) = false.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_ST3_trans_with_obj_ok : forall s v obj wo ty ip h,
    cv_transitivity v = Transitive ->
    ss_transitivity_ok
      (mkSentence s v (Some obj) None None wo ty ip h) = true.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_ST7_ditrans_iobj_without_dobj_bad : forall s v iobj wo ty ip h,
    cv_transitivity v = Ditransitive ->
    ss_transitivity_ok
      (mkSentence s v None (Some iobj) None wo ty ip h) = false.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_ST8_ditrans_both_ok : forall s v obj iobj wo ty ip h,
    cv_transitivity v = Ditransitive ->
    ss_transitivity_ok
      (mkSentence s v (Some obj) (Some iobj) None wo ty ip h) = true.
Proof.
  intros. unfold ss_transitivity_ok. simpl. rewrite H. reflexivity.
Qed.

(* ---------- SH: person hierarchy §4.2 ---------- *)

Theorem rule_SH1_partial_args_ok : forall v dobj iobj pobj wo ty ip h,
    cv_transitivity v = Transitive ->
    ss_hierarchy_ok
      (mkSentence None v dobj iobj pobj wo ty ip h) = true.
Proof.
  intros. unfold ss_hierarchy_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_SH2_intrans_skips_check : forall s v dobj iobj pobj wo ty ip h,
    cv_transitivity v = Intransitive ->
    ss_hierarchy_ok
      (mkSentence s v dobj iobj pobj wo ty ip h) = true.
Proof.
  intros. unfold ss_hierarchy_ok. simpl. rewrite H. reflexivity.
Qed.

(* ---------- SN: double negation §4.9, §3.5.3 ---------- *)

Theorem rule_SN1_avave_subj_pos_bad : forall v dobj iobj pobj wo ty ip h,
    cv_polarity v = Positive ->
    ss_neg_concord_ok
      (mkSentence (Some (NP_PronNeg NegPron_Avave)) v
                  dobj iobj pobj wo ty ip h) = false.
Proof.
  intros. unfold ss_neg_concord_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_SN2_avave_subj_neg_ok : forall v dobj iobj pobj wo ty ip h,
    cv_polarity v = Negative ->
    ss_neg_concord_ok
      (mkSentence (Some (NP_PronNeg NegPron_Avave)) v
                  dobj iobj pobj wo ty ip h) = true.
Proof.
  intros. unfold ss_neg_concord_ok. simpl. rewrite H. reflexivity.
Qed.

(* SN3: negative IO also triggers neg-concord requirement. Source: Claude*)
Theorem rule_SN3_neg_iobj_pos_bad : forall s v dobj wo ty ip h,
    cv_polarity v = Positive ->
    ss_neg_concord_ok
      (mkSentence s v dobj (Some (NP_PronNeg NegPron_Mbaeve))
                  None wo ty ip h) = false.
Proof.
  intros s v dobj wo ty ip h Hpol.
  unfold ss_neg_concord_ok. simpl. rewrite Hpol.
  destruct s as [sNP|]; simpl.
  - destruct (is_negative_np sNP); simpl.
    + reflexivity.
    + destruct dobj as [dNP|]; simpl.
      * destruct (is_negative_np dNP); reflexivity.
      * reflexivity.
  - destruct dobj as [dNP|]; simpl.
    + destruct (is_negative_np dNP); reflexivity.
    + reflexivity.
Qed.
(* ---------- SK: hikuái placement §4.1.1 ---------- *)

Theorem rule_SK1_no_hikuai_ok : forall s v dobj iobj pobj wo ty ip,
    ss_hikuai_ok
      (mkSentence s v dobj iobj pobj wo ty ip false) = true.
Proof. reflexivity. Qed.

Theorem rule_SK2_hikuai_1sg_bad : forall s v dobj iobj pobj wo ty ip,
    cv_person v = First ->
    ss_hikuai_ok
      (mkSentence s v dobj iobj pobj wo ty ip true) = false.
Proof.
  intros. unfold ss_hikuai_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_SK4_hikuai_vso_ok : forall s v dobj iobj pobj ty ip,
    cv_person v = Third ->
    ss_hikuai_ok
      (mkSentence s v dobj iobj pobj WO_VSO ty ip true) = true.
Proof.
  intros. unfold ss_hikuai_ok. simpl. rewrite H. reflexivity.
Qed.

(* ---------- SP: human =pe/=me §5.1 ---------- *)

(* Human NP with Post_Pe is fine *)
Theorem rule_SP1_human_pe_ok :
    ss_human_pe_ok
      (mkSentence None
        (mkConjVerb (VF_Regular (mkVerb Areal Oral "heka" PostpComplement
                                        VRoot_Plain C3sg_I))
                    First Singular None Indicative Positive Active nil None)
        None None
        (Some (NP_PronSubj Subj2SG, Post_Pe))
        WO_SVO ST_Declarative None false) = true.
Proof. reflexivity. Qed.

(* Human NP with wrong postposition is ill-formed *)
Theorem rule_SP2_human_wrong_pp_bad :
    ss_human_pe_ok
      (mkSentence None
        (mkConjVerb (VF_Regular (mkVerb Areal Oral "heka" PostpComplement
                                        VRoot_Plain C3sg_I))
                    First Singular None Indicative Positive Active nil None)
        None None
        (Some (NP_PronSubj Subj2SG, Post_Rehe))
        WO_SVO ST_Declarative None false) = false.
Proof. reflexivity. Qed.


(* ---------- SY: sentence type / mood ---------- *)

Theorem rule_SY1_decl_needs_indicative : forall s v dobj iobj pobj wo ip h,
    cv_mood v = Imperative ->
    ss_type_ok
      (mkSentence s v dobj iobj pobj wo ST_Declarative ip h) = false.
Proof.
  intros. unfold ss_type_ok. simpl. rewrite H. reflexivity.
Qed.

Theorem rule_SY3_yn_needs_particle : forall s v dobj iobj pobj wo h,
    cv_mood v = Indicative ->
    ss_type_ok
      (mkSentence s v dobj iobj pobj wo ST_Interrog_YN None h) = false.
Proof.
  intros. unfold ss_type_ok. simpl. rewrite H. reflexivity.
Qed.

(* ---------- Adverbial clause theorems §12.2.3 ---------- *)

Theorem rule_AC1_purposive_hagua_ok :
    wf_adv_clause (mkAdvClause AC_Purposive "haguã") = true.
Proof. reflexivity. Qed.

Theorem rule_AC2_purposive_wrong_morpheme_bad :
    wf_adv_clause (mkAdvClause AC_Purposive "ramo") = false.
Proof. reflexivity. Qed.

Theorem rule_AC3_cond_hyp_ro_ok :
    wf_adv_clause (mkAdvClause AC_Cond_Hyp "rõ") = true.
Proof. reflexivity. Qed.

Theorem rule_AC4_cond_hyp_ramo_ok :
    wf_adv_clause (mkAdvClause AC_Cond_Hyp "ramo") = true.
Proof. reflexivity. Qed.

Theorem rule_AC5_temp_simult_jave_ok :
    wf_adv_clause (mkAdvClause AC_Temp_Simult "jave") = true.
Proof. reflexivity. Qed.

Theorem rule_AC6_temp_ant_mboyve_ok :
    wf_adv_clause (mkAdvClause AC_Temp_Ant "mboyve") = true.
Proof. reflexivity. Qed.

Theorem rule_AC7_temp_post_rire_ok :
    wf_adv_clause (mkAdvClause AC_Temp_Post "rire") = true.
Proof. reflexivity. Qed.

Theorem rule_AC8_concessive_ramo_jepe_ok :
    wf_adv_clause (mkAdvClause AC_Concessive "ramo jepe") = true.
Proof. reflexivity. Qed.

Theorem rule_AC9_manner_ha_icha_ok :
    wf_adv_clause (mkAdvClause AC_Manner "ha-icha") = true.
Proof. reflexivity. Qed.

Theorem rule_AC10_manner_hague_icha_ok :
    wf_adv_clause (mkAdvClause AC_Manner "hague-icha") = true.
Proof. reflexivity. Qed.

Theorem rule_AC11_causal_gui_ok :
    wf_adv_clause (mkAdvClause AC_Causal_Gui "gui") = true.
Proof. reflexivity. Qed.

Theorem rule_AC12_causal_porque_ok :
    wf_adv_clause (mkAdvClause AC_Causal_Porque "porque") = true.
Proof. reflexivity. Qed.

(* Counterfactual: main verb needs va'erã-mo'ã *)
Theorem rule_AC13_counterfactual_needs_main_marking : forall vf p n inc vc ev,
    wf_counterfactual_main
      (mkConjVerb vf p n inc Indicative Positive vc nil ev) = false.
Proof. reflexivity. Qed.

(* ---------- Wrap-up ---------- *)

Theorem rule_NV1_equative_wf : forall a b,
    wf_np a = true -> wf_np b = true ->
    wf_nonverbal (NVS_Equative a b) = true.
Proof. intros a b Ha Hb. simpl. rewrite Ha, Hb. reflexivity. Qed.

Theorem rule_CX1_adverbial_purposive_ok : forall main subord,
    wf_sentence main = true ->
    wf_sentence subord = true ->
    wf_complex
      (CS_Adverbial main (mkAdvClause AC_Purposive "haguã") subord) = true.
Proof.
  intros main subord H1 H2. simpl. rewrite H1, H2. reflexivity.
Qed.

Theorem rule_CX2_adverbial_wrong_morpheme_bad : forall main subord,
    wf_complex
      (CS_Adverbial main (mkAdvClause AC_Purposive "ramo") subord) = false.
Proof.
  intros. simpl.
  destruct (wf_sentence main); destruct (wf_sentence subord); reflexivity.
Qed.

Theorem rule_TL1_simple_lifts : forall s,
    wf_sentence s = true ->
    wf_any_sentence (Sent_Simple s) = true.
Proof. intros. simpl. exact H. Qed.
