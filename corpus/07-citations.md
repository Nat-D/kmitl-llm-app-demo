# Citations

Grounded answers are only trustworthy if you can check them, so this app makes the model cite its sources. Citations tie each claim back to the specific retrieved chunk it came from, letting a reader verify the answer against the underlying notes.

The mechanism is straightforward. When the retrieved chunks are placed into the prompt, they are formatted as a numbered list: chunk one, chunk two, and so on. The model is instructed to refer to these sources by their numbers, writing markers like `[1]` and `[2]` inline in its answer wherever it uses information from a given chunk.

Because the numbers in the answer correspond directly to positions in the numbered context list, the application can map each marker back to the exact chunk and show the source to the user. A claim marked `[2]` is meant to be supported by the second chunk that was retrieved for that question.

Citations also reinforce the rest of the RAG design. They encourage the model to stay within the supplied context rather than drawing on unsupported memory, and they pair naturally with the minimum score floor: when no chunk is good enough to cite, the app answers "I don't know" instead of producing uncited claims.
