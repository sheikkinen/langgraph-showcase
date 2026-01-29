# Feature Request: URL-based Graph and Prompt Paths

**Priority:** MEDIUM  
**Type:** Feature  
**Status:** Proposed  
**Effort:** 2-3 days  
**Requested:** 2026-01-29

## Summary

Allow graphs and prompts to be loaded from URLs (GitHub raw files initially), enabling runtime prompt updates without redeploying the application.

## Problem

Currently, all graphs and prompts must be bundled with the application:

```yaml
# graph.yaml
nodes:
  ask_probe:
    type: interrupt
    prompt: prompts/probe.yaml  # Local file only
```

This means any prompt change requires:
1. Edit file locally
2. Commit and push
3. Rebuild Docker image
4. Redeploy application

For production systems, this creates friction for iterative prompt improvements and A/B testing.

## Proposed Solution

### 1. URL Support in Paths

Allow `https://` URLs in `prompt`, `graph`, and `prompts_dir` fields:

```yaml
# graph.yaml
defaults:
  prompts_dir: https://raw.githubusercontent.com/sheikkinen/questionnaire-api/main/questionnaires/interrai-ca/prompts/

nodes:
  ask_probe:
    type: interrupt
    prompt: https://raw.githubusercontent.com/sheikkinen/questionnaire-api/main/questionnaires/interrai-ca/prompts/probe.yaml
  
  run_subgraph:
    type: subgraph
    graph: https://raw.githubusercontent.com/sheikkinen/yamlgraph/main/examples/hello/graph.yaml
```

### 2. GitHub Shorthand Syntax

Support `github://` scheme for cleaner URLs:

```yaml
# Expands to: https://raw.githubusercontent.com/sheikkinen/questionnaire-api/main/prompts/probe.yaml
prompt: github://sheikkinen/questionnaire-api/main/prompts/probe.yaml

# With branch shorthand (defaults to main)
prompt: github://sheikkinen/questionnaire-api/prompts/probe.yaml
```

### 3. Caching Strategy

```python
class URLLoader:
    def __init__(
        self,
        cache_ttl: int = 300,  # 5 minutes default
        cache_dir: Path = Path(".yamlgraph_cache"),
    ):
        ...
    
    def load(self, url: str) -> str:
        """Load content from URL with caching."""
        ...
```

**Cache behavior:**
- TTL-based expiration (configurable)
- ETag/Last-Modified header support for conditional fetches
- Fallback to cached version on network errors
- Optional force-refresh via environment variable

### 4. Configuration

```yaml
# graph.yaml
config:
  url_loader:
    cache_ttl: 300        # seconds
    cache_dir: .cache/    # relative to graph
    offline_mode: false   # use cached only
    auth_token_env: GITHUB_TOKEN  # for private repos
```

Environment variables:

```bash
YAMLGRAPH_URL_CACHE_TTL=300
YAMLGRAPH_URL_CACHE_DIR=/tmp/yamlgraph
YAMLGRAPH_OFFLINE_MODE=false
GITHUB_TOKEN=ghp_xxx  # For private repos
```

### 5. CLI Support

```bash
# Force refresh all cached prompts
yamlgraph cache clear

# Show cache status
yamlgraph cache status

# Fetch and validate remote graph
yamlgraph graph validate github://sheikkinen/questionnaire-api/main/questionnaires/navigator/graph.yaml
```

### 6. Private Repository Support

```yaml
config:
  url_loader:
    auth:
      github:
        token_env: GITHUB_TOKEN
      gitlab:
        token_env: GITLAB_TOKEN
```

## Implementation

### URL Detection

```python
def is_url(path: str) -> bool:
    return path.startswith(("https://", "http://", "github://", "gitlab://"))

def resolve_github_url(path: str) -> str:
    """Convert github:// to raw.githubusercontent.com URL."""
    # github://owner/repo/branch/path → https://raw.githubusercontent.com/owner/repo/branch/path
    # github://owner/repo/path → https://raw.githubusercontent.com/owner/repo/main/path
    ...
```

### Loader Integration

Update `load_prompt()` and `load_graph_config()`:

```python
def load_prompt(path: str, base_dir: Path | None = None) -> dict:
    if is_url(path):
        content = url_loader.load(path)
        return yaml.safe_load(content)
    else:
        # Existing file-based loading
        ...
```

### New Files

```
yamlgraph/
├── utils/
│   └── url_loader.py    # URL fetching and caching
├── cli/
│   └── cache_commands.py  # cache clear/status commands
```

## Use Cases

### 1. Runtime Prompt Tuning

```yaml
# Production graph points to GitHub
nodes:
  ask_probe:
    prompt: github://company/prompts-repo/main/probe.yaml
```

Update prompt on GitHub → Changes live in 5 minutes (cache TTL).

### 2. A/B Testing

```yaml
# Feature flag determines which prompt version
nodes:
  ask_probe:
    prompt: "github://company/prompts-repo/main/probe-{{ variant }}.yaml"
```

### 3. Multi-Environment

```yaml
# Different branches for different environments
defaults:
  prompts_dir: "github://company/prompts-repo/{{ env_branch }}/"
```

### 4. Shared Prompt Library

```yaml
# Reference common prompts across projects
nodes:
  extract_fields:
    prompt: github://company/shared-prompts/main/extraction/fields.yaml
```

## Acceptance Criteria

- [ ] `https://` URLs work for `prompt`, `graph`, and `prompts_dir`
- [ ] `github://` shorthand expands to raw.githubusercontent.com
- [ ] Caching with configurable TTL
- [ ] Fallback to cache on network errors
- [ ] `GITHUB_TOKEN` support for private repos
- [ ] `yamlgraph cache clear` and `yamlgraph cache status` commands
- [ ] Offline mode via environment variable
- [ ] ETag/conditional fetch to minimize bandwidth
- [ ] Tests for URL loading, caching, and fallback
- [ ] Documentation updated

## Alternatives Considered

1. **Git submodules**: Complex to manage, requires rebuild anyway
2. **S3/GCS storage**: More infrastructure, GitHub is simpler
3. **Webhook-based invalidation**: More complex, TTL is simpler for v1
4. **Database storage**: Overkill for YAML files

## Security Considerations

- Only HTTPS URLs allowed (no HTTP)
- Token stored in environment variable, never in YAML
- Cache directory permissions should be restricted
- Consider URL allowlist for production

## Related

- Current implementation: `yamlgraph/graph_loader.py` (file-based only)
- Similar pattern: Terraform remote modules, Docker remote builds
