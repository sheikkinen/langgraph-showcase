# OpenAI-Compatible YAMLGraph Proxy

An OpenAI-compatible guardrail proxy that routes every `/v1/chat/completions` call through a
YAMLGraph graph: **echo** → **validate** → **LLM respond**.

## Architecture

```
POST /v1/chat/completions (Bearer: WEB_API_KEY)
  → verify_token(WEB_API_KEY)
  → run graph:
      echo_input:     log raw input, store in state.echo
      validate_input: stamp *validation missing*, store in state.validation
      respond:        LLM prompt uses {{validation}} as content
  → format response as OpenAI ChatCompletion
  → return to client
```

## Local Development

```bash
# Set env vars
export WEB_API_KEY=test-key
export PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Run server
uvicorn examples.openai_proxy.api.app:app --reload --factory

# Test with curl
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-haiku-4-5", "messages": [{"role": "user", "content": "Hello"}]}'
```

## Test with OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="test-key")
r = client.chat.completions.create(
    model="claude-haiku-4-5",
    messages=[{"role": "user", "content": "Hello"}],
)
print(r.choices[0].message.content)
```

## Deploy to Fly.io

```bash
cd examples/openai_proxy
fly apps create yamlgraph-proxy
fly secrets set \
  WEB_API_KEY=yg-secret-xxx \
  PROVIDER=anthropic \
  ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

## Tests

```bash
pytest examples/openai_proxy/tests/ -v
```

## File Structure

```
examples/openai_proxy/
├── api/
│   ├── app.py           # FastAPI + OpenAI endpoints
│   └── models.py        # Pydantic request/response models
├── nodes/
│   └── tools.py         # echo_input, validate_input
├── prompts/
│   └── respond.yaml     # LLM prompt with {{validation}}
├── tests/
│   ├── test_app.py      # API endpoint tests
│   ├── test_fly_config.py
│   ├── test_graph.py    # Graph YAML structure tests
│   ├── test_models.py   # Pydantic model tests
│   └── test_tools.py    # Tool node tests
├── graph.yaml           # echo → validate → respond
├── fly.toml
├── Dockerfile
└── README.md
```
