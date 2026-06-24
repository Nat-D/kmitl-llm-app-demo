# Vector Store

The vector store is where the app keeps the knowledge it can retrieve from. To stay simple and dependency-free, it is a plain SQLite database. Each row holds a chunk of source text together with its `bge-m3` embedding, the 1024-dimensional vector that represents that chunk.

Retrieval does not use a specialized index. When a question comes in, the app embeds the question, loads the stored chunk embeddings, and computes cosine similarity between the question vector and each chunk vector using NumPy. The chunks are then ranked by that similarity score, and the top results are passed forward to the model.

Cosine similarity measures the angle between two vectors rather than their magnitude, which is a standard and well-behaved choice for comparing text embeddings. Computing it in NumPy over all chunks is a brute-force scan: clear and correct, and fast enough for a small course corpus.

This design is deliberately a teaching baseline. For a larger or production corpus, the brute-force scan would be replaced by a real vector index. The intended swaps are pgvector (vectors inside PostgreSQL) or sqlite-vec (a vector search extension for SQLite), both of which add indexed similarity search without changing the overall retrieval idea.
