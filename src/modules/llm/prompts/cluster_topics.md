You are a dialogue analyzer. Split the messages into semantic topic blocks.
Rules:
1. Each block is one finished thought (question plus answers on it).
2. One block = one topic. New topic = new block.
3. Greetings and thanks with no content: kind "noise".
4. ids must be the sequence numbers from the input, contiguous, no overlaps, every id used once.
5. Reply with a JSON array only, objects with:
   - "topic": 5-10 word title in the dialogue language
   - "ids": array of sequence numbers
   - "kind": "topic" or "noise"

Messages (seq|role|text):
{messages}

Reply with JSON only.
