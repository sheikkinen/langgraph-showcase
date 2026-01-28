# Router Demo: Tone-Based Routing

Routes customer messages to different response handlers based on detected **emotional tone**.

## Quick Start

```bash
# Positive tone
yamlgraph graph run graphs/router-demo.yaml --var message="I absolutely love your product!"

# Negative tone
yamlgraph graph run graphs/router-demo.yaml --var message="This is frustrating, nothing works"

# Neutral tone
yamlgraph graph run graphs/router-demo.yaml --var message="What are your business hours?"
```

## Flow

```
User Message
     │
     ▼
┌─────────────────────────────┐
│   classify (type: router)   │
│   Returns: {tone, confidence}│
└─────────────────────────────┘
     │
     ├── tone="positive" ──▶ respond_positive ──▶ Upbeat response
     ├── tone="negative" ──▶ respond_negative ──▶ Empathetic response
     └── tone="neutral"  ──▶ respond_neutral  ──▶ Informative response
```

## Files

| File | Purpose |
|------|---------|
| `classify_tone.yaml` | LLM classifies message tone |
| `respond_positive.yaml` | Upbeat, enthusiastic response |
| `respond_negative.yaml` | Empathetic, helpful response |
| `respond_neutral.yaml` | Informative, factual response |

## How It Works

1. **classify** node calls LLM with `classify_tone` prompt
2. LLM returns `ToneClassification(tone="positive", confidence=0.95, reasoning="...")`
3. Router extracts `tone` field and sets `_route = "positive"` in state
4. Graph routes to `respond_positive` node based on `_route`
5. Handler generates appropriate response

## Graph Definition

See [graphs/router-demo.yaml](../../graphs/router-demo.yaml)

## Example Output

```
$ yamlgraph graph run graphs/router-demo.yaml --var message="I love this product!"

🔍 Classifying tone...
📊 Detected: positive (confidence: 0.95)
🚀 Routing to: respond_positive

Response:
That's wonderful to hear! We're so glad you're enjoying our product.
Your satisfaction means everything to us!
```
