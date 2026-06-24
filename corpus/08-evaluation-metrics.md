# Evaluation Metrics

A RAG app needs to be measured, not just demoed. This app is evaluated against a labelled set: questions paired with the source chunks that should be retrieved and the answers that should be produced. The evaluation has two parts, one for retrieval and one for the generated answer.

Retrieval quality is scored with three standard ranking metrics. Recall@k measures whether the correct chunks appear among the top k results. MRR (Mean Reciprocal Rank) rewards placing the first relevant chunk high in the list, scoring by the reciprocal of its rank. nDCG (normalized Discounted Cumulative Gain) credits relevant results more when they appear near the top, then normalizes against the ideal ordering.

Together these tell you whether the retriever is finding the right material and ranking it well, which is the foundation everything else depends on. Tuning choices like the minimum score floor can be checked against these numbers.

Answer quality is judged separately with an LLM-as-judge: a language model scores each generated answer for faithfulness (does it stay true to the retrieved context) and relevance (does it actually address the question). This catches failures the retrieval metrics miss, such as a correct retrieval followed by an answer that drifts off-topic or contradicts its sources.
