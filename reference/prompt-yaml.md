# Prompt YAML Reference

This document explains all configuration options for prompt YAML files in the `prompts/` directory.

## File Structure

```yaml
# Option 1: Native schema format
schema:
  name: OutputModel
  fields:
    field_name:
      type: str
      description: "Field description"

# Option 2: JSON Schema format (alternative)
output_schema:
  type: object
  properties:
    field_name:
      type: string
      description: "Field description"
  required: [field_name]

# System message (always required)
system: |
  You are a helpful assistant...

# User message (simple templates)
user: |
  Please process: {input}

# OR: Template (advanced Jinja2)
template: |
  {% for item in items %}
  {{ item.name }}
  {% endfor %}
```

---

## Prompt Sections

### `system`
**Type:** `string` (multiline)
**Required:** Yes

The system message that sets the LLM's behavior and persona.

```yaml
system: |
  You are a creative content writer. Generate engaging, informative content
  on the requested topic.

  Your writing should be:
  - Clear and well-structured
  - Engaging and informative
  - Appropriate for a general audience
```

### `user`
**Type:** `string` (multiline)
**Required:** Yes (unless `template` is used)

The user message with simple `{variable}` placeholders.

```yaml
user: |
  Write about: {topic}

  Target length: approximately {word_count} words
  Style: {style}
```

**Placeholder syntax:**
- `{variable_name}` - Replaced with variable value
- Lists are automatically joined with `, `

### `template`
**Type:** `string` (multiline)
**Required:** No (alternative to `user`)

Advanced template using Jinja2 syntax for loops, conditionals, and filters.

```yaml
template: |
  ## Items to Analyze

  {% for item in items %}
  ### {{ loop.index }}. {{ item.title }}
  **Content**: {{ item.content[:200] }}...
  {% endfor %}
```

When to use `template` vs `user`:
- Use `user` for simple variable substitution
- Use `template` when you need loops, conditionals, or filters

---

## Inline Schema

Define structured output directly in the prompt YAML, making prompts self-contained.

### Basic Schema Structure

```yaml
schema:
  name: MyOutputModel       # Pydantic model name
  fields:
    field_name:
      type: str             # Python type
      description: "..."    # Field description (helps LLM)
```

### Supported Types

| Type String | Python Type | Example |
|-------------|-------------|---------|
| `str` | `str` | `"hello"` |
| `int` | `int` | `42` |
| `float` | `float` | `0.95` |
| `bool` | `bool` | `true` |
| `list[str]` | `list[str]` | `["a", "b"]` |
| `list[int]` | `list[int]` | `[1, 2, 3]` |
| `dict[str, str]` | `dict[str, str]` | `{"key": "value"}` |
| `dict[str, Any]` | `dict[str, Any]` | `{"key": ...}` |
| `Any` | `Any` | Any value |

### Field Properties

```yaml
schema:
  name: Example
  fields:
    # Required string field
    title:
      type: str
      description: "The document title"

    # Float with constraints
    confidence:
      type: float
      description: "Confidence score"
      constraints:
        ge: 0.0               # Greater than or equal
        le: 1.0               # Less than or equal

    # Optional field with default
    tags:
      type: list[str]
      description: "Content tags"
      default: []             # Default value if not provided

    # Optional nullable field
    notes:
      type: str
      description: "Optional notes"
      optional: true          # Can be null
```

### Constraint Reference

| Constraint | Type | Description |
|------------|------|-------------|
| `ge` | `int`/`float` | Greater than or equal |
| `le` | `int`/`float` | Less than or equal |
| `gt` | `int`/`float` | Greater than |
| `lt` | `int`/`float` | Less than |
| `min_length` | `str`/`list` | Minimum length |
| `max_length` | `str`/`list` | Maximum length |
| `pattern` | `str` | Regex pattern |

---

## JSON Schema Format (output_schema)

Alternative to the native `schema:` format. Uses standard JSON Schema syntax, familiar to most developers.

### Basic Structure

```yaml
output_schema:
  type: object
  properties:
    field_name:
      type: string
      description: "Field description"
  required: [field_name]
```

### Supported JSON Schema Types

| JSON Schema Type | Python Type | Notes |
|------------------|-------------|-------|
| `string` | `str` | Basic string |
| `integer` | `int` | Whole numbers |
| `number` | `float` | Decimal numbers |
| `boolean` | `bool` | True/false |
| `array` | `list` | Use `items` for element type |
| `object` | `dict` | Nested objects |

### Array Types

```yaml
output_schema:
  type: object
  properties:
    tags:
      type: array
      items:
        type: string
      description: "List of tags"
    scores:
      type: array
      items:
        type: number
      description: "List of scores"
```

### Enum Values

```yaml
output_schema:
  type: object
  properties:
    action_type:
      type: string
      enum: [speak, move, attack, defend, wait]
      description: "Type of action to take"
    priority:
      type: string
      enum: [low, medium, high, critical]
```

### Complete Example

```yaml
system: |
  You are analyzing customer feedback.

user: |
  Analyze this feedback: {{ feedback }}

output_schema:
  type: object
  properties:
    sentiment:
      type: string
      enum: [positive, negative, neutral]
      description: "Overall sentiment"
    confidence:
      type: number
      description: "Confidence score 0-1"
    themes:
      type: array
      items:
        type: string
      description: "Key themes identified"
    summary:
      type: string
      description: "Brief summary"
  required: [sentiment, confidence, themes, summary]
```

### When to Use Which Format

| Format | Best For |
|--------|----------|
| `schema:` | Type constraints (ge, le), Python-native syntax |
| `output_schema:` | JSON Schema familiarity, enum values, required fields |

Both formats produce identical Pydantic models at runtime.

---

## Jinja2 Template Features

When using `template` or when `system`/`user` contain `{{` or `{%`, Jinja2 mode is activated.

### Variables

```yaml
template: |
  Topic: {{ topic }}
  Author: {{ state.author }}    # Access state directly
```

### Loops

```yaml
template: |
  {% for item in items %}
  - {{ item.title }}: {{ item.content }}
  {% endfor %}
```

**Loop context variables:**
- `loop.index` - 1-based iteration count
- `loop.index0` - 0-based iteration count
- `loop.first` - True on first iteration
- `loop.last` - True on last iteration
- `loop.length` - Total number of items

### Conditionals

```yaml
template: |
  {% if score > 0.8 %}
  High confidence result.
  {% elif score > 0.5 %}
  Medium confidence result.
  {% else %}
  Low confidence - review needed.
  {% endif %}
```

### Filters

```yaml
template: |
  Tags: {{ tags | join(", ") }}
  Preview: {{ content[:100] }}...
  Count: {{ items | length }}
  Upper: {{ title | upper }}
```

**Common filters:**
- `join(sep)` - Join list items
- `length` - Get length
- `upper` / `lower` - Case conversion
- `default(value)` - Default if undefined
- `first` / `last` - First/last item

### String Slicing

```yaml
template: |
  {% if content|length > 200 %}
  Preview: {{ content[:200] }}...
  {% else %}
  Full: {{ content }}
  {% endif %}
```

---

## Complete Examples

### Simple Prompt (No Schema)

```yaml
# prompts/greet.yaml
system: |
  You are a friendly assistant.

user: |
  Greet the user named {name} in a {style} manner.
```

### Structured Output Prompt

```yaml
# prompts/generate.yaml
schema:
  name: GeneratedContent
  fields:
    title:
      type: str
      description: "Title of the generated content"
    content:
      type: str
      description: "The main generated text"
    word_count:
      type: int
      description: "Approximate word count"
    tags:
      type: list[str]
      description: "Relevant tags"
      default: []

system: |
  You are a creative content writer. Generate engaging content.

user: |
  Write about: {topic}
  Target length: approximately {word_count} words
  Style: {style}
```

### Router Classification Prompt

```yaml
# prompts/router-demo/classify_tone.yaml
schema:
  name: ToneClassification
  fields:
    tone:
      type: str
      description: "Detected tone: positive, negative, or neutral"
    confidence:
      type: float
      description: "Confidence score 0-1"
      constraints:
        ge: 0.0
        le: 1.0
    reasoning:
      type: str
      description: "Explanation for the classification"

system: |
  You are a tone classifier. Analyze the user's message and classify its tone.

  Respond with exactly one of these tones:
  - positive: Happy, grateful, excited, satisfied
  - negative: Frustrated, angry, disappointed, upset
  - neutral: Informational, questioning, matter-of-fact

user: |
  Classify the tone of this message:

  "{message}"
```

### Jinja2 List Processing Prompt

```yaml
# prompts/analyze_list.yaml
system: |
  You are an expert content summarizer.

template: |
  Please analyze the following {{ items|length }} items:

  {% for item in items %}
  ### {{ loop.index }}. {{ item.title }}
  **Topic**: {{ item.topic }}
  {% if item.tags %}
  **Tags**: {{ item.tags | join(", ") }}
  {% endif %}

  {% if item.content|length > 200 %}
  **Preview**: {{ item.content[:200] }}...
  {% else %}
  **Content**: {{ item.content }}
  {% endif %}
  ---
  {% endfor %}

  {% if min_confidence %}
  Note: Only include insights with confidence >= {{ min_confidence }}
  {% endif %}
```

### Critique Prompt (For Loops)

```yaml
# prompts/reflexion-demo/critique.yaml
schema:
  name: Critique
  fields:
    score:
      type: float
      description: "Quality score 0-1"
      constraints:
        ge: 0.0
        le: 1.0
    feedback:
      type: str
      description: "Specific improvement suggestions"
    issues:
      type: list[str]
      description: "List of identified issues"
      default: []
    should_refine:
      type: bool
      description: "Whether refinement is needed"
      default: true

system: |
  You are a critical essay reviewer. Evaluate the essay draft and provide:
  1. A quality score from 0.0 to 1.0 (where 0.8+ is publication-ready)
  2. Specific, actionable feedback for improvement
  3. A list of specific issues found
  4. Whether refinement is needed (score < 0.8)

user: |
  Please critique this essay draft (iteration {iteration}):

  ---
  {content}
  ---
```

### Agent Tool Prompt

```yaml
# prompts/code_review.yaml
system: |
  You are a code review assistant. You can:

  1. **git_log**: View recent commits
     - count: Number of commits to show

  2. **git_diff**: See file changes
     - commits: How many commits back to diff

  3. **git_show**: View commit details
     - commit: The commit hash

  Analyze the repository and provide insights about:
  - Recent development activity
  - Code quality patterns
  - Collaboration patterns

user: |
  Review the code repository and provide your analysis.
```

---

## Best Practices

### 1. Always Include Descriptions

Descriptions help the LLM understand what each field should contain:

```yaml
fields:
  summary:
    type: str
    description: "A 2-3 sentence summary of the main points"  # Good
```

### 2. Use Constraints for Bounded Values

```yaml
fields:
  rating:
    type: float
    description: "Quality rating"
    constraints:
      ge: 0.0
      le: 5.0
```

### 3. Provide Defaults for Optional Lists

```yaml
fields:
  tags:
    type: list[str]
    description: "Relevant tags"
    default: []                # Prevents null/undefined issues
```

### 4. Keep System Messages Focused

```yaml
system: |
  You are a [specific role].

  Your task is to [specific task].

  Guidelines:
  - [Guideline 1]
  - [Guideline 2]
```

### 5. Use Jinja2 Only When Needed

Simple variable substitution:
```yaml
user: |
  Topic: {topic}
```

Complex iteration (use Jinja2):
```yaml
template: |
  {% for item in items %}
  - {{ item }}
  {% endfor %}
```
