# NPC Generator - YAMLGraph Example

D&D NPC creation pipeline ported from Python to pure YAML graphs.

## Graphs

### NPC Creation (`npc-creation.yaml`)

Generate complete D&D NPCs from a concept:

```bash
yamlgraph graph run examples/npc/npc-creation.yaml \
  -v 'concept=grumpy dwarf blacksmith with a secret past'
```

**Pipeline flow:**
```
START → identity → personality → knowledge → behavior → [stats] → END
```

**Options:**
- `-v 'race=Dwarf'` - Specify race
- `-v 'character_class=Fighter'` - Specify class
- `-v 'location=The Red Dragon Inn'` - Where they're found
- `-v 'include_stats=true'` - Generate D&D 5e stats

### Encounter Turn (`encounter-turn.yaml`)

Process a single NPC turn in an encounter:

```bash
yamlgraph graph run examples/npc/encounter-turn.yaml \
  -v 'npc_name=Thorek Ironbellow' \
  -v 'location=The Rusty Anchor tavern' \
  -v 'recent_events=A hooded figure just entered'
```

**Pipeline flow:**
```
START → perceive → decide → narrate → END
```

### Encounter Loop (`encounter-loop.yaml`)

Multi-turn interactive encounter with DM interrupts and image generation:

```bash
python examples/npc/run_encounter.py
```

**Features:**
- Human-in-the-loop: pauses for DM input each turn
- Image generation: creates scene images via Replicate API
- Turn history: accumulates narrative summaries
- Loop: continues until DM types 'end'

**Pipeline flow:**
```
START → await_dm ──(end)→ END
            │
            └→ perceive → decide → narrate → describe_scene
                                                   │
                                                   ↓
                 generate_scene_image → summarize → next_turn → await_dm
```

**Node types used:**
- `interrupt` - await_dm (pauses for human input)
- `llm` - perceive, decide, narrate, describe_scene, summarize
- `python` - generate_scene_image (Replicate API)
- `passthrough` - next_turn (increment counter, append history)

**Requirements:**
- `REPLICATE_API_TOKEN` environment variable for image generation

## Prompts

All prompts are in `prompts/` using Jinja2 templates with inline schemas:

**NPC Creation:**
- `npc_identity.yaml` - Name, race, appearance, voice
- `npc_personality.yaml` - Traits, ideals, bonds, flaws
- `npc_knowledge.yaml` - World, local, and secret knowledge
- `npc_behavior.yaml` - Goals, triggers, combat style
- `npc_stats.yaml` - D&D 5e ability scores

**Encounter:**
- `encounter_perceive.yaml` - What the NPC notices
- `encounter_decide.yaml` - What action to take
- `encounter_narrate.yaml` - Scene description
- `encounter_summarize.yaml` - Turn summary for history

**Image:**
- `scene_describe.yaml` - Convert narration to image prompt

## Shared Dependencies

Uses `examples/shared/replicate_tool.py` for image generation (shared with storyboard example).

## Example Output

```
🚀 Running graph: npc-creation.yaml

📝 Generating identity...
   ✓ Thorek Ironbellow, Dwarf Blacksmith

📝 Generating personality...
   ✓ Gruff, Protective, Haunted by past

📝 Generating knowledge...
   ✓ 3 world facts, 4 local rumors, 2 secrets

📝 Generating behavior...
   ✓ Neutral disposition, 3 goals, 4 triggers

============================================================
RESULT
============================================================
{
  "name": "Thorek Ironbellow",
  "race": "Dwarf",
  "appearance": "Stocky even for a dwarf, with burn scars...",
  ...
}
```

## Ported From

Originally implemented in Python:
- `npc/showcase/npc_builder.py` (~250 LOC)
- `npc/showcase/nodes/npc_nodes.py`

Now pure YAML: ~200 lines across 3 graphs.
