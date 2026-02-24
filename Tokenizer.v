From Stdlib Require Import String List Ascii.
Import ListNotations.
Open Scope string_scope.

(* Split on ASCII space only (Milestone 3). *)

Fixpoint skip_spaces (s:string) : string :=
  match s with
  | EmptyString => EmptyString
  | String c rest =>
      if Ascii.eqb c " "%char then skip_spaces rest else s
  end.

Fixpoint take_until_space (s:string) : (string * string) :=
  match s with
  | EmptyString => ("", "")
  | String c rest =>
      if Ascii.eqb c " "%char then ("", rest)
      else
        let '(tok, rem) := take_until_space rest in
        (String c tok, rem)
  end.

Fixpoint tokenize_aux (s:string) (fuel:nat) : list string :=
  match fuel with
  | O => []
  | S fuel' =>
      let s1 := skip_spaces s in
      match s1 with
      | EmptyString => []
      | _ =>
          let '(tok, rem) := take_until_space s1 in
          tok :: tokenize_aux rem fuel'
      end
  end.

Definition tokenize (s:string) : list string :=
  tokenize_aux s 200.
