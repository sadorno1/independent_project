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

(* ============================================================ *)
(*  is_one: true if the numeral denotes peteĩ (1).             *)
(*  Used by NounPhrases.v to decide singular vs plural for      *)
(*  NP_Num.  Peteĩ is the only digit with no Mult constructor,  *)
(*  so the only path to "1" is the bare digit wrapped through   *)
(*  all four Sub- layers.                                       *)
(* ============================================================ *)

Definition is_one (n : GuaraniNum) : bool :=
  match n with
  | GN_Small (S1000Su_Small (S1000_Small (S100_Digit Peteĩ))) => true
  | _ => false
  end.

(* ============================================================ *)
(*  Theorems                                                    *)
(* ============================================================ *)

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

Theorem is_one_petei :
    is_one (GN_Small (S1000Su_Small (S1000_Small (S100_Digit Peteĩ)))) = true.
Proof. reflexivity. Qed.

Theorem is_one_mult_false : forall m,
    is_one (GN_Small (S1000Su_Small (S1000_Small (S100_MultPa m)))) = false.
Proof. intros m. reflexivity. Qed.

Theorem is_one_sua_false : is_one GN_Sua = false.
Proof. reflexivity. Qed.

Open Scope string_scope.

Definition render_digit (d : Digit) : string :=
  match d with
  | Peteĩ   => "peteĩ"
  | Mokõi   => "mokõi"
  | Mbohapy => "mbohapy"
  | Irundy  => "irundy"
  | Po      => "po"
  | Poteĩ   => "poteĩ"
  | Pokõi   => "pokõi"
  | Poapy   => "poapy"
  | Porundy => "porundy"
  end.

Definition render_mult (m : Mult) : string :=
  render_digit (mult_to_digit m).

Definition render_teen (t : Teen) : string :=
  match t with
  | Pateĩ    => "pateĩ"
  | Pakõi    => "pakõi"
  | Pa'apy   => "pa'apy"
  | Parundy  => "parundy"
  | Papo     => "papo"
  | Papoteĩ  => "papoteĩ"
  | Papokõi  => "papokõi"
  | Papoapy  => "papoapy"
  | Paporundy => "paporundy"
  end.

Definition render_sub100 (s : Sub100) : string :=
  match s with
  | S100_Digit d         => render_digit d
  | S100_Pa              => "pa"
  | S100_Teen t          => render_teen t
  | S100_MultPa m        => render_mult m ++ "pa"
  | S100_MultPaDigit m d => render_mult m ++ "pa " ++ render_digit d
  end.

Definition render_sub1000 (s : Sub1000) : string :=
  match s with
  | S1000_Small s        => render_sub100 s
  | S1000_Sa             => "sa"
  | S1000_SaTail s       => "sa " ++ render_sub100 s
  | S1000_MultSa m       => render_mult m ++ "sa"
  | S1000_MultSaTail m s => render_mult m ++ "sa " ++ render_sub100 s
  end.

Definition render_sub1000su (s : Sub1000Su) : string :=
  match s with
  | S1000Su_Small s        => render_sub1000 s
  | S1000Su_Su             => "su"
  | S1000Su_SuTail s       => "su " ++ render_sub1000 s
  | S1000Su_MultSu m       => render_sub1000 m ++ "su"
  | S1000Su_MultSuTail m s => render_sub1000 m ++ "su " ++ render_sub1000 s
  end.

Definition render_num (n : GuaraniNum) : string :=
  match n with
  | GN_Small s        => render_sub1000su s
  | GN_Sua            => "sua"
  | GN_SuaTail s      => "sua " ++ render_sub1000su s
  | GN_MultSua m      => render_sub1000su m ++ "sua"
  | GN_MultSuaTail m s => render_sub1000su m ++ "sua " ++ render_sub1000su s
  end.

  