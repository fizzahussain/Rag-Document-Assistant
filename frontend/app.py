import os
import uuid
import gradio as gr
import httpx

# API Backend Base URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")


def get_headers():
    return {"Content-Type": "application/json"}


def upload_file_action(user_id_str: str, file):
    if not file:
        return "Please select a file to upload.", gr.update()
    if not user_id_str:
        user_id_str = str(uuid.uuid4())

    try:
        file_path = file.name if hasattr(file, "name") else file
        filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        files = {"file": (filename, file_bytes, "application/octet-stream")}
        data = {"user_id": user_id_str}

        response = httpx.post(f"{BACKEND_URL}/documents/upload", files=files, data=data, timeout=60.0)

        if response.status_code in (200, 201):
            doc = response.json()
            status_msg = f"Successfully uploaded '{doc['filename']}'. Status: {doc['status']}."
            return status_msg, refresh_documents_action(user_id_str)[0]
        else:
            err = response.json()
            return f"Upload failed: {err.get('message', response.text)}", gr.update()
    except Exception as e:
        return f"Error connecting to backend: {str(e)}", gr.update()


def refresh_documents_action(user_id_str: str):
    if not user_id_str:
        return [], []

    try:
        response = httpx.get(f"{BACKEND_URL}/documents", params={"user_id": user_id_str}, timeout=10.0)
        if response.status_code == 200:
            docs = response.json()
            table_data = []
            doc_choices = []
            for d in docs:
                table_data.append([d["id"], d["filename"], d["status"], f"{d['file_size'] / 1024:.1f} KB", d["updated_at"]])
                doc_choices.append((f"{d['filename']} ({d['status']})", d["id"]))
            return table_data, gr.update(choices=doc_choices)
        return [], gr.update(choices=[])
    except Exception:
        return [], gr.update(choices=[])


def delete_document_action(user_id_str: str, doc_id: str):
    if not doc_id:
        return "Please select a document ID to delete."
    try:
        response = httpx.delete(f"{BACKEND_URL}/documents/{doc_id}", params={"user_id": user_id_str}, timeout=10.0)
        if response.status_code in (200, 204):
            return f"Document '{doc_id}' deleted successfully."
        return f"Delete failed: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"


def chat_action(user_id_str: str, message: str, history, selected_docs, conversation_id_str: str):
    if not message.strip():
        return history, "", "", conversation_id_str

    if not user_id_str:
        user_id_str = str(uuid.uuid4())

    doc_ids = selected_docs if selected_docs else None

    payload = {
        "user_id": user_id_str,
        "message": message,
        "document_ids": doc_ids,
        "top_k": 5,
    }
    if conversation_id_str:
        payload["conversation_id"] = conversation_id_str

    try:
        response = httpx.post(f"{BACKEND_URL}/chat", json=payload, headers=get_headers(), timeout=60.0)
        if response.status_code == 200:
            res = response.json()
            conv_id = res["conversation_id"]
            answer = res["answer"]
            sources = res.get("retrieved_sources", [])

            # Format source citations display
            source_text_list = []
            for s in sources:
                page_info = f"page {s['page_number']}" if s.get("page_number") else f"chunk {s.get('chunk_index', 0)}"
                source_text_list.append(f"**[{s['filename']} - {page_info}]** (Score: {s['score']:.3f})\n> {s['text']}")
            
            sources_formatted = "\n\n---\n\n".join(source_text_list) if source_text_list else "No relevant context sources retrieved."

            history.append((message, answer))
            return history, "", sources_formatted, conv_id
        else:
            err = response.json()
            err_msg = err.get("message", response.text)
            history.append((message, f"Error: {err_msg}"))
            return history, "", "Error generating answer.", conversation_id_str
    except Exception as e:
        history.append((message, f"Connection error: {str(e)}"))
        return history, "", f"Failed to reach backend: {str(e)}", conversation_id_str


def build_ui():
    with gr.Blocks(title="Enterprise RAG Dashboard") as demo:
        gr.Markdown(
            """
            # Enterprise Document Ingestion & RAG System
            Upload files, manage documents, execute semantic search, and ask questions with document citations.
            """
        )

        with gr.Row():
            user_id_input = gr.Textbox(
                label="User ID (UUID)",
                value=str(uuid.uuid4()),
                interactive=True,
                scale=3,
            )
            refresh_btn = gr.Button("Refresh Dashboard", variant="secondary", scale=1)

        conversation_id_state = gr.State(value="")

        with gr.Tabs():
            with gr.TabItem("Upload & Ingestion"):
                with gr.Row():
                    file_input = gr.File(
                        label="Select Document (PDF, DOCX, TXT, MD, CSV, HTML, JSON)",
                        file_types=[".pdf", ".docx", ".txt", ".md", ".csv", ".html", ".json"],
                    )
                    upload_btn = gr.Button("Upload & Ingest", variant="primary")

                upload_status_output = gr.Markdown(label="Upload Log")

                gr.Markdown("### Uploaded Documents")
                doc_table = gr.Dataframe(
                    headers=["ID", "Filename", "Status", "Size", "Updated At"],
                    datatype=["str", "str", "str", "str", "str"],
                    interactive=False,
                )

                with gr.Row():
                    delete_doc_id_input = gr.Textbox(label="Document ID to Delete", placeholder="Paste Document UUID")
                    delete_doc_btn = gr.Button("Delete Document", variant="stop")
                delete_status_output = gr.Markdown()

            with gr.TabItem("RAG Chat & Assistant"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(label="Conversation", height=500)
                        msg_input = gr.Textbox(
                            label="Ask a question about your documents...",
                            placeholder="e.g. What are the key findings in the report?",
                            lines=2,
                        )
                        with gr.Row():
                            send_btn = gr.Button("Send Question", variant="primary")
                            clear_chat_btn = gr.Button("Clear Session")

                    with gr.Column(scale=2):
                        selected_docs_checkbox = gr.CheckboxGroup(
                            label="Filter Search by Documents (Optional)",
                            choices=[],
                        )
                        sources_output = gr.Markdown(label="Retrieved Context & Citations")

        # Callbacks
        upload_btn.click(
            fn=upload_file_action,
            inputs=[user_id_input, file_input],
            outputs=[upload_status_output, doc_table],
        )

        refresh_btn.click(
            fn=refresh_documents_action,
            inputs=[user_id_input],
            outputs=[doc_table, selected_docs_checkbox],
        )

        delete_doc_btn.click(
            fn=delete_document_action,
            inputs=[user_id_input, delete_doc_id_input],
            outputs=[delete_status_output],
        )

        send_btn.click(
            fn=chat_action,
            inputs=[user_id_input, msg_input, chatbot, selected_docs_checkbox, conversation_id_state],
            outputs=[chatbot, msg_input, sources_output, conversation_id_state],
        )

        clear_chat_btn.click(
            fn=lambda: ([], "", "", str(uuid.uuid4())),
            outputs=[chatbot, msg_input, sources_output, conversation_id_state],
        )

    return demo


if __name__ == "__main__":
    theme = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="slate",
    )
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860, theme=theme)
