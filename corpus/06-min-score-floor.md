# Minimum Score Floor

Retrieval always returns a ranked list, but a top result is not necessarily a good one. If the corpus contains nothing relevant to a question, the highest-ranked chunk is still only the least-bad match, and feeding it to the model invites a confident but wrong answer. The minimum score floor exists to prevent that.

After cosine similarity is computed, every retrieved chunk whose similarity falls below a threshold is dropped. The default threshold is `0.45`. Only chunks that clear this floor are kept as context for the model.

The important case is when nothing clears the floor. If no chunk scores at or above the threshold, the app does not pass weak context to the model and hope for the best. Instead it short-circuits and answers "I don't know." This is a deliberate refusal: the app would rather admit the corpus lacks an answer than hallucinate one.

This single number is a practical guard against hallucination. Set it too high and the app refuses questions it could actually answer; set it too low and irrelevant chunks leak into the prompt. The `0.45` default is a starting point meant to be tuned against the evaluation set for a given corpus and embedding model.
