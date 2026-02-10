# Expression Language Reference

YAMLGraph uses a simple expression language for data flow between nodes. There are two expression systems:

1. **Value Expressions** — resolve state values for node variables and outputs (`{state.field}`)
2. **Condition Expressions** — boolean tests for edge routing (`field < 0.8`)

> Every behavior documented here is verified by tests in `tests/unit/test_expression_language.py`.

---

## Value Expressions

Value expressions resolve state values. They appear in:

| Context | Example |
|---------|---------|
| Node `variables:` | `topic: "{state.topic}"` |
| Passthrough `output:` | `counter: "{state.counter + 1}"` |
| Map node `over:` | `over: "{state.items}"` |
| Tool call `tool_name:` | `tool_name: "{state.selected_tool}"` |

### Simple Path Resolution

Wrap a dotted path in curly braces to resolve a state value:

```yaml
variables:
  name: "{state.name}"              # state["name"]
  score: "{state.critique.score}"   # state["critique"]["score"]
  deep: "{state.a.b.c}"            # state["a"]["b"]["c"]
```

**Resolution order** for each path segment:
1. Dict key lookup (`dict.get(key)`)
2. Object attribute (`getattr(obj, key)`) — handles Pydantic models

```yaml
# If state["critique"] is a Pydantic model with a .score attribute:
score: "{state.critique.score}"    # Works via getattr
```

#### The `state.` Prefix

Two resolution functions exist with different prefix rules:

| Function | Used by | `state.` prefix | On missing |
|----------|---------|-----------------|------------|
| `resolve_template` | `variables:`, `output:`, `over:` | **Required** | Returns `None` |
| `resolve_state_expression` | Internal / direct calls | Optional | Raises `KeyError` |

```yaml
# In variables: and output: — state. prefix is REQUIRED
variables:
  name: "{state.name}"    # ✓ Resolves
  name: "{name}"          # ✗ Returned as literal string "{name}"
```

### Arithmetic Expressions

Perform arithmetic on state values in passthrough `output:` and node `variables:`:

```yaml
output:
  counter: "{state.counter + 1}"
  total: "{state.a + state.b}"
  scaled: "{state.value * 2}"
  half: "{state.value / 2}"
  diff: "{state.a - state.b}"
```

**Supported operators:** `+`, `-`, `*`, `/`

**Operand types:**

| Left operand | Right operand | Examples |
|-------------|---------------|----------|
| `state.path` (required) | Integer literal | `{state.counter + 1}` |
| `state.path` (required) | Float literal | `{state.score + 0.1}` |
| `state.path` (required) | State reference | `{state.a + state.b}` |
| `state.path` (required) | List literal | `{state.items + [state.item]}` |
| `state.path` (required) | Dict literal | `{state.log + {'key': state.val}}` |

**Rules:**
- The left operand **must** start with `state.` (the regex requires it)
- `{counter + 1}` without `state.` prefix will **not** be recognized as arithmetic
- Division always returns `float` (Python `/` operator)
- Division by zero raises `ZeroDivisionError`
- If the left operand is missing from state, returns `None`
- Nested left operands work: `{state.a.b + 1}`

### List Operations

Append items to lists using the `+` operator:

```yaml
output:
  # Append a state value (wrapped in list literal)
  history: "{state.history + [state.current_item]}"

  # Append a dict directly (auto-wrapped into list)
  log: "{state.log + {'turn': state.turn, 'action': state.action}}"
```

**How `+` works with lists:**

| Left | Right | Result |
|------|-------|--------|
| `list` | `list` | Concatenation: `[1,2] + [3,4]` → `[1,2,3,4]` |
| `list` | non-list | Auto-wrap: `[1,2] + "x"` → `[1,2,"x"]` |

**List literal syntax** — `[single_item]`:
- `[state.field]` — resolves state ref, wraps in list
- `[state.a.b]` — nested state refs work
- `[42]` — literal value in list
- Multi-item `[a, b]` — **not supported** (treated as single item)

**Dict-in-list limitation:**
- `[{'key': state.val}]` — **does not work** (dict inside list literal is not parsed)
- Use `{'key': state.val}` directly instead — auto-wrapped when left operand is a list

**Important:** List operations create a new list; the original is never mutated.

### Dict Literal Syntax

Dict literals can be operands in arithmetic expressions:

```yaml
output:
  # Append dict to list (dict auto-wrapped into list)
  events: "{state.events + {'type': state.event_type, 'data': state.payload}}"
```

**Supported forms:**
- `{'key': state.path}` — state reference value
- `{'key': 42}` — literal value
- `{"key": state.path}` — double-quoted keys work
- `{'a': state.x, 'b': state.y}` — multiple key-value pairs
- Nested state refs: `{'score': state.a.b}`

---

## Condition Expressions

Condition expressions are boolean tests used in edge routing. They are evaluated **without `eval()`** using regex-based parsing.

```yaml
edges:
  - from: critique
    to: refine
    condition: critique.score < 0.8

  - from: critique
    to: END
    condition: critique.score >= 0.8
```

### Syntax Differences from Value Expressions

Conditions use a completely different syntax:

| Feature | Value expressions | Condition expressions |
|---------|-------------------|----------------------|
| Braces | `{state.field}` | No braces |
| Prefix | `state.` required | No prefix |
| Left side | State path | State path (bare) |
| Right side | State ref or literal | **Literal only** |
| Quoting | N/A | Strings must be quoted |

```yaml
# CORRECT condition syntax:
condition: score < 0.8
condition: critique.score >= 0.8
condition: status == 'done'

# WRONG (these won't work):
condition: "{state.score} < 0.8"     # No braces in conditions
condition: state.score < 0.8         # No state. prefix
condition: a < b                     # 'b' is literal string, not state.b
```

### Comparison Operators

| Operator | Meaning |
|----------|---------|
| `<` | Less than |
| `<=` | Less than or equal |
| `>` | Greater than |
| `>=` | Greater than or equal |
| `==` | Equal |
| `!=` | Not equal |

The left side is always a dotted state path. The right side is always a **literal value**.

### Right-Side Literal Values

The right side of a comparison is parsed as a literal:

| Syntax | Parsed as | Type |
|--------|-----------|------|
| `42` | `42` | `int` |
| `-5` | `-5` | `int` |
| `0.8` | `0.8` | `float` |
| `true` | `True` | `bool` (case-insensitive) |
| `false` | `False` | `bool` (case-insensitive) |
| `null` | `None` | `NoneType` |
| `None` | `None` | `NoneType` |
| `'hello'` | `"hello"` | `str` |
| `"hello"` | `"hello"` | `str` |
| `hello` | `"hello"` | `str` (unquoted fallback) |

> **Type matters:** `flag == true` tests against boolean `True`. `flag == 'true'` tests against string `"true"`. These are not the same.

### Compound Conditions

Combine comparisons with `and` / `or` (case-insensitive):

```yaml
# AND — all must be true
condition: "has_gaps == true and probe_count < 10"

# OR — any can be true
condition: "status == 'done' or retry_count >= 3"

# Mixed — AND has higher precedence
condition: "a > 10 or b < 5 and c > 3"
# Parsed as: (a > 10) OR ((b < 5) AND (c > 3))
```

**Precedence:**
1. `or` splits first (lower precedence)
2. `and` splits within each `or` branch (higher precedence)
3. Individual comparisons are evaluated last

Multiple terms work: `a > 1 and b < 10 and c == 7`

### Not Supported

The following are **not supported** by design:

| Feature | Example | What happens |
|---------|---------|-------------|
| Parentheses | `(a > 1) and (b < 2)` | `ValueError` raised |
| NOT operator | `not flag == true` | `ValueError` raised |
| State ref on right | `a < b` (meaning state.b) | `b` parsed as literal string |
| Nested expressions | `a > (b + 1)` | `ValueError` raised |

### Gotchas

#### `and`/`or` Keywords in String Values

**WARNING:** The keywords `and` and `or` inside quoted string values will break condition parsing:

```yaml
# BROKEN — 'and' inside the value triggers compound split:
condition: "status == 'done and dusted'"
# Splits into: "status == 'done" AND "dusted'"
# Result: incorrect evaluation (False or ValueError)

# WORKAROUND: use a different value or encode differently
condition: "status == 'done_and_dusted'"
```

This is because the compound split uses regex `\s+and\s+` / `\s+or\s+` which cannot distinguish keywords from content inside quotes.

### Missing Values in Conditions

| Operator | Missing left value | Behavior |
|----------|-------------------|----------|
| `<`, `>`, `<=`, `>=` | Returns `False` |
| `==` | `None == None` → `True` |
| `!=` | `None != anything` → `True` |

### Whitespace

Whitespace around operators is flexible:

```yaml
condition: "score < 0.8"       # Normal
condition: "  score   <  0.8 " # Extra whitespace — works
condition: "score<0.8"          # No whitespace — works
```

---

## Where Expressions Are Used

### Node `variables:` — `resolve_template`

```yaml
nodes:
  draft:
    type: llm
    prompt: write_draft
    variables:
      topic: "{state.topic}"          # Simple path
      count: "{state.word_count}"     # Simple path
```

Requires `state.` prefix. Missing paths return `None` (no error).

### Passthrough `output:` — `resolve_template`

```yaml
nodes:
  update_state:
    type: passthrough
    output:
      counter: "{state.counter + 1}"                    # Arithmetic
      history: "{state.history + [state.current]}"       # List append
      log: "{state.log + {'event': state.event_type}}"   # Dict append
```

Requires `state.` prefix. Arithmetic and list operations supported.

### Map node `over:` — `resolve_state_expression`

```yaml
nodes:
  process_items:
    type: map
    over: "{state.items}"             # Must resolve to a list
    as: item
```

### Edge `condition:` — `evaluate_condition`

```yaml
edges:
  - from: check
    to: retry
    condition: "has_gaps == true and probe_count < 10"
  - from: check
    to: END
    condition: "has_gaps == false"
```

No braces, no `state.` prefix. Bare dotted paths only.

---

## `resolve_node_variables` Behavior

When a node has explicit `variables:`, each template is resolved against state.

When no `variables:` are specified (or empty dict), the **entire state** is passed as variables, with two filters:
- Keys starting with `_` are excluded (internal keys like `_route`)
- `None` values are excluded

Falsy values `0`, `False`, `""`, `[]` are **not** filtered — only `None`.

---

## Grammar (Semi-Formal EBNF)

```ebnf
(* Value Expressions — used in variables:, output:, over: *)
value_expr     = "{" ( arith_expr | path_expr ) "}" ;
path_expr      = "state." identifier { "." identifier } ;
arith_expr     = "state." identifier { "." identifier } operator operand ;
operator       = "+" | "-" | "*" | "/" ;
operand        = state_ref | list_literal | dict_literal | number ;
state_ref      = "state." identifier { "." identifier } ;
list_literal   = "[" ( state_ref | literal ) "]" ;       (* single item only *)
dict_literal   = "{"  kv_pair { "," kv_pair } "}" ;
kv_pair        = quoted_key ":" ( state_ref | literal ) ;
quoted_key     = "'" identifier "'" | '"' identifier '"' ;

(* Condition Expressions — used in edge condition: *)
condition      = or_expr ;
or_expr        = and_expr { " or " and_expr } ;           (* case-insensitive *)
and_expr       = comparison { " and " comparison } ;       (* case-insensitive *)
comparison     = path comp_op literal ;
path           = identifier { "." identifier } ;           (* no state. prefix *)
comp_op        = "<=" | ">=" | "==" | "!=" | "<" | ">" ;
literal        = quoted_string | boolean | null | number | raw_string ;

(* Shared Literals *)
quoted_string  = '"' chars '"' | "'" chars "'" ;
boolean        = "true" | "false" ;                        (* case-insensitive *)
null           = "null" | "none" ;
number         = [ "-" ] digits [ "." digits ] ;
raw_string     = chars ;                                   (* fallback *)
identifier     = letter_or_underscore { letter_or_underscore | digit | "." } ;
```

---

## Implementation Files

| File | Purpose |
|------|---------|
| `yamlgraph/utils/expressions.py` | Value expression resolution |
| `yamlgraph/utils/conditions.py` | Condition evaluation |
| `yamlgraph/utils/parsing.py` | Shared literal parsing |
| `tests/unit/test_expression_language.py` | TDD specification (130 tests) |

## Related

- [Graph YAML Reference](graph-yaml.md) — Full graph configuration
- [Passthrough Nodes](passthrough-nodes.md) — Counter and accumulator patterns
- [Map Nodes](map-nodes.md) — Fan-out with `over:` expression
- [Patterns](patterns.md) — Common graph patterns using expressions
