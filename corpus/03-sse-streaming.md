# Server-Sent Events Streaming

So the user sees text appear word by word instead of waiting for a whole answer, the chat endpoint streams its response using Server-Sent Events (SSE). SSE is a simple one-way HTTP streaming format: the server keeps the response open and writes small text frames as the model produces tokens.

Each token is sent as its own frame in the form `data: {"token": "..."}\n\n`. The `data:` prefix and the blank line (two newlines) are part of the SSE convention that marks the boundary of one event. When generation is finished, the server sends a final sentinel frame, `data: [DONE]\n\n`, so the client knows to stop.

The browser does not use a framework for this. It reads the response body as a stream and runs a buffer-and-split loop: incoming bytes are appended to a buffer, the buffer is split on the `\n\n` event boundary, and each complete frame is parsed. A frame's JSON yields the next token, which is appended to the on-screen answer; the `[DONE]` frame ends the loop.

Buffering matters because network chunks do not align with frame boundaries. A frame may arrive split across reads, so the loop keeps any partial trailing frame in the buffer until the rest arrives.
