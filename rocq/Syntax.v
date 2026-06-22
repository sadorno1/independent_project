From Stdlib Require Import String.
Open Scope string_scope.

(* Primitives.v: shared phonological/grammatical atoms; no internal deps. *)


(* ============================================================ *)
(*  1. Phonology                                                *)
(*  §1.2 "Orality drives all allomorphy."                       *)
(* ============================================================ *)

Inductive orality : Type :=
  | Oral
  | Nasal.

(* §3.1.1: final vowel class selects =eta/=ita multitude *)
Inductive word_ending : Type :=
  | EndAEO     (* final a/e/o -> -ita *)
  | EndIUY.    (* final i/u/y -> -eta *)

(* ============================================================ *)
(*  2. Person, number, inclusivity                              *)
(*  §3.5.1 person system; §4.1.1 inclusivity                    *)
(* ============================================================ *)

Inductive person : Type :=
  | First
  | Second
  | Third.

Inductive number : Type :=
  | Singular
  | Plural.

(* §4.1.1: ñande (incl.) vs ore (excl.) *)
Inductive inclusivity : Type :=
  | Inclusive
  | Exclusive.

(* ============================================================ *)
(*  3. Possessive markers                                       *)
(*  §3.6 "che juru" = my mouth                                  *)
(* ============================================================ *)

Inductive poss_marker : Type :=
  | Poss1       (* che              *)
  | Poss2       (* nde / ne         *)
  | Poss3       (* i / iñ           *)
  | Poss1Incl   (* ñánde / ñáne     *)
  | Poss1Excl   (* ore              *)
  | Poss2Pl     (* pénde / péne     *)
  | Poss3Pl.    (* i / iñ           *)

(* §1.2 oral / nasal allomorphs of possessive markers *)
Definition poss_marker_form (o : orality) (pm : poss_marker) : string :=
  match pm with
  | Poss1     => "che"
  | Poss2     => match o with Oral => "nde"   | Nasal => "ne"   end
  | Poss3     => match o with Oral => "i"     | Nasal => "iñ"   end
  | Poss1Incl => match o with Oral => "ñánde" | Nasal => "ñáne" end
  | Poss1Excl => "ore"
  | Poss2Pl   => match o with Oral => "pénde" | Nasal => "péne" end
  | Poss3Pl   => match o with Oral => "i"     | Nasal => "iñ"   end
  end.

(* ============================================================ *)
(*  4. Allomorphy functions                                     *)
(*  Each one used by either NounPhrases.v or Verb.v (often      *)
(*  both), so they live here in the shared module.              *)
(* ============================================================ *)

(* §3.1.1: adjectival plural — karai kuéra, mitãnguéra *)
Definition plural_suffix_adj (o : orality) : string :=
  match o with
  | Oral  => "kuéra"
  | Nasal => "nguéra"
  end.

(* §3.1.1: nominal plural — ogaita, ñatĩ'ueta *)
Definition plural_suffix_noun (e : word_ending) : string :=
  match e with
  | EndAEO => "ita"
  | EndIUY => "eta"
  end.

(* §2.2.1.d: superlative — tuichaite / tuichaete *)
Definition super_suffix (o : orality) : string :=
  match o with
  | Oral  => "ite"
  | Nasal => "ete"
  end.

(* §4.9: negative circumfix prefix — nd-/n- *)
Definition neg_prefix (o : orality) : string :=
  match o with
  | Oral  => "nd"
  | Nasal => "n"
  end.

(* §6: voice prefixes *)
Definition passive_prefix (o : orality) : string :=
  match o with
  | Oral  => "je"
  | Nasal => "ñe"
  end.

Definition reciprocal_prefix (o : orality) : string :=
  match o with
  | Oral  => "jo"
  | Nasal => "ño"
  end.

Definition coactive_prefix (o : orality) : string :=
  match o with
  | Oral  => "mbo"
  | Nasal => "mo"
  end.

(* §4.10.1: totalitative suffix — pa / mba *)
Definition totalitative_suffix (o : orality) : string :=
  match o with
  | Oral  => "pa"
  | Nasal => "mba"
  end.

(* ============================================================ *)
(*  5. Theorems                                                 *)
(* ============================================================ *)

Theorem plural_adj_distinct :
    plural_suffix_adj Oral <> plural_suffix_adj Nasal.
Proof. simpl. discriminate. Qed.

Theorem plural_noun_distinct :
    plural_suffix_noun EndAEO <> plural_suffix_noun EndIUY.
Proof. simpl. discriminate. Qed.

Theorem plural_adj_total : forall o,
    plural_suffix_adj o = "kuéra" \/ plural_suffix_adj o = "nguéra".
Proof. intros o; destruct o; [left|right]; reflexivity. Qed.

Theorem plural_noun_total : forall e,
    plural_suffix_noun e = "ita" \/ plural_suffix_noun e = "eta".
Proof. intros e; destruct e; [left|right]; reflexivity. Qed.

Theorem neg_prefix_distinct :
    neg_prefix Oral <> neg_prefix Nasal.
Proof. simpl. discriminate. Qed.

Theorem poss1_always_che : forall o,
    poss_marker_form o Poss1 = "che".
Proof. intros o; destruct o; reflexivity. Qed.

Theorem poss1excl_always_ore : forall o,
    poss_marker_form o Poss1Excl = "ore".
Proof. intros o; destruct o; reflexivity. Qed.

Theorem poss2_forms_distinct :
    poss_marker_form Oral Poss2 <> poss_marker_form Nasal Poss2.
Proof. simpl. discriminate. Qed.