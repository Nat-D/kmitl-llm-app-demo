# Embeddings with bge-m3

Retrieval in this app depends on embeddings: numeric vectors that place similar text near each other in space. The app uses the `bge-m3` embedding model, served through the same LiteLLM proxy as the chat model, so the code requests embeddings with the same OpenAI client.

Each `bge-m3` embedding is a 1024-dimensional vector. Every chunk of source text is embedded once when it is indexed, and the resulting vector is stored alongside the chunk. At query time the user's question is embedded the same way, producing another 1024-dimensional vector that can be compared against the stored ones.

A key property of `bge-m3` is that it is multilingual, including Thai. A question asked in Thai can retrieve relevant notes written in English, and vice versa, because both map into the same shared vector space. This matters for a course where source material and student questions may mix languages.

Because the query embedding and the chunk embeddings share the same model and the same 1024 dimensions, they are directly comparable. The app measures their closeness with cosine similarity to decide which chunks are most relevant to the question.
