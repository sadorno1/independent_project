# check.py
import sys
from guarani.analyzer import load_lexicon, analyze
from guarani.loop import tokenize, build_sentence
from guarani.verifier import Verifier

load_lexicon("enriched.csv")
verifier = Verifier(coq_lib_dir="./coq")

sentence_str = " ".join(sys.argv[1:])
tokens = tokenize(sentence_str)
sentence_ast = build_sentence(tokens)

if sentence_ast is None:
    print(" Could not parse a verb in the sentence.")
    sys.exit(1)

result = verifier.verify(sentence_ast)
if result.wf:
    print("✓ Grammatically correct.")
else:
    print(f"✗ Error: {result.feedback}")