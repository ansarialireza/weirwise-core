"""Basic RAG workflow example using the Weirwise Python SDK."""

import os
from weirwise import Weirwise

# 1. Initialize client
# When running locally, ensure Weirwise Core server is running at http://localhost:8000
API_KEY = os.getenv("WEIRWISE_API_KEY", "your-api-key-here")
client = Weirwise(base_url="http://localhost:8000", api_key=API_KEY)

print("[1] Creating Knowledge Base...")
kb = client.knowledge_bases.create(
    name="Company Guidelines",
    description="Internal company policies and standard operating procedures.",
)
print(f"Created Knowledge Base: {kb.name} (ID: {kb.id})")

# 2. Prepare sample document
sample_file = "guidelines.txt"
with open(sample_file, "w", encoding="utf-8") as f:
    f.write(
        "Remote Work Policy 2026:\n"
        "All engineers are eligible for flexible remote work.\n"
        "Core collaboration hours are 10:00 to 15:00 UTC.\n"
        "Home office stipends of $500 per annum are provided for ergonomic equipment."
    )

print("\n[2] Uploading Document...")
doc = client.documents.upload(knowledge_base_id=kb.id, path=sample_file)
print(f"Uploaded: {doc.filename} (ID: {doc.id}, Status: {doc.status})")

# Allow ingestion processing
print("\n[3] Waiting for document ingestion to complete...")
doc = client.documents.wait_for_completion(doc.id, timeout=30.0, poll_interval=0.5)
print(f"Document ingestion finished with status: {doc.status}")

print("\n[4] Performing Vector Similarity Search...")
results = client.search(
    knowledge_base_id=kb.id,
    query="What is the home office stipend amount?",
    top_k=2,
)
for r in results:
    print(f" - [Score: {r.similarity_score}] {r.content}")

print("\n[5] Creating AI Assistant...")
assistant = client.assistants.create(
    name="Policy Bot",
    knowledge_base_id=kb.id,
    system_instructions="You are a helpful HR assistant. Answer questions truthfully based only on company guidelines.",
)
print(f"Created Assistant: {assistant.name} (ID: {assistant.id})")

print("\n[6] Asking Question to Assistant...")
response = client.chat(
    assistant_id=assistant.id,
    message="What is the allowance for home office equipment?",
)
print(f"\nAssistant Response:\n{response.content}")
print(f"\nAttributed Sources: {len(response.sources)} retrieved chunks")

# Cleanup sample file
if os.path.exists(sample_file):
    os.remove(sample_file)
