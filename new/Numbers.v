From Stdlib Require Import String.

(* ============================================================ *)
(*  Numbers.v                                                   *)
(*  Guaraní numeral grammar types and theorems.                 *)
(* ============================================================ *)

Inductive Digit : Type :=
  | Peteĩ | Mokõi | Mbohapy | Irundy | Po
  | Poteĩ | Pokõi | Poapy   | Porundy.

Inductive Mult : Type :=
  | MokõiM | MbohapyM | IrundyM | PoM
  | PoteĩM | PokõiM   | PoapyM  | PorundyM.

Definition mult_to_digit (m : Mult) : Digit :=
  match m with
  | MokõiM   => Mokõi   | MbohapyM => Mbohapy
  | IrundyM  => Irundy  | PoM      => Po
  | PoteĩM   => Poteĩ   | PokõiM   => Pokõi
  | PoapyM   => Poapy   | PorundyM => Porundy
  end.

Inductive Teen : Type :=
  | Pateĩ    | Pakõi   | Pa'apy  | Parundy | Papo
  | Papoteĩ  | Papokõi | Papoapy | Paporundy.

Inductive Sub100 : Type :=
  | S100_Digit       (d : Digit)
  | S100_Pa
  | S100_Teen        (t : Teen)
  | S100_MultPa      (m : Mult)
  | S100_MultPaDigit (m : Mult) (d : Digit).

Inductive Sub1000 : Type :=
  | S1000_Small      (s : Sub100)
  | S1000_Sa
  | S1000_SaTail     (s : Sub100)
  | S1000_MultSa     (m : Mult)
  | S1000_MultSaTail (m : Mult) (s : Sub100).

Inductive Sub1000Su : Type :=
  | S1000Su_Small      (s : Sub1000)
  | S1000Su_Su
  | S1000Su_SuTail     (s : Sub1000)
  | S1000Su_MultSu     (m : Sub1000)
  | S1000Su_MultSuTail (m : Sub1000) (s : Sub1000).

Inductive GuaraniNum : Type :=
  | GN_Small       (s : Sub1000Su)
  | GN_Sua
  | GN_SuaTail     (s : Sub1000Su)
  | GN_MultSua     (m : Sub1000Su)
  | GN_MultSuaTail (m : Sub1000Su) (s : Sub1000Su).

(* ------------------------------------------------------------ *)
(*  is_one: true iff the numeral denotes peteĩ (1).             *)
(*  Used by NounPhrases.v to decide singular vs plural for      *)
(*  NP_Num.  Peteĩ is the only digit with no Mult constructor,  *)
(*  so the only path to "1" is the bare digit wrapped through   *)
(*  all four Sub- layers.                                       *)
(* ------------------------------------------------------------ *)

Definition is_one (n : GuaraniNum) : bool :=
  match n with
  | GN_Small (S1000Su_Small (S1000_Small (S100_Digit Peteĩ))) => true
  | _ => false
  end.

(* ------------------------------------------------------------ *)
(*  Theorems                                                    *)
(* ------------------------------------------------------------ *)

Theorem peteĩ_not_mult : forall m : Mult,
    mult_to_digit m <> Peteĩ.
Proof.
  intro m; destruct m; simpl; discriminate.
Qed.

Theorem mult_to_digit_inj : forall m1 m2,
    mult_to_digit m1 = mult_to_digit m2 -> m1 = m2.
Proof.
  intros m1 m2; destruct m1; destruct m2; simpl; intro H;
    try reflexivity; discriminate.
Qed.

Theorem sa_ne_satail   : forall s, S1000_Sa   <> S1000_SaTail s.
Proof. intros s H; discriminate. Qed.

Theorem su_ne_sutail   : forall s, S1000Su_Su <> S1000Su_SuTail s.
Proof. intros s H; discriminate. Qed.

Theorem sua_ne_suatail : forall s, GN_Sua     <> GN_SuaTail s.
Proof. intros s H; discriminate. Qed.

(* is_one is true exactly for the peteĩ term *)
Theorem is_one_petei :
    is_one (GN_Small (S1000Su_Small (S1000_Small (S100_Digit Peteĩ)))) = true.
Proof. reflexivity. Qed.

(* No multiplier numeral is one *)
Theorem is_one_mult_false : forall m,
    is_one (GN_Small (S1000Su_Small (S1000_Small (S100_MultPa m)))) = false.
Proof. intros m. reflexivity. Qed.

(* Power words are not one *)
Theorem is_one_sua_false : is_one GN_Sua = false.
Proof. reflexivity. Qed.

(* ------------------------------------------------------------ *)
(*  Examples                                                    *)
(* ------------------------------------------------------------ *)

Example ex_mokoipa          : Sub100    := S100_MultPa MokõiM.
Example ex_mokoipa_petei    : Sub100    := S100_MultPaDigit MokõiM Peteĩ.
Example ex_sa_popa          : Sub1000   := S1000_SaTail (S100_MultPa PoM).
Example ex_mokisa           : Sub1000   := S1000_MultSa MokõiM.
Example ex_mokisa_popa      : Sub1000   := S1000_MultSaTail MokõiM (S100_MultPa PoM).
Example ex_pa_su            : Sub1000Su := S1000Su_MultSu (S1000_Small S100_Pa).
Example ex_patei_su         : Sub1000Su := S1000Su_MultSu (S1000_Small (S100_Teen Pateĩ)).
Example ex_sa_su            : Sub1000Su := S1000Su_MultSu S1000_Sa.
Example ex_mokisa_su        : Sub1000Su := S1000Su_MultSu (S1000_MultSa MokõiM).
Example ex_mokisa_popa_su   : Sub1000Su := S1000Su_MultSu (S1000_MultSaTail MokõiM (S100_MultPa PoM)).
Example ex_su_sa_popa       : Sub1000Su := S1000Su_SuTail (S1000_SaTail (S100_MultPa PoM)).
Example ex_su_sua           : GuaraniNum := GN_MultSua S1000Su_Su.
Example ex_sa_su_sua        : GuaraniNum := GN_MultSua (S1000Su_MultSu S1000_Sa).
Example ex_porundysua       : GuaraniNum := GN_MultSua (S1000Su_Small (S1000_Small (S100_Digit Porundy))).

Fail Example wrong_peteisa : Sub1000 :=
  S1000_MultSa PeteĩM.