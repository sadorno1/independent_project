From Stdlib Require Import String List Bool.
Import ListNotations.
Open Scope string_scope.

Require Import GuaraniCore.
Import GuaraniCore.

Require Import LexiconGenerated.
Require Import Tokenizer.

(* ===================== *)
(* Helpers *)
Definition eqb_str (a b : string) : bool :=
  if String.string_dec a b then true else false.

Fixpoint find_map {A B:Type} (f:A -> option B) (xs:list A) : option B :=
  match xs with
  | [] => None
  | x::rest => match f x with
               | Some y => Some y
               | None => find_map f rest
               end
  end.

Fixpoint map_option {A B:Type} (f:A -> option B) (xs:list A) : option (list B) :=
  match xs with
  | [] => Some []
  | x::rest =>
      match f x, map_option f rest with
      | Some y, Some ys => Some (y::ys)
      | _, _ => None
      end
  end.

(* ===================== *)
(* Word categories (Milestone 3) *)
Inductive word : Type :=
| WSubj (p:person) (n:number)
| WObjPre (requiresP1:bool)     (* only ro/po *)
| WObjPost                      (* only chupe/ichupe *)
| WVerb (p:person) (n:number) (r:vroot).

(* ===================== *)
(* Verb surface matcher (POS/NEG via pol) *)
Definition lex_verbs : list vroot := lex_verbs_generated.

Definition all_pn : list (person * number) :=
  [ (P1, SG); (P2, SG); (P3, SG)
  ; (P1, PL_INCL); (P1, PL_EXCL); (P2, PL_2); (P3, PL_3)
  ].

Definition maybe_negate (pol:polarity) (o:orality) (p:person) (n:number) (base:string) : string :=
  match pol with
  | POS => base
  | NEG => GuaraniCore.negate o p n base
  end.

Definition check_surface_with_pol
  (pol:polarity) (p:person) (n:number) (r:vroot) (surface:string) : bool :=
  match conjugate p n r with
  | None => false
  | Some base =>
      eqb_str (maybe_negate pol r.(r_orality) p n base) surface
  end.

Definition try_match_one_root (pol:polarity) (surface:string) (r:vroot)
  : option (person * number * vroot) :=
  find_map
    (fun pn =>
       let '(p,n) := pn in
       if check_surface_with_pol pol p n r surface then Some (p,n,r) else None)
    all_pn.

Definition analyze_verb_surface (pol:polarity) (surface:string)
  : option (person * number * vroot) :=
  find_map (fun r => try_match_one_root pol surface r) lex_verbs.

(* ===================== *)
(* One classifier: no find_pronoun, no find_obj_pron *)
Definition classify (pol:polarity) (s:string) : option word :=
  (* subjects *)
  if eqb_str s "che" then Some (WSubj P1 SG) else
  if eqb_str s "nde" then Some (WSubj P2 SG) else
  if eqb_str s "ha'e" then Some (WSubj P3 SG) else
  if eqb_str s "ñande" then Some (WSubj P1 PL_INCL) else
  if eqb_str s "ore" then Some (WSubj P1 PL_EXCL) else
  if eqb_str s "peẽ" then Some (WSubj P2 PL_2) else
  if eqb_str s "ha'ekuéra" then Some (WSubj P3 PL_3) else

  (* objects (Option A) *)
  if eqb_str s "ro" then Some (WObjPre true) else
  if eqb_str s "po" then Some (WObjPre true) else
  if eqb_str s "chupe" then Some WObjPost else
  if eqb_str s "ichupe" then Some WObjPost else

  (* verbs *)
  match analyze_verb_surface pol s with
  | Some (p,n,r) => Some (WVerb p n r)
  | None => None
  end.

(* ===================== *)
(* Agreement + constraints *)
Definition agrees (sp:person) (sn:number) (vp:person) (vn:number) : bool :=
  match sp,sn,vp,vn with
  | P1, SG,      P1, SG      => true
  | P2, SG,      P2, SG      => true
  | P3, SG,      P3, SG      => true
  | P1, PL_INCL, P1, PL_INCL => true
  | P1, PL_EXCL, P1, PL_EXCL => true
  | P2, PL_2,    P2, PL_2    => true
  | P3, PL_3,    P3, PL_3    => true
  | _,_,_,_ => false
  end.

Definition isP1 (p:person) : bool := match p with P1 => true | _ => false end.

Record parse := { per:person; num:number; root:vroot; pol:polarity }.

Definition check_words (pol:polarity) (ws:list word) : option parse :=
  match ws with
  | [WVerb p n r] =>
      Some {| per := p; num := n; root := r; pol := pol |}

  | [WSubj sp sn; WVerb vp vn r] =>
      if agrees sp sn vp vn then Some {| per:=vp; num:=vn; root:=r; pol:=pol |} else None

  | [WSubj sp sn; WObjPre req; WVerb vp vn r] =>
      if agrees sp sn vp vn
      then if req then if isP1 vp then Some {| per:=vp; num:=vn; root:=r; pol:=pol |} else None
           else Some {| per:=vp; num:=vn; root:=r; pol:=pol |}
      else None

  | [WSubj sp sn; WVerb vp vn r; WObjPost] =>
      if agrees sp sn vp vn then Some {| per:=vp; num:=vn; root:=r; pol:=pol |} else None

  | _ => None
  end.

Definition check_sentence (pol:polarity) (s:string) : option parse :=
  match map_option (classify pol) (tokenize s) with
  | None => None
  | Some ws => check_words pol ws
  end.

(* ===================== *)
(* Tiny proofs that don't depend on verb lexicon *)
Example test_classify_subj_che :
  classify POS "che" = Some (WSubj P1 SG).
Proof. simpl. reflexivity. Qed.

Example test_classify_obj_ro :
  classify POS "ro" = Some (WObjPre true).
Proof. simpl. reflexivity. Qed.

Example test_classify_obj_chupe :
  classify POS "chupe" = Some WObjPost.
Proof. simpl. reflexivity. Qed.