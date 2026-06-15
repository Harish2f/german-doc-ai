import os
import gradio as gr
import httpx

BASE_URL = os.getenv("GERMANDOCAI_URL", "http://localhost:8000")
API_KEY = os.getenv("GERMANDOCAI_API_KEY", "dev-secret-key")
HEADERS = {"x-api-key": API_KEY}

DOC_TYPES = ["bafin", "eu_ai_act", "dsgvo", "other"]

# ── Ingestion ────────────────────────────────────────────────

def ingest_url(url: str, title: str, doc_type: str) -> str:
    if not url or not title:
        return "Please provide both URL and title."
    try:
        response = httpx.post(
            f"{BASE_URL}/ingestion/",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={"url": url, "title": title, "doc_type": doc_type},
            timeout=30,
        )
        data = response.json()
        if response.status_code in (200, 201, 202):
            return f"✅ {data['message']}\nDoc ID: {data['doc_id']}"
        return f"❌ Error: {data.get('detail', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def ingest_file(file, title: str, doc_type: str) -> str:
    if file is None or not title:
        return "Please provide both file and title."
    try:
        with open(file.name, "rb") as f:
            response = httpx.post(
                f"{BASE_URL}/ingestion/upload",
                headers=HEADERS,
                data={"title": title, "doc_type": doc_type},
                files={"file": (os.path.basename(file.name), f, "application/pdf")},
                timeout=30,
            )
        data = response.json()
        if response.status_code in (200, 201, 202):
            return f"✅ {data['message']}\nDoc ID: {data['doc_id']}"
        return f"❌ Error: {data.get('detail', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error: {str(e)}"
    

def check_status(doc_id: str) -> str:
    if not doc_id:
        return "Please enter a Doc ID."
    try:
        response = httpx.get(
            f"{BASE_URL}/ingestion/{doc_id}/status",
            headers=HEADERS,
            timeout=10,
        )
        data = response.json()
        status = data.get("status", "unknown")
        message = data.get("message", "")
        chunk_count = data.get("chunk_count", 0)
        if status == "ready":
            return f"✅ {message}"
        return f"⏳ {message} (chunks indexed so far: {chunk_count})"
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ── Ask ──────────────────────────────────────────────────────

def ask_question(query: str, doc_types: list, use_agent: bool, user_id: str) -> tuple:
    if not query:
        return "Please enter a question.", ""
    try:
        endpoint = "/ask/agent" if use_agent else "/ask/"
        response = httpx.post(
            f"{BASE_URL}{endpoint}",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={
                "query": query,
                "doc_types": doc_types if doc_types else [],
                "top_k": 5,
                "user_id": user_id or "gradio-user",
            },
            timeout=60,
        )
        data = response.json()
        if response.status_code == 200:
            answer = data.get("answer", "No answer returned.")
            chunks = data.get("chunks", [])
            sources = "\n\n".join([
                f"**Chunk {i+1}** (score: {c.get('rrf_score', 0):.3f})\n{c['text'][:300]}..."
                for i, c in enumerate(chunks)
            ])
            return answer, sources
        return f"❌ Error: {data.get('detail', 'Unknown error')}", ""
    except Exception as e:
        return f"❌ Error: {str(e)}", ""


# ── Audit ────────────────────────────────────────────────────

def get_audit_trail(user_id: str) -> str:
    if not user_id:
        return "Please enter a user ID."
    try:
        response = httpx.get(
            f"{BASE_URL}/compliance/audit/{user_id}",
            headers=HEADERS,
            timeout=30,
        )
        data = response.json()
        if response.status_code == 200:
            logs = data.get("logs", [])
            if not logs:
                return f"No audit logs found for user '{user_id}'."
            output = f"**{len(logs)} queries found for user '{user_id}'**\n\n"
            for log in logs[:10]:
                output += f"---\n**Query:** {log['query_text']}\n"
                output += f"**Answer:** {log['answer'][:200]}...\n"
                output += f"**Time:** {log['created_at']}\n\n"
            return output
        return f"❌ Error: {data.get('detail', 'Unknown error')}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ── UI ───────────────────────────────────────────────────────

with gr.Blocks(title="GermanDocAI") as demo:
    gr.Markdown("""
    # 🇩🇪 GermanDocAI
    **Regulatory document intelligence for German compliance frameworks**
    
    Built with RAG, LangGraph, pgvector, and Azure OpenAI GPT-4o.
    """)

    with gr.Tab("📄 Ingest Documents"):
        gr.Markdown("### Ingest from URL")
        with gr.Row():
            url_input = gr.Textbox(label="PDF URL", placeholder="https://www.bafin.de/...")
            url_title = gr.Textbox(label="Document Title")
            url_doc_type = gr.Dropdown(choices=DOC_TYPES, value="bafin", label="Document Type")
        url_btn = gr.Button("Ingest URL", variant="primary")
        url_output = gr.Textbox(label="Result", interactive=False)
        url_btn.click(ingest_url, inputs=[url_input, url_title, url_doc_type], outputs=url_output)

        gr.Markdown("---\n### Upload PDF")
        with gr.Row():
            file_input = gr.File(label="Upload PDF", file_types=[".pdf"])
            file_title = gr.Textbox(label="Document Title")
            file_doc_type = gr.Dropdown(choices=DOC_TYPES, value="bafin", label="Document Type")
        file_btn = gr.Button("Upload and Ingest", variant="primary")
        file_output = gr.Textbox(label="Result", interactive=False)
        file_btn.click(ingest_file, inputs=[file_input, file_title, file_doc_type], outputs=file_output)

        gr.Markdown("---\n### Check Ingestion Status")
        with gr.Row():
            status_doc_id = gr.Textbox(label="Doc ID", placeholder="doc_abc123...")
        status_btn = gr.Button("Check Status")
        status_output = gr.Textbox(label="Status", interactive=False)
        status_btn.click(check_status, inputs=[status_doc_id], outputs=status_output)

    with gr.Tab("💬 Ask Questions"):
        with gr.Row():
            query_input = gr.Textbox(label="Your Question", placeholder="What are BaFin requirements for AI systems?", scale=3)
            user_id_input = gr.Textbox(label="User ID", value="gradio-user", scale=1)
        with gr.Row():
            doc_type_filter = gr.CheckboxGroup(choices=DOC_TYPES, label="Filter by Document Type (leave empty for all)")
            use_agent = gr.Checkbox(label="Use Agent (query rewriting + relevance grading)", value=True)
        ask_btn = gr.Button("Ask", variant="primary")
        answer_output = gr.Markdown(label="Answer")
        chunks_output = gr.Markdown(label="Retrieved Chunks")
        ask_btn.click(ask_question, inputs=[query_input, doc_type_filter, use_agent, user_id_input], outputs=[answer_output, chunks_output])

    with gr.Tab("🔍 Audit Trail"):
        gr.Markdown("### DSGVO Article 15 — Right of Access\nView all queries made by a user.")
        audit_user_id = gr.Textbox(label="User ID", placeholder="gradio-user")
        audit_btn = gr.Button("Get Audit Trail", variant="primary")
        audit_output = gr.Markdown(label="Audit Trail")
        audit_btn.click(get_audit_trail, inputs=[audit_user_id], outputs=audit_output)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)