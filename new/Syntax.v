From Stdlib Require Import String.
Open Scope string_scope.

(*  Primitives.v -- shared grammatical and phonological types   *)

(* --- Phonology --- *)

(* Drives all prefix/suffix allomorphy in Guaraní *)
Inductive orality : Type :=
  | Oral
  | Nasal.

(* Final vowel class: determines nominal plural suffix *)
Inductive word_ending : Type :=
  | EndAEO  (* final a/e/o -> -ita *)
  | EndIUY. (* final i/u/y -> -eta *)

(* --- Grammar --- *)

Inductive person : Type :=
  | First
  | Second
  | Third.

Inductive number : Type :=
  | Singular
  | Plural.

(* ñande (incl.) vs ore (excl.) *)
Inductive inclusivity : Type :=
  | Inclusive
  | Exclusive.

(* --- Possessive markers --- *)
(* Used in NPs (che juru) and later in attributive verb conjugation *)

Inductive poss_marker : Type :=
  | Poss1       (* che            *)
  | Poss2       (* nde / ne       *)
  | Poss3       (* i / iñ         *)
  | Poss1Incl   (* ñánde / ñáne   *)
  | Poss1Excl   (* ore            *)
  | Poss2Pl     (* pénde / péne   *)
  | Poss3Pl.    (* i / iñ         *)

(* Oral/nasal allomorphs for possessive markers *)
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

(* --- Allomorphy functions --- *)

(* Adjectival plural: karai kuéra, mitãnguéra *)
Definition plural_suffix_adj (o : orality) : string :=
  match o with
  | Oral  => "kuéra"
  | Nasal => "nguéra"
  end.

(* Nominal plural: ogaita, ñatĩ'ueta *)
Definition plural_suffix_noun (e : word_ending) : string :=
  match e with
  | EndAEO => "ita"
  | EndIUY => "eta"
  end.

(* Superlative: tuichaite / tuichaete *)
Definition super_suffix (o : orality) : string :=
  match o with
  | Oral  => "ite"
  | Nasal => "ete"
  end.

(* Negative prefix: nd (oral) / n (nasal) *)
Definition neg_prefix (o : orality) : string :=
  match o with
  | Oral  => "nd"
  | Nasal => "n"
  end.

(* Passive voice: je (oral) / ñe (nasal) *)
Definition passive_prefix (o : orality) : string :=
  match o with
  | Oral  => "je"
  | Nasal => "ñe"
  end.

(* Reciprocal voice: jo (oral) / ño (nasal) *)
Definition reciprocal_prefix (o : orality) : string :=
  match o with
  | Oral  => "jo"
  | Nasal => "ño"
  end.

(* Coactive voice: mbo (oral) / mo (nasal) *)
Definition coactive_prefix (o : orality) : string :=
  match o with
  | Oral  => "mbo"
  | Nasal => "mo"
  end.

(* Totalitative suffix: pa (oral) / mba (nasal) *)
Definition totalitative_suffix (o : orality) : string :=
  match o with
  | Oral  => "pa"
  | Nasal => "mba"
  end.

(* --- Decidable equality --- *)

Scheme Equality for orality.
Scheme Equality for word_ending.
Scheme Equality for person.
Scheme Equality for number.
Scheme Equality for inclusivity.
Scheme Equality for poss_marker.

(* --- Theorems --- *)

(* oral and nasal adjectival plural are distinct strings *)
Theorem plural_adj_distinct :
    plural_suffix_adj Oral <> plural_suffix_adj Nasal.
Proof. simpl. discriminate. Qed.

(* -ita and -eta are distinct strings *)
Theorem plural_noun_distinct :
    plural_suffix_noun EndAEO <> plural_suffix_noun EndIUY.
Proof. simpl. discriminate. Qed.

(* every orality gives one of the two adjectival plural forms *)
Theorem plural_adj_total : forall o,
    plural_suffix_adj o = "kuéra" \/ plural_suffix_adj o = "nguéra".
Proof. intros o; destruct o; [left|right]; reflexivity. Qed.

(* every word ending gives one of the two nominal plural forms *)
Theorem plural_noun_total : forall e,
    plural_suffix_noun e = "ita" \/ plural_suffix_noun e = "eta".
Proof. intros e; destruct e; [left|right]; reflexivity. Qed.

(* nd and n are distinct *)
Theorem neg_prefix_distinct :
    neg_prefix Oral <> neg_prefix Nasal.
Proof. simpl. discriminate. Qed.

(* Poss1 (che) and Poss1Excl (ore) are invariant across orality *)
Theorem poss1_always_che : forall o,
    poss_marker_form o Poss1 = "che".
Proof. intros o; destruct o; reflexivity. Qed.

Theorem poss1excl_always_ore : forall o,
    poss_marker_form o Poss1Excl = "ore".
Proof. intros o; destruct o; reflexivity. Qed.

(* Poss2 oral/nasal forms are distinct *)
Theorem poss2_forms_distinct :
    poss_marker_form Oral Poss2 <> poss_marker_form Nasal Poss2.
Proof. simpl. discriminate. Qed.