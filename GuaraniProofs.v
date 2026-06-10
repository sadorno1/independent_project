(* GuaraniProofs.v
   Big-picture theorems about the system.
   Keep this file for proofs only (no new core definitions unless truly needed).

   Imports:
   - GuaraniSystem already pulls Core + LexiconTypes + LexiconGenerated.
*)

From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import GuaraniSystem.
Require Import GuaraniLexiconTypes.
Require Import LexiconGenerated.

(* ========================================================= *)
(* 1) Generic list helpers (tiny + reusable)                  *)
(* ========================================================= *)

Fixpoint All {A : Type} (P : A -> Prop) (xs : list A) : Prop :=
  match xs with
  | [] => True
  | x :: rest => P x /\ All P rest
  end.

Lemma All_app :
  forall (A : Type) (P : A -> Prop) (xs ys : list A),
    All P xs ->
    All P ys ->
    All P (xs ++ ys).
Proof.
  intros A P xs.
  induction xs as [|x rest IH]; intros ys Hx Hy.
  - simpl. exact Hy.
  - simpl in *. destruct Hx as [HPx HPrest].
    split.
    + exact HPx.
    + apply IH; assumption.
Qed.

(* ========================================================= *)
(* 2) Every token in a Sentence is in the lexicon             *)
(* ========================================================= *)

(* For our current grammar, Sentence is only 1 or 2 tokens long,
   so we can prove this cleanly by cases. *)
  (* Theorem Sentence_all_tokens_in_lexicon :
  forall xs,
  Sentence xs ->
  All InLexicon xs.
  Proof.
  intros xs Hs.
  destruct Hs as [p v Hp Hv | n v Hn Hv | v Hv | v Hv]; simpl.
  - split.
  + apply (PronounTok_in_lexicon p). exact Hp.
  + split.
    * apply (ArealVerbTok_in_lexicon v). exact Hv.
    * exact I.
  - split.
  + apply (NounTok_in_lexicon n). exact Hn.
  + split.
    * apply (AttribVerbTok_in_lexicon v). exact Hv.
    * exact I.
  - split.
  + apply (ArealVerbTok_in_lexicon v). exact Hv.
  + exact I.
  - split.
  + apply (AttribVerbTok_in_lexicon v). exact Hv.
  + exact I.
  Qed. *)

(* ========================================================= *)
(* 3) If a token is typed, it exists in lookup (unpacks Prop) *)
(* ========================================================= *)

Lemma PronounTok_lookup :
  forall s,
    PronounTok s ->
    exists e, lookup s = Some e.
Proof.
  intros s H.
  unfold PronounTok in H.
  inversion H as [p s' e Hlk Htag]; subst.
  exists e. exact Hlk.
Qed.

Lemma NounTok_lookup :
  forall s,
    NounTok s ->
    exists e, lookup s = Some e.
Proof.
  intros s H.
  unfold NounTok in H.
  inversion H as [p s' e Hlk Htag]; subst.
  exists e. exact Hlk.
Qed.

Lemma ArealVerbTok_lookup :
  forall s,
    ArealVerbTok s ->
    exists e, lookup s = Some e.
Proof.
  intros s H.
  unfold ArealVerbTok in H.
  inversion H as [p s' e Hlk Htag]; subst.
  exists e. exact Hlk.
Qed.

Lemma AttribVerbTok_lookup :
  forall s,
    AttribVerbTok s ->
    exists e, lookup s = Some e.
Proof.
  intros s H.
  unfold AttribVerbTok in H.
  inversion H as [p s' e Hlk Htag]; subst.
  exists e. exact Hlk.
Qed.

(* ========================================================= *)
(* 4) Determinism / uniqueness style lemma (very common)      *)
(* ========================================================= *)

(* If lookup returns Some e1 and Some e2 for the same string,
   then e1 = e2. This is true because lookup is a function. *)
Lemma lookup_deterministic :
  forall s e1 e2,
    lookup s = Some e1 ->
    lookup s = Some e2 ->
    e1 = e2.
Proof.
  intros s e1 e2 H1 H2.
  rewrite H1 in H2.
  inversion H2.
  reflexivity.
Qed.

(* ========================================================= *)
(* 5) Example: show how to prove a concrete sentence          *)
(* ========================================================= *)
(* You normally do NOT prove each sentence. This is just a demo
   to show the mechanics once. *)

(*
Example ex_sentence_demo :
  Sentence ["che"; "amano"].
Proof.
  apply S_Pron_Areal.
  - (* PronounTok "che" *)
    (* This depends on your LexiconGenerated.lookup and tags.
       If your CSV tagged "che" as POS_PRON, this will be provable. *)
    eapply has_pos_tok.
    + (* lookup "che" = Some e *) admit.
    + (* has_pos POS_PRON (e_pos e) = true *) admit.
  - (* ArealVerbTok "amano" *) admit.
Qed.
*)
Example nde_is_pronoun_form :
  PronounForm S2SG "nde".
Proof.
  change (PronounForm (slot_of_pronoun Nde) (pronoun_string Nde)).
  apply pron_form.
Qed.

Example remano_is_s2sg_areal :
  ArealVerbForm S2SG "remano".
Proof.
  eapply mk_areal_form with (root := "mano") (e := w_mano).
  - vm_compute. reflexivity.
  - vm_compute. reflexivity.
Qed.

Example ex_nde_remano :
  Sentence ["nde"; "amano"].
Proof.
  apply S_Pron_Areal with (slot := S2SG).
  - change (PronounForm (slot_of_pronoun Nde) (pronoun_string Nde)).
    apply pron_form.
  - eapply mk_areal_form with (root := "mano") (e := w_mano).
    + vm_compute. reflexivity.
    + vm_compute. reflexivity.
Qed.
(* You can keep demos commented out until your CSV tag mapping
   guarantees "che" is POS_PRON and "amano" is POS_VERB_AREAL. *)
