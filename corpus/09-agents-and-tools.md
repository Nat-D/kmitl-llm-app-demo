# Agents and Tools

The later stage of the course extends the app from a single retrieve-then-answer pass into an agent. An agent lets the model decide, step by step, what to do next instead of running one fixed pipeline. This is useful when a question needs several lookups or some reasoning between them.

The agent runs a loop with three repeating moves: call the model, run the tool the model asked for, then feed the tool's result back into the model. The model sees the new result, decides what to do next, and the loop repeats. Crucially the loop has a stop condition: it ends when the model produces a final answer rather than another tool request (or hits a safety limit on iterations), so it cannot spin forever.

Tools are the actions the agent can take. In this app the main tool searches the notes, the same retrieval over the SQLite vector store used in basic RAG. The difference is that the agent can choose when and how often to search, and can refine its query based on what earlier searches returned.

This builds directly on the rest of the stack. Each tool call still uses `bge-m3` embeddings and cosine similarity, and the final answer can carry citations, but now the model orchestrates retrieval instead of it happening once up front.
