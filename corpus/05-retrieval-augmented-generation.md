# Retrieval-Augmented Generation

Retrieval-Augmented Generation (RAG) is the core pattern of this app. Instead of asking the language model to answer from memory, the app first retrieves relevant text from its own notes and gives that text to the model as context. The model then grounds its answer in the supplied passages rather than inventing facts.

The flow has clear steps. The user's question is embedded with `bge-m3` into a 1024-dimensional vector. That vector is compared against the stored chunk embeddings in the SQLite vector store using cosine similarity computed in NumPy. The top-ranked chunks are selected as context.

Those chunks are then assembled into the prompt as a numbered list and sent to the chat model, `gemma-4-E4B-it`, through the LiteLLM proxy. The model writes its answer from that context and is asked to cite the chunks it used as `[1]`, `[2]`, and so on.

RAG matters because a small model has limited and possibly stale internal knowledge. By retrieving course-specific notes at query time, the app can answer questions about material the model never saw in training, keep answers traceable to sources, and update its knowledge simply by changing the indexed documents rather than retraining.
