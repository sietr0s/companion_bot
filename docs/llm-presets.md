# LLM sampling presets

One chat model, three sampling presets. Call sites pass a preset name. Numbers come from code defaults, overridable by a single JSON env var. The provider applies them per call with LangChain `bind` and does not rebuild the client.

## Decisions

- A preset is `temperature`, `top_p`, and `max_tokens`. Model, provider, and API key stay shared.
- Three preset names: `reply`, `rag`, `extract`.
- Call sites pass the name: `complete(system, user, preset="rag")` and the same keyword on `complete_messages`. They do not read the numbers.
- Config is `LLM_PRESETS`, one JSON object. Missing or blank env uses code defaults. A present value is merged onto those defaults: omitted preset keys and omitted fields keep the code value.
- Bad JSON, an unknown key, or an out-of-range number fails while building `LLMSettings`. The process does not start.
- An unknown preset name at the call raises. It is not replaced with `reply` or with `0.3`.
- Embeddings are not chat completions and do not take a preset.

## Defaults

| Preset | temperature | top_p | max_tokens |
|---|---|---|---|
| `reply` | 0.8 | 0.95 | 1024 |
| `rag` | 0.1 | 1.0 | 512 |
| `extract` | 0.0 | 1.0 | 1024 |

Ranges, checked at startup: temperature `0…2`, `top_p` `0…1`, `max_tokens` integer `>= 1`.

Example that changes only the reply temperature:

```json
{"reply": {"temperature": 0.9}}
```

## Call sites

| Preset | Calls |
|---|---|
| `reply` | `LLMService.generate_reply` |
| `rag` | `LLMService.retrieve_pre`, `LLMService.retrieve_post` |
| `extract` | `LLMService.cluster_topics`, `LLMService.summarize`, behavior intake classification |

## Provider

`MistralChat`, `GeminiChat`, and `OpenAICompatChat` are constructed once, without a fixed `temperature=0.3`. `LLMSettings` parses `LLM_PRESETS` once and the provider receives the resolved map of three presets.

On each `complete` / `complete_messages`, the provider looks up the name and invokes:

```text
llm.bind(temperature=..., top_p=..., max_tokens=...)
```

`bind` returns a runnable on the existing HTTP client. The stub provider used in tests does not call the network and does not send the numbers, but it rejects an unknown preset name the same way.

## Tests

No network.

- Empty `LLM_PRESETS` yields the three code defaults. A partial object overrides only the given fields. Invalid JSON, an unknown key, and out-of-range numbers raise while constructing `LLMSettings`.
- For Mistral, Gemini, and the OpenAI-compatible client, a fake `bind` / `ainvoke` sees `rag` as `0.1 / 1.0 / 512`, and the same check for `reply` and `extract`. An unknown name raises and `ainvoke` is not called.
- `generate_reply` passes `reply`. `retrieve_pre` and `retrieve_post` pass `rag`. `cluster_topics`, `summarize`, and the behavior classifier pass `extract`. Embedding calls do not pass a preset.

## Out of scope

- Per-preset model or provider.
- Admin UI for the numbers.
- Per-request overrides from a chat or HTTP body.
- Changing softmax temperature in the behavior engine. That setting is not an LLM sampling preset.
