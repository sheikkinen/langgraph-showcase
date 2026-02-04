# Interrupt Subgraph Tests

Test cases for interrupt nodes inside subgraphs (FR-006 bug investigation).

## Purpose

These graphs test the interaction between:
- Parent graphs with checkpointers
- Child subgraphs with interrupt nodes
- Redis and memory checkpointers

## Files

| File | Description |
|------|-------------|
| `interrupt-parent.yaml` | Parent with memory checkpointer |
| `interrupt-parent-redis.yaml` | Parent with Redis checkpointer |
| `interrupt-parent-with-checkpointer-child.yaml` | Parent + child both with checkpointers |
| `subgraphs/interrupt-child.yaml` | Child graph with interrupt |
| `test_subgraph_interrupt.py` | Test suite |

## Key Insight

When using interrupts inside subgraphs, the **parent** graph must have the checkpointer, not the child. The child inherits the parent's checkpointer context.

## Usage

```bash
# Run tests
pytest examples/demos/interrupt/test_subgraph_interrupt.py -v
```

## Related

- [reference/interrupt-nodes.md](../../../reference/interrupt-nodes.md)
- [reference/subgraph-nodes.md](../../../reference/subgraph-nodes.md)
- [docs-planning/subgraph-interrupt-bug.md](../../../docs-planning/subgraph-interrupt-bug.md)
