# Weirwise Python SDK

Official Python client library for the Weirwise Core RAG infrastructure.

## Installation

```bash
pip install weirwise
```

## Quickstart

```python
from weirwise import Weirwise

client = Weirwise(base_url="http://localhost:8000", api_key="YOUR_API_KEY")

kb = client.knowledge_bases.create(name="Docs")
client.documents.upload(knowledge_base_id=kb.id, path="guide.txt")
results = client.search(knowledge_base_id=kb.id, query="How to install?")
```
