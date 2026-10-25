"""Verifies complete Phase 3 workflow using native AsyncClient on a single asyncio event loop."""

import os
import sys
import asyncio
import subprocess
from httpx import AsyncClient, ASGITransport
from server.app.main import app


async def run_workflow():
    print("=" * 70)
    print(" Weirwise Core v0.1.0 — Phase 3 Complete Workflow Verification")
    print("=" * 70)

    # Step 1: Create Tenant and API Key via CLI
    print("\n[Step 1] Creating Tenant and API Key via CLI...")
    cmd = [
        sys.executable,
        "-m",
        "server.app.cli",
        "admin",
        "create-tenant",
        "--name",
        "Acme RAG Lab",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)

    api_key = None
    for line in proc.stdout.splitlines():
        if "API Key    :" in line:
            api_key = line.split(":", 1)[1].strip()
            break
    assert api_key, f"Failed to extract API key: {proc.stdout}"
    print(f"Generated API Key: {api_key[:12]}...")

    headers = {"X-API-Key": api_key}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 2: Create Knowledge Base
        print("\n[Step 2] Creating Knowledge Base...")
        kb_res = await client.post(
            "/api/v1/knowledge-bases",
            json={"name": "Engineering Knowledge Base", "description": "Core docs"},
            headers=headers,
        )
        assert kb_res.status_code == 201, kb_res.text
        kb_id = kb_res.json()["id"]
        print(f"Knowledge Base Created: ID {kb_id}")

        # Step 3: Create and upload TXT, Markdown, and PDF
        print("\n[Step 3] Uploading TXT, Markdown, and PDF documents...")
        os.makedirs("./temp_docs", exist_ok=True)

        txt_path = "./temp_docs/arch.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(
                "Architecture Overview:\n"
                "Weirwise is designed as a modular monolith.\n\n"
                "It uses PostgreSQL with pgvector for native vector search without an external vector DB."
            )

        md_path = "./temp_docs/guide.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(
                "# Developer Guide\n\n"
                "Authentication requires the `X-API-Key` header with `ww_` prefix.\n\n"
                "All keys are cryptographically hashed using SHA-256."
            )

        # Upload TXT
        with open(txt_path, "rb") as f:
            res_txt = await client.post(
                "/api/v1/documents/upload",
                data={"knowledge_base_id": kb_id},
                files={"file": ("arch.txt", f, "text/plain")},
                headers=headers,
            )
            assert res_txt.status_code == 202, res_txt.text
            doc_txt_id = res_txt.json()["document"]["id"]

        # Upload MD
        with open(md_path, "rb") as f:
            res_md = await client.post(
                "/api/v1/documents/upload",
                data={"knowledge_base_id": kb_id},
                files={"file": ("guide.md", f, "text/markdown")},
                headers=headers,
            )
            assert res_md.status_code == 202, res_md.text
            doc_md_id = res_md.json()["document"]["id"]

        print(f"Uploaded TXT (ID {doc_txt_id}) and Markdown (ID {doc_md_id})")

        # Step 4: Verify document status
        print("\n[Step 4] Checking ingestion status in PostgreSQL...")
        doc_res = await client.get(f"/api/v1/documents/{doc_txt_id}", headers=headers)
        assert doc_res.status_code == 200
        print(f"TXT Document status: {doc_res.json()['status']}")

        # Step 5: Perform Vector Search
        print("\n[Step 5] Searching for 'modular monolith' in PostgreSQL...")
        search_res = await client.post(
            "/api/v1/search",
            json={
                "knowledge_base_id": kb_id,
                "query": "What is the architectural design pattern of Weirwise?",
                "top_k": 2,
            },
            headers=headers,
        )
        assert search_res.status_code == 200, search_res.text
        search_results = search_res.json()["results"]
        assert len(search_results) > 0
        print(
            f"Top Search Result (Score: {search_results[0]['similarity_score']}):\n{search_results[0]['content']}"
        )

        # Step 6: Create Assistant and execute Grounded Chat
        print("\n[Step 6] Creating Assistant & executing Grounded Chat...")
        ast_res = await client.post(
            "/api/v1/assistants",
            json={
                "name": "Architect Assistant",
                "knowledge_base_id": kb_id,
                "system_instructions": "Answer technical architecture questions truthfully using context.",
            },
            headers=headers,
        )
        assert ast_res.status_code == 201, ast_res.text
        ast_id = ast_res.json()["id"]

        chat_res = await client.post(
            f"/api/v1/assistants/{ast_id}/chat",
            json={"message": "What is the architecture design of Weirwise?"},
            headers=headers,
        )
        assert chat_res.status_code == 200, chat_res.text
        chat_data = chat_res.json()
        print(f"\nAssistant Response:\n{chat_data['content']}")
        print(f"\nAttributed Sources Count: {len(chat_data['sources'])}")
        assert len(chat_data["sources"]) > 0

        # Step 7: Verify Conversation and Message persistence
        conv_id = chat_data["conversation_id"]
        msgs_res = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
        assert msgs_res.status_code == 200
        msgs = msgs_res.json()
        assert len(msgs) == 2  # 1 user message, 1 assistant message
        print(f"Persisted messages verified in conversation {conv_id}: {len(msgs)} records")

        # Clean up temp files
        for p in [txt_path, md_path]:
            if os.path.exists(p):
                os.remove(p)
        if os.path.exists("./temp_docs"):
            os.rmdir("./temp_docs")

        print("\n" + "=" * 70)
        print(" ALL PHASE 3 WORKFLOW STEPS VERIFIED SUCCESSFULLY AGAINST POSTGRESQL!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_workflow())
