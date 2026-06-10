From Stdlib Require Import String Bool.
Open Scope string_scope.

Definition concat := String.append.

(* =============================== *)
(* 1) FEATURES                     *)
(* =============================== *)

Inductive orality : Type := ORAL | NASAL.

Inductive polarity : Type := POS | NEG.

Inductive verb_class : Type := Areal | Attrib.

(* 6 agreement slots you care about *)
Inductive agr_slot : Type :=
| S1SG | S2SG | S3SG | S1PL_INCL | S1PL_EXCL | S2PL.

(* =============================== *)
(* 2) PRONOUNS                     *)
(* =============================== *)

Inductive pronoun : Type :=
| Che | Nde | Hae | Ñande | Ore | Pee.

Definition slot_of_pronoun (p : pronoun) : agr_slot :=
  match p with
  | Che   => S1SG
  | Nde   => S2SG
  | Hae   => S3SG
  | Ñande => S1PL_INCL
  | Ore   => S1PL_EXCL
  | Pee   => S2PL
  end.

Definition pronoun_string (p : pronoun) : string :=
  match p with
  | Che   => "che"
  | Nde   => "nde"
  | Hae   => "ha'e"
  | Ñande => "ñande"
  | Ore   => "ore"
  | Pee   => "peẽ"
  end.

(* =============================== *)
(* 3) MORPHOLOGY TABLES            *)
(* =============================== *)

(* Agreement prefixes (Propio-style), oral vs nasal *)
Definition conj_pref (o : orality) (s : agr_slot) : string :=
  match o, s with
  | ORAL,  S1SG      => "a"
  | ORAL,  S2SG      => "re"
  | ORAL,  S3SG      => "o"
  | ORAL,  S1PL_INCL => "ja"
  | ORAL,  S1PL_EXCL => "ro"
  | ORAL,  S2PL      => "pe"
  | NASAL, S1SG      => "a"
  | NASAL, S2SG      => "re"
  | NASAL, S3SG      => "o"
  | NASAL, S1PL_INCL => "ña"
  | NASAL, S1PL_EXCL => "ro"
  | NASAL, S2PL      => "pe"
  end.

Definition neg_pref (o : orality) : string :=
  match o with
  | ORAL  => "nd"
  | NASAL => "n"
  end.