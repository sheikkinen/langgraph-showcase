# Novel Generator Demo

> Ever fancied writing a novel? Now you can:
> ```bash
> yamlgraph graph run examples/demos/novel_generator/graph.yaml \
>   --var premise="Your story idea here" --var genre="fantasy"
> ```

A complete AI-powered story generator demonstrating YAMLGraph's core patterns: evolution loops, map nodes, and quality gates.

## Quick Start

```bash
# Generate a short story (3 beats)
yamlgraph graph run examples/demos/novel_generator/graph.yaml \
  --var premise="A baker discovers she can taste emotions" \
  --var genre="magical realism" \
  --var target_beats=3

# Longer story (10 beats)
yamlgraph graph run examples/demos/novel_generator/graph.yaml \
  --var premise="A lighthouse keeper's parents disappeared with a ghost ship" \
  --var genre="dark fantasy" \
  --var target_beats=10
```

## Saving Results

```bash
# Save full output to file
yamlgraph graph run examples/demos/novel_generator/graph.yaml \
  --var premise="A librarian discovers books that rewrite themselves" \
  --var genre="literary fantasy" \
  --var target_beats=3 \
  --full > outputs/novel_generator/my_story.txt

# Or with tee to see output AND save
yamlgraph graph run examples/demos/novel_generator/graph.yaml \
  --var premise="A clockmaker builds a device that stops time" \
  --var genre="steampunk" \
  --var target_beats=3 \
  --full 2>&1 | tee outputs/novel_generator/clockmaker.txt

# With LangSmith trace URL for debugging
yamlgraph graph run examples/demos/novel_generator/graph.yaml \
  --var premise="A chef's recipes come to life" \
  --var genre="magical realism" \
  --var target_beats=3 \
  --share-trace
```

**Output structure:**
```
outputs/novel_generator/
├── my_story.txt          # Full pipeline output
└── clockmaker.txt        # Another story

# Each output contains:
# - synopsis (title, logline, full synopsis)
# - timeline (beats breakdown)
# - prose_sections (generated story text)
# - review (quality assessment)
```

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: IDEATION (Evolution Loop)                              │
│                                                                 │
│   generate_synopsis → analyze_synopsis ─┬→ (grade≥B) → PHASE 2  │
│                             ↑           │                       │
│                             └───────────┼→ evolve_synopsis      │
│                                         │        ↓              │
│                                         └────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: GENERATION (Map Node - Parallel)                       │
│                                                                 │
│   construct_timeline → generate_prose (map over beats)          │
│                              ↓                                  │
│                        [beat_1] → prose                         │
│                        [beat_2] → prose                         │
│                        [beat_N] → prose                         │
│                              ↓                                  │
│                        (fan-in: prose_sections)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: ASSEMBLY (Review Gate)                                 │
│                                                                 │
│   review_draft ─┬→ (passed=true) → END                          │
│        ↑        │                                               │
│        │        └→ (passed=false) → revise_draft                │
│        └────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Key Patterns Demonstrated

### 1. Evolution Loop (Phase 1)
Quality-driven iteration until synopsis meets threshold.

```yaml
edges:
  # Grade > 'B' means C, D, F → needs evolution
  # Grade <= 'B' means A, B → proceed to timeline
  - from: analyze_synopsis
    to: evolve_synopsis
    condition: "analysis.grade > 'B'"
  - from: analyze_synopsis
    to: construct_timeline
    condition: "analysis.grade <= 'B'"
```

### 2. Map Node (Phase 2)
Parallel prose generation for each story beat.

```yaml
generate_prose:
  type: map
  over: "{state.timeline.beats}"
  as: beat
  collect: prose_sections
```

### 3. Quality Gate (Phase 3)
Review-revise loop with conditional exit.

```yaml
edges:
  - from: review_draft
    to: END
    condition: "review.passed == true"
  - from: review_draft
    to: revise_draft
    condition: "review.passed == false"
```

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `graph.yaml` | 84 | Pipeline definition |
| `prompts/synopsis/generate.yaml` | ~55 | Initial synopsis |
| `prompts/synopsis/analyze.yaml` | ~45 | Quality analysis |
| `prompts/synopsis/evolve.yaml` | ~55 | Synopsis improvement |
| `prompts/timeline/construct.yaml` | ~50 | Beat breakdown |
| `prompts/prose/generate_beat.yaml` | ~45 | Per-beat prose |
| `prompts/review/review.yaml` | ~50 | Quality review |
| `prompts/review/revise.yaml` | ~45 | Targeted revision |

## Development Process

This demo was built using YAMLGraph's standard TDD workflow:

1. **Red Phase:** Wrote 5 failing tests exercising REQ-YG-024 (routing) and REQ-YG-040 (map nodes)
2. **Green Phase:** Implemented graph.yaml and prompts until all tests passed
3. **Refactor Phase:** Added comments, safety limits, documentation

```bash
# Verify tests pass
pytest tests/integration/test_novel_generator.py -v

# Lint the graph
cd examples/demos/novel_generator && yamlgraph graph lint graph.yaml
```

## Learning Path

After this demo, explore:
- [reflexion](../reflexion/) - Simpler evolution loop
- [map](../map/) - Map node basics
- [innovation_matrix](../innovation_matrix/) - Another multi-phase pipeline

---

## Sample Output

**Premise:** "A baker discovers she can taste emotions"
**Genre:** magical realism
**Beats:** 3

### The Flavor of Feelings

#### Act 1: Discovery

Maya's fingers pressed into the butter, folding it between layers of dough for the third time. The kitchen was still dark—4:47 AM, according to the clock above the stove—and the only sound was the whisper of her rolling pin against the marble counter. She'd done this a thousand times, muscle memory guiding her through the motions her grandmother had taught her as a child.

But this morning tasted different.

It started as she brought the dough to her nose, checking for the yeasty sweetness that meant the first rise was complete. Instead of smelling it, she felt it—a sharp, metallic tang coating her tongue. Grief. Not her grief. Someone else's, ancient and heavy, pressing down like fog on the harbor outside.

Maya froze, her hands still buried in the dough.

She closed her eyes and breathed through her mouth. The taste bloomed: dark chocolate and burnt sugar, the flavor of something beautiful turned to ash. Underneath it, something else—a bitter, green note that made her jaw clench. Jealousy. She could taste it as clearly as she could taste the salt she'd mixed in herself.

"Abuela?" she whispered to the empty kitchen.

#### Act 2: Confrontation

The folder hit the counter with a slap that made Maya flinch. Blueprints, crisp and official, spilled across the worn laminate—architectural drawings of a parking structure where the restaurant currently stood.

"It's a good offer," Richard said, his voice smooth as caramel, carrying none of the bitterness she expected. He wore an expensive suit that looked uncomfortable on him, like borrowed skin. "More than fair, actually."

Maya's gift surged without warning. She tasted it immediately—the flavor of his words, the actual *taste* beneath them. It was sour, metallic. Dishonest. But not the dishonesty of a man lying to his family. This was something else. Something hollow.

Richard pulled out a check. The numbers made Maya's breath catch, but it wasn't the amount that disturbed her—it was what she tasted when Richard slid it across the counter. Nothing. Absolutely nothing. No guilt, no satisfaction, no conflict. Just a void where emotion should have been.

And that meant she had no way to reach him.

#### Act 3: Resolution

Maya's hands moved through the dough like a conductor through an orchestra, each fold deliberate, each turn infused with intention. She wasn't thinking anymore—she was feeling. Every loss she'd witnessed in the community, every moment of loneliness she'd absorbed through her fingertips over the past weeks, flowed directly into the pastries taking shape before her.

She approached Richard with a single cannoli, still warm. "Try it," she said.

He took it reluctantly, bit into it, and his jaw tightened. His eyes glistened.

"What is this?" he whispered.

"It tastes like the day your mother taught you to make pasta," Maya said quietly. "Like you remembered what that felt like. Like you let yourself feel it again."

By the end of the week, the landlord had called with news: three community organizations had pooled resources to buy the building. The bakery wasn't just saved—it was transformed into something the neighborhood would protect fiercely.

Richard found Maya restocking the shelves that night.

"I don't understand your gift," he said. "But I understand that you have one."

Maya nodded, accepting the weight of it—the responsibility to never bake carelessly again, to always remember that her hands held the power to heal or harm.

---

*~1,100 words | Generated in ~90 seconds by YAMLGraph novel_generator (84 lines YAML)*
