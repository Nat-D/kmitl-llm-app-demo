# LiteLLM Proxy

This app does not call a model vendor directly. Instead it talks to a LiteLLM proxy, which exposes an OpenAI-compatible API in front of whatever models the course has deployed. Because the proxy speaks the OpenAI wire format, the application code can use the standard OpenAI Python client unchanged.

The chat model is `gemma-4-E4B-it`, served through this proxy. The same proxy also serves the embedding model, so chat and embeddings share one endpoint and one set of credentials.

The OpenAI client is pointed at the proxy with two environment variables. `OPENAI_BASE_URL` is set to the proxy's URL, and `OPENAI_API_KEY` holds the key the proxy accepts. With those set, `from openai import OpenAI; OpenAI()` connects to the proxy automatically, and calls such as `chat.completions.create(...)` route to the configured model.

The benefit of this layering is that the model can be swapped, rate-limited, logged, or load-balanced at the proxy without touching the application. The app only needs to know the model name and the OpenAI-shaped interface. This keeps the demo small while staying close to how production LLM systems are wired.
