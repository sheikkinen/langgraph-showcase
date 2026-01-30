# Feature Request: URL-based Graph and Prompt Paths

**Priority:** MEDIUM  
**Type:** Feature  
**Status:** Proposed  
**Effort:** 2 days  
**Requested:** 2026-01-29

## Summary

Allow graphs and prompts to be loaded from HTTPS URLs, enabling runtime prompt updates without redeploying.

## Problem

Currently, all graphs and prompts must be bundled with the application. Any prompt change requires rebuild and redeploy.

## Proposed Solution

### URL Support in Paths

Allow `https://` URLs in `prompt`, `graph`, and `prompts_dir` fields:

```yaml
# graph.yaml
nodes:
  ask_probe:
    type: interrupt
    prompt: https://raw.githubusercontent.com/company/prompts/main/probe.yaml
  
  run_subgraph:
    type: subgraph
    graph: https://raw.githubusercontent.com/company/graphs/main/sub.yaml
```

### Simple Caching

```python
class URLLoader:
    """Fetch URLs with TTL-based file caching."""
    
    def __init__(
        self,
        cache_ttl: int = 300,  # 5 minutes
        cache_dir: Path = Path("/tmp/yamlgraph_cache"),
        timeout: int = 10,  # seconds
        max_size: int = 1_000_000,  # 1MB
    ): ...
    
    def load(self, url: str) -> str:
        """Load content from URL, use cache if fresh."""
        ...
```

**Cache behavior:**
- TTL-based expiration (default 5 minutes)
- Fallback to stale cache on network errors
- Error if URL unreachable and no cache exists (cold start)
- File-based cache in `/tmp/yamlgraph_cache`
- Cache key: SHA256 hash of URL

### Configuration

Environment variables:

```bash
YAMLGRAPH_URL_CACHE_TTL=300       # seconds (5 minutes)
YAMLGRAPH_URL_CACHE_DIR=/tmp/yamlgraph_cache
```

## Implementation

### URL Detection

```python
def is_url(path: str) -> bool:
    return path.startswith("https://")
```

### Loader Integration

Update `load_prompt()` and `load_graph_config()`:

```python
def load_prompt(path: str, base_dir: Path | None = None) -> dict:
    if is_url(path):
        content = url_loader.load(path)
        return yaml.safe_load(content)
    # Existing file-based loading...
```

### New File

```
yamlgraph/utils/url_loader.py
```

## Constraints

- **HTTPS only** (no HTTP)
- **Max file size**: 1MB
- **Timeout**: 10 seconds
- **No Jinja2 in URLs** (static paths only)
- **Public URLs only** (private repos deferred to v2)
- **prompts_dir URLs**: Relative paths appended (e.g., `https://...prompts/` + `probe.yaml`)

## Acceptance Criteria

- [ ] `https://` URLs work for `prompt`, `graph`, and `prompts_dir`
- [ ] TTL-based caching with env var configuration
- [ ] Fallback to stale cache on network errors
- [ ] Clear error messages for timeouts, size limits, invalid YAML
- [ ] Tests for URL loading, caching, and fallback
- [ ] Logging for cache hits/misses/fetches
- [ ] Documentation updated

## Security

- HTTPS-only enforced
- Follow redirects only within same domain
- Cache directory uses restrictive permissions

## Related

- Current implementation: `yamlgraph/graph_loader.py` (file-based only)
