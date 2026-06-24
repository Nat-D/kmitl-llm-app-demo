# FastAPI Backend

The backend is a FastAPI application, and it does two jobs: it serves the API the chat UI calls, and it serves the static frontend itself. The frontend is plain HTML and JavaScript with no framework, so FastAPI can hand out those static files directly and there is no separate web server to run.

The main API route is `POST /api/chat`. The browser sends the user's message to this endpoint, and the endpoint runs the RAG flow: embed the question, retrieve chunks from the SQLite vector store, build the prompt, and call the chat model through the LiteLLM proxy. Its response is streamed back as Server-Sent Events rather than a single JSON blob.

Incoming requests are validated by a Pydantic model. FastAPI uses that model to parse and type-check the JSON body before any handler logic runs, so a malformed request is rejected early with a clear error instead of failing deep inside the pipeline.

This keeps the whole demo in one small process. A single FastAPI app holds the request validation, the retrieval logic, the proxy calls, the streaming response, and the static files, which makes it easy for students to read end to end and to run locally.
