(* GuaraniSystem.v
   This is the "usable system" layer:
   - typing judgments that consult the auto-generated lexicon (lookup + tags)
   - morphology helpers on top of Core tables
   - agreement-aware grammar rules over token lists

   Imports:
   - GuaraniCore: features + tables (conj_pref, neg_pref, pronouns)
   - GuaraniLexiconTypes: lex_entry schema + pos + has_pos
   - LexiconGenerated: the actual dictionary + lookup
*)

From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import GuaraniCore.
Require Import GuaraniLexiconTypes.
Require Import LexiconGenerated.

(* =============================== *)
(* 1) Typed-token judgments        *)
(* =============================== *)

(* Generic typing judgment:
   token s has POS tag p according to the generated lexicon. *)
Inductive HasPOSTok : pos -> string -> Prop :=
| has_pos_tok :
    forall p s e,
      lookup s = Some e ->
      has_pos p (e_pos e) = true ->
      HasPOSTok p s.

Definition PronounTok : string -> Prop := HasPOSTok POS_PRON.
Definition NounTok : string -> Prop := HasPOSTok POS_NOUN.
Definition ArealVerbTok : string -> Prop := HasPOSTok POS_VERB_AREAL.
Definition AttribVerbTok : string -> Prop := HasPOSTok POS_VERB_ATTR.
Definition ConjTok : string -> Prop := HasPOSTok POS_CONJ.

(* Optional convenience: token exists in dict *)
Definition InLexicon (s : string) : Prop :=
  exists e, lookup s = Some e.

(* =============================== *)
(* 2) Minimal morphology layer     *)
(* =============================== *)

(* Render agreement prefix + root *)
Definition render_conj (o : orality) (slot : agr_slot) (root : string) : string :=
  conj_pref o slot ++ root.

(* Super-minimal negation: neg_pref + base *)
Definition render_neg (o : orality) (base : string) : string :=
  neg_pref o ++ base.

(* Pull orality from lexicon entry *)
Definition token_orality (s : string) : option orality :=
  match lookup s with
  | None => None
  | Some e => Some (e_orality e)
  end.

(* =============================== *)
(* 3) Agreement-aware forms        *)
(* =============================== *)

(* Pronouns are generated directly from the core pronoun inventory. *)
Inductive PronounForm : agr_slot -> string -> Prop :=
| pron_form :
    forall p,
      PronounForm (slot_of_pronoun p) (pronoun_string p).

(* Areal verb SURFACE forms are generated from lexical roots.
   So if root "mano" is in the lexicon as an areal verb and is ORAL,
   then slot S2SG generates "remano". *)
Inductive ArealVerbForm : agr_slot -> string -> Prop :=
| mk_areal_form :
    forall slot root e,
      lookup root = Some e ->
      has_pos POS_VERB_AREAL (e_pos e) = true ->
      ArealVerbForm slot (render_conj (e_orality e) slot root).

(* =============================== *)
(* 4) Grammar rules                *)
(* =============================== *)

(* Start tiny:
   - Sentence can be [pronoun; arealVerbForm] with matching agreement slot
   - Sentence can be [noun; attribVerb] as before
   - bare areal verb forms are still allowed
   - bare attributive verbs are still allowed
*)

Inductive Sentence : list string -> Prop :=
| S_Pron_Areal :
    forall slot p v,
      PronounForm slot p ->
      ArealVerbForm slot v ->
      Sentence [p; v]
| S_Noun_Attrib :
    forall n v,
      NounTok n ->
      AttribVerbTok v ->
      Sentence [n; v]
| S_Areal_Only :
    forall slot v,
      ArealVerbForm slot v ->
      Sentence [v]
| S_Attrib_Only :
    forall v,
      AttribVerbTok v ->
      Sentence [v].

(* =============================== *)cha
(* 5) Tiny helper lemmas           *)
(* =============================== *)

Lemma PronounTok_in_lexicon :
  forall s, PronounTok s -> InLexicon s.
Proof.
  intros s H.
  unfold PronounTok in H.
  inversion H as [p s' e Hlk Hpos]; subst.
  exists e. exact Hlk.
Qed.

Lemma NounTok_in_lexicon :
  forall s, NounTok s -> InLexicon s.
Proof.
  intros s H.
  unfold NounTok in H.
  inversion H as [p s' e Hlk Hpos]; subst.
  exists e. exact Hlk.
Qed.

Lemma ArealVerbTok_in_lexicon :
  forall s, ArealVerbTok s -> InLexicon s.
Proof.
  intros s H.
  unfold ArealVerbTok in H.
  inversion H as [p s' e Hlk Hpos]; subst.
  exists e. exact Hlk.
Qed.

Lemma AttribVerbTok_in_lexicon :
  forall s, AttribVerbTok s -> InLexicon s.
Proof.
  intros s H.
  unfold AttribVerbTok in H.
  inversion H as [p s' e Hlk Hpos]; subst.
  exists e. exact Hlk.
Qed.

Lemma HasPOS_in_lexicon :
  forall p s, HasPOSTok p s -> InLexicon s.
Proof.
  intros p s H.
  inversion H as [p' s' e Hlk Hpos]; subst.
  exists e. exact Hlk.
Qed.

(* New helper: every generated areal verb form comes from a lexical root *)
Lemma ArealVerbForm_has_root :
  forall slot surf,
    ArealVerbForm slot surf ->
    exists root e,
      lookup root = Some e /\
      has_pos POS_VERB_AREAL (e_pos e) = true /\
      surf = render_conj (e_orality e) slot root.
Proof.
  intros slot surf H.
  inversion H as [slot' root e Hlk Hpos]; subst.
  exists root, e.
  repeat split; assumption.
Qed.

(* Every generated areal verb form is backed by some lexical entry,
   even if the SURFACE form itself is not literally in the lexicon. *)
Lemma ArealVerbForm_has_lexical_source :
  forall slot surf,
    ArealVerbForm slot surf ->
    exists root, InLexicon root.
Proof.
  intros slot surf H.
  inversion H as [slot' root e Hlk Hpos]; subst.
  exists root.
  unfold InLexicon.
  exists e.
  exact Hlk.
Qed.

(* Core pronoun forms are always pronoun tokens in the lexicon,
   provided your lexicon contains the same pronoun strings tagged as POS_PRON. *)
