# Feature Request: ChainMap Serialization in SimpleRedisCheckpointer

## Problem

When using `SimpleRedisCheckpointer` with graphs that have `ChainMap` in their state, serialization fails:

```
TypeError: Cannot serialize <class 'collections.ChainMap'>
TypeError: Type is not JSON serializable: ChainMap
```

This happens because `_serialize_value()` in `simple_redis.py` doesn't handle `ChainMap`.

## Context

- Questionnaire-api uses yamlgraph with `redis-simple` checkpointer
- LangGraph state contains `ChainMap` objects (possibly from channel defaults)
- Works fine with `MemorySaver` but fails with `SimpleRedisCheckpointer`

## Proposed Solution

Add ChainMap handling to `_serialize_value()` and `_deserialize_value()` in `simple_redis.py`:

1. Add import: `from collections import ChainMap`

2. In `_serialize_value()`, add before the raise:
```python
if isinstance(obj, ChainMap):
    return {"__type__": "chainmap", "value": dict(obj)}
```

3. In `_deserialize_value()`, add:
```python
if type_name == "chainmap":
    return ChainMap(value)
```

## Priority

High - blocks production Redis usage for questionnaire-api

## Related

- `yamlgraph/storage/simple_redis.py` lines 40-48
