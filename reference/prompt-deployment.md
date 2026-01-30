# Prompt Deployment Patterns

This guide covers common patterns for deploying and updating prompts without rebuilding your application.

## Overview

YAMLGraph reads prompts from the filesystem at graph load time. To enable dynamic prompt updates, configure your deployment to update the filesystem externally rather than bundling prompts in the Docker image.

## Patterns

### 1. Volume Mount (Docker/Kubernetes)

Mount prompts from the host or a persistent volume.

**Docker Compose:**
```yaml
services:
  app:
    image: myapp:latest
    volumes:
      - ./prompts:/app/prompts:ro
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: app
      volumeMounts:
        - name: prompts
          mountPath: /app/prompts
          readOnly: true
  volumes:
    - name: prompts
      configMap:
        name: my-prompts
```

**Pros:** Simple, native to orchestrators, no code changes  
**Cons:** Requires deployment config change for updates

---

### 2. ConfigMap/Secret (Kubernetes)

Store prompts as ConfigMaps for easy updates via `kubectl`.

```bash
# Create ConfigMap from directory
kubectl create configmap my-prompts --from-file=prompts/

# Update a single prompt
kubectl create configmap my-prompts \
  --from-file=prompts/ \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up changes
kubectl rollout restart deployment/myapp
```

**Graph config:**
```yaml
# graph.yaml
defaults:
  prompts_dir: /app/prompts/  # Mounted from ConfigMap
```

**Pros:** GitOps-friendly, versioned in cluster  
**Cons:** Pod restart needed (unless using subPath + inotify)

---

### 3. Git-Sync Sidecar (Kubernetes)

Auto-sync prompts from a Git repository.

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: app
      volumeMounts:
        - name: prompts
          mountPath: /app/prompts
          readOnly: true
    
    - name: git-sync
      image: registry.k8s.io/git-sync/git-sync:v4.2.1
      args:
        - --repo=https://github.com/company/prompts
        - --root=/git
        - --link=current
        - --period=60s
      volumeMounts:
        - name: prompts
          mountPath: /git
  
  volumes:
    - name: prompts
      emptyDir: {}
```

**Pros:** Automatic updates, Git history preserved  
**Cons:** Additional container, slight complexity

---

### 4. S3/GCS Sync at Startup

Fetch prompts from cloud storage on application start.

```python
# In your application startup
import boto3
import os

def sync_prompts_from_s3():
    s3 = boto3.client('s3')
    bucket = os.getenv('PROMPTS_BUCKET', 'my-prompts')
    prefix = os.getenv('PROMPTS_PREFIX', 'v1/')
    
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            local_path = f"/app/prompts/{key.replace(prefix, '')}"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            s3.download_file(bucket, key, local_path)

# Call before loading graph
sync_prompts_from_s3()
graph = load_and_compile("graph.yaml")
```

**Pros:** Central storage, versioning via S3  
**Cons:** Startup latency, requires cloud SDK

---

### 5. Environment-Based Prompt Selection

Use different prompts per environment via `prompts_dir`.

```python
import os
from yamlgraph import load_and_compile

env = os.getenv('ENVIRONMENT', 'development')
prompts_dir = f"prompts/{env}/"

graph = load_and_compile("graph.yaml", prompts_dir=prompts_dir)
```

**Directory structure:**
```
prompts/
├── development/
│   └── greeting.yaml
├── staging/
│   └── greeting.yaml
└── production/
    └── greeting.yaml
```

**Pros:** Simple, no external deps  
**Cons:** All versions bundled in image

---

### 6. Runtime Override via API

Allow prompt updates via your application's API.

```python
from fastapi import FastAPI
from pathlib import Path

app = FastAPI()
PROMPTS_DIR = Path("/app/prompts")

@app.put("/admin/prompts/{name}")
async def update_prompt(name: str, content: dict):
    prompt_path = PROMPTS_DIR / f"{name}.yaml"
    prompt_path.write_text(yaml.dump(content))
    
    # Reload graph
    global graph
    graph = await load_and_compile_async("graph.yaml")
    
    return {"status": "updated", "prompt": name}
```

**Pros:** Immediate updates, no restart  
**Cons:** Requires persistent volume, security considerations

---

## Comparison

| Pattern | Update Speed | Complexity | Best For |
|---------|-------------|------------|----------|
| Volume Mount | Minutes | Low | Simple deployments |
| ConfigMap | Minutes | Low | Kubernetes native |
| Git-Sync | 1-5 min | Medium | GitOps workflows |
| S3 Sync | Restart | Medium | Cloud-native apps |
| Env Selection | Deploy | Low | Multi-env testing |
| Runtime API | Instant | High | Rapid iteration |

## Recommendations

1. **Start simple**: Volume mounts or ConfigMaps cover most cases
2. **For GitOps**: Use git-sync sidecar
3. **For rapid iteration**: Consider runtime API with auth
4. **Avoid**: Baking prompts into Docker images if you need flexibility

## Related

- [Graph YAML Reference](graph-yaml.md) - `prompts_dir` configuration
- [Prompt YAML Reference](prompt-yaml.md) - Prompt file format
- [Async Usage](async-usage.md) - Hot-reloading graphs
