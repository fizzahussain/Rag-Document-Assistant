import html
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr
import httpx

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:8000/api/v1",
).rstrip("/")

ACCESS_TOKEN = os.getenv("RAG_ACCESS_TOKEN", "")
TIMEOUT = httpx.Timeout(60.0, connect=10.0)

SUPPORTED_FILE_TYPES = [
    ".pdf",
    ".docx",
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".html",
    ".htm",
    ".json",
]

CSS = """
:root {
    color-scheme: dark;
    --bg: #100e0b;
    --sidebar: #0d0c0a;
    --surface: #15120f;
    --surface-2: #1b1712;
    --text: #f5efe5;
    --muted: #aaa094;
    --faint: #6f675e;
    --line: #2a251f;
    --line-strong: #3a332a;
    --accent: #d59a18;
    --accent-soft: rgba(213, 154, 24, 0.13);
    --success: #72c49a;
    --danger: #e07c6d;
}

html,
body {
    background: var(--bg) !important;
}

.gradio-container {
    max-width: none !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    color: var(--text) !important;
    background: var(--bg) !important;
}

.gradio-container * {
    box-sizing: border-box;
}

footer {
    display: none !important;
}

#shell {
    gap: 0 !important;
    min-height: 100vh;
    align-items: stretch;
}

#sidebar {
    min-height: 100vh;
    padding: 0 !important;
    background: var(--sidebar) !important;
    border-right: 1px solid var(--line) !important;
}

#main {
    min-height: 100vh;
    padding: 0 !important;
    background: var(--bg) !important;
}

.sidebar-header {
    padding: 18px 18px 16px;
    border-bottom: 1px solid var(--line);
}

.brand-row {
    display: flex;
    align-items: center;
    gap: 11px;
}

.brand-mark {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    color: var(--accent);
    background: var(--accent-soft);
    border: 1px solid rgba(213, 154, 24, 0.28);
    border-radius: 9px;
}

.brand-title {
    margin: 0;
    color: var(--text) !important;
    font-size: 1rem;
    font-weight: 800;
}

.brand-copy {
    margin: 2px 0 0;
    color: var(--muted) !important;
    font-size: 0.76rem;
}

.sidebar-content {
    padding: 16px 10px;
}

.section-label {
    padding: 0 8px 8px;
    color: #b9ad9d;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.library-summary {
    padding: 0 8px 12px;
    color: var(--text);
    font-size: 0.84rem;
    font-weight: 700;
}

.status-line {
    display: flex;
    align-items: center;
    gap: 7px;
    min-height: 18px;
    color: var(--muted);
    font-size: 0.75rem;
    line-height: 1.4;
}

.status-line::before {
    content: "";
    width: 7px;
    height: 7px;
    flex: 0 0 auto;
    background: var(--faint);
    border-radius: 999px;
}

.status-line.success::before {
    background: var(--success);
}

.status-line.error::before {
    background: var(--danger);
}

.status-line.warning::before {
    background: var(--accent);
}

#token-input input {
    min-height: 38px !important;
    font-size: 0.8rem !important;
}

#document-picker > label {
    display: none !important;
}

#document-picker .wrap {
    gap: 7px !important;
    background: transparent !important;
    border: 0 !important;
}

#document-picker .wrap label {
    width: 100% !important;
    margin: 0 !important;
    padding: 11px 12px !important;
    color: var(--text) !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
}

#document-picker .wrap label:hover {
    background: var(--surface) !important;
}

#document-picker .wrap label:has(input:checked) {
    background: var(--accent-soft) !important;
    border-color: rgba(213, 154, 24, 0.4) !important;
}

#document-picker input {
    accent-color: var(--accent) !important;
}

#document-picker span {
    color: var(--text) !important;
    font-size: 0.84rem !important;
}

.upload-panel {
    margin-top: 16px;
    padding: 12px;
    background: var(--surface);
    border: 1px dashed var(--line-strong);
    border-radius: 12px;
}

.upload-title {
    color: var(--text);
    font-size: 0.84rem;
    font-weight: 760;
}

.upload-copy {
    margin: 4px 0 10px;
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.4;
}

#file-upload {
    min-height: 88px !important;
    background: var(--surface-2) !important;
    border: 1px dashed var(--line-strong) !important;
    border-radius: 10px !important;
}

#file-upload * {
    color: var(--muted) !important;
}

.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 58px;
    padding: 0 22px;
    border-bottom: 1px solid var(--line);
}

.topbar-title {
    color: var(--text);
    font-size: 0.93rem;
    font-weight: 720;
}

.topbar-badge {
    padding: 7px 10px;
    color: var(--muted);
    border: 1px solid var(--line);
    border-radius: 999px;
    font-size: 0.72rem;
}

.hero {
    padding: 54px 24px 16px;
    text-align: center;
}

.hero-icon {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    margin: 0 auto 16px;
    color: var(--accent);
    background: var(--accent-soft);
    border: 1px solid rgba(213, 154, 24, 0.28);
    border-radius: 12px;
}

.hero-title {
    margin: 0;
    color: var(--text) !important;
    font-size: 1.55rem;
    font-weight: 780;
    letter-spacing: -0.03em;
}

.hero-copy {
    max-width: 560px;
    margin: 10px auto 0;
    color: var(--muted) !important;
    font-size: 0.9rem;
    line-height: 1.65;
}

#chatbot {
    min-height: 500px !important;
    max-height: calc(100vh - 315px) !important;
    margin: 0 !important;
    padding: 22px max(24px, calc((100vw - 900px) / 2)) !important;
    color: var(--text) !important;
    background: var(--bg) !important;
    border: 0 !important;
    overflow: auto !important;
}

#chatbot * {
    color: var(--text) !important;
}

#chatbot .message,
#chatbot .message-content {
    color: var(--text) !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

#chatbot .user .message,
#chatbot .user-message .message {
    padding: 12px 14px !important;
    background: var(--surface-2) !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
}

.composer {
    padding: 14px max(22px, calc((100vw - 900px) / 2)) 18px;
    background: var(--bg);
    border-top: 1px solid var(--line);
}

#message-box textarea {
    min-height: 92px !important;
    padding: 14px !important;
    color: var(--text) !important;
    background: var(--surface) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 12px !important;
}

#message-box textarea:focus {
    border-color: rgba(213, 154, 24, 0.72) !important;
    box-shadow: 0 0 0 3px rgba(213, 154, 24, 0.08) !important;
}

#message-box textarea::placeholder {
    color: var(--faint) !important;
}

.gradio-container button {
    min-height: 40px !important;
    border-radius: 10px !important;
    font-size: 0.82rem !important;
    font-weight: 720 !important;
}

.gradio-container button.primary,
.primary-action button {
    color: #171108 !important;
    background: var(--accent) !important;
    border: 0 !important;
}

.secondary-action button {
    color: var(--muted) !important;
    background: transparent !important;
    border: 1px solid var(--line) !important;
}

.danger-action button {
    color: var(--danger) !important;
    background: transparent !important;
    border: 1px solid rgba(224, 124, 109, 0.3) !important;
}

.gradio-container input,
.gradio-container textarea,
.gradio-container select {
    color: var(--text) !important;
    background: var(--surface) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 10px !important;
}

.gradio-container label,
.gradio-container label span,
.gradio-container .info,
.gradio-container .description {
    color: var(--muted) !important;
}

.gradio-container .accordion,
.gradio-container .accordion summary {
    color: var(--text) !important;
    background: transparent !important;
    border-color: var(--line) !important;
}

#sources-box {
    max-height: 300px;
    overflow: auto;
}

.source-item {
    margin-bottom: 9px;
    padding: 12px 13px;
    color: var(--text);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 10px;
}

.source-title {
    color: var(--text);
    font-weight: 760;
}

.source-meta {
    margin: 3px 0 7px;
    color: var(--faint);
    font-size: 0.72rem;
}

.source-text {
    color: #c7bcae;
    font-size: 0.8rem;
    line-height: 1.5;
    white-space: pre-wrap;
}

@media (max-width: 900px) {
    #shell {
        display: block !important;
    }

    #sidebar {
        min-height: auto;
        border-right: 0 !important;
        border-bottom: 1px solid var(--line) !important;
    }

    #chatbot {
        min-height: 430px !important;
        max-height: none !important;
        padding: 18px !important;
    }

    .composer {
        padding: 12px 16px 18px;
    }
}
"""


def request_headers(token: str) -> dict[str, str]:
    """Build bearer-token headers"""

    return {"Authorization": f"Bearer {token.strip()}"}


def api_error(response: httpx.Response) -> str:
    """Extract a useful API error message"""

    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or "The server returned an unreadable response."

    if isinstance(payload, dict):
        detail = payload.get("message") or payload.get("detail")

        if isinstance(detail, list):
            return "; ".join(
                str(item.get("msg", item)) if isinstance(item, dict) else str(item)
                for item in detail
            )

        if detail:
            return str(detail)

    return response.text.strip() or "The request could not be completed."


def notice(kind: str, title: str, message: str) -> str:
    """Render a compact status line"""

    return (
        f'<div class="status-line {html.escape(kind)}">'
        f"{html.escape(title)} · {html.escape(message)}"
        "</div>"
    )


def format_datetime(value: str | None) -> str:
    """Render an API timestamp"""

    if not value:
        return "—"

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value

    return parsed.astimezone().strftime("%d %b %Y · %H:%M")


def format_file_size(size: int | float | None) -> str:
    """Render a readable file size"""

    if size is None:
        return "—"

    value = float(size)

    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"

        value /= 1024

    return f"{value:.1f} GB"


def document_outputs(
    documents: list[dict[str, Any]],
) -> tuple[list[list[str]], Any, Any, str]:
    """Build document UI outputs"""

    rows: list[list[str]] = []
    choices: list[tuple[str, str]] = []
    ready_count = 0
    processing_count = 0

    for item in documents:
        status = str(item.get("status", "unknown"))
        filename = str(item.get("filename", "Untitled document"))
        document_id = str(item.get("id", ""))

        if status.lower() == "ready":
            ready_count += 1
        elif status.lower() in {"pending", "processing", "uploaded"}:
            processing_count += 1

        rows.append(
            [
                filename,
                status.title(),
                format_file_size(item.get("file_size")),
                format_datetime(item.get("updated_at")),
            ]
        )
        choices.append((f"{filename} · {status.title()}", document_id))

    stats = (
        '<div class="metric-row">'
        f'<div class="metric"><div class="metric-value">{len(documents)}</div>'
        '<div class="metric-label">Documents</div></div>'
        f'<div class="metric"><div class="metric-value">{ready_count}</div>'
        '<div class="metric-label">Ready</div></div>'
        f'<div class="metric"><div class="metric-value">{processing_count}</div>'
        '<div class="metric-label">Processing</div></div>'
        "</div>"
    )

    return (
        rows,
        gr.update(choices=choices, value=[]),
        gr.update(choices=choices, value=None),
        stats,
    )


def load_documents(
    token: str,
) -> tuple[list[list[str]], Any, Any, str, str]:
    """Load authenticated documents"""

    if not token.strip():
        empty = document_outputs([])
        return (
            *empty,
            notice(
                "warning",
                "Token required",
                "Paste your access token before loading documents.",
            ),
        )

    try:
        response = httpx.get(
            f"{BACKEND_URL}/documents",
            headers=request_headers(token),
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        empty = document_outputs([])
        return (
            *empty,
            notice("error", "Backend unavailable", str(exc)),
        )

    if response.status_code != 200:
        empty = document_outputs([])
        return (
            *empty,
            notice("error", "Could not load documents", api_error(response)),
        )

    documents = response.json()

    if not isinstance(documents, list):
        empty = document_outputs([])
        return (
            *empty,
            notice(
                "error",
                "Unexpected response",
                "The backend returned an invalid document list.",
            ),
        )

    outputs = document_outputs(documents)

    return (
        *outputs,
        notice(
            "success" if documents else "info",
            "Documents loaded" if documents else "No documents yet",
            (
                f"{len(documents)} document{'' if len(documents) == 1 else 's'} available."
                if documents
                else "Upload your first document to begin."
            ),
        ),
    )


def upload_file_action(
    token: str,
    file_path: str | None,
) -> tuple[str, list[list[str]], Any, Any, str]:
    """Upload a document"""

    if not token.strip():
        rows, selected, delete_choice, stats = document_outputs([])
        return (
            notice("warning", "Token required", "Paste your access token first."),
            rows,
            selected,
            delete_choice,
            stats,
        )

    if not file_path:
        rows, selected, delete_choice, stats, _ = load_documents(token)
        return (
            notice("warning", "Choose a file", "Select a supported document."),
            rows,
            selected,
            delete_choice,
            stats,
        )

    path = Path(file_path)

    try:
        with path.open("rb") as file_handle:
            response = httpx.post(
                f"{BACKEND_URL}/documents/upload",
                files={"file": (path.name, file_handle)},
                headers=request_headers(token),
                timeout=TIMEOUT,
            )
    except (OSError, httpx.HTTPError) as exc:
        rows, selected, delete_choice, stats, _ = load_documents(token)
        return (
            notice("error", "Upload failed", str(exc)),
            rows,
            selected,
            delete_choice,
            stats,
        )

    rows, selected, delete_choice, stats, _ = load_documents(token)

    if response.status_code != 201:
        return (
            notice("error", "Upload failed", api_error(response)),
            rows,
            selected,
            delete_choice,
            stats,
        )

    document = response.json()

    return (
        notice(
            "success",
            "Upload complete",
            (f"{document.get('filename', path.name)} is {document.get('status', 'processing')}."),
        ),
        rows,
        selected,
        delete_choice,
        stats,
    )


def delete_document_action(
    token: str,
    document_id: str | None,
    confirmed: bool,
) -> tuple[str, list[list[str]], Any, Any, str, bool]:
    """Delete a selected document"""

    rows, selected, delete_choice, stats, _ = load_documents(token)

    if not token.strip():
        return (
            notice("warning", "Token required", "Connect the workspace first."),
            rows,
            selected,
            delete_choice,
            stats,
            False,
        )

    if not document_id:
        return (
            notice("warning", "Choose a document", "Select a document to delete."),
            rows,
            selected,
            delete_choice,
            stats,
            False,
        )

    if not confirmed:
        return (
            notice(
                "warning",
                "Confirmation required",
                "Tick the confirmation box before deleting.",
            ),
            rows,
            selected,
            delete_choice,
            stats,
            False,
        )

    try:
        response = httpx.delete(
            f"{BACKEND_URL}/documents/{document_id}",
            headers=request_headers(token),
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        return (
            notice("error", "Delete failed", str(exc)),
            rows,
            selected,
            delete_choice,
            stats,
            False,
        )

    rows, selected, delete_choice, stats, _ = load_documents(token)

    if response.status_code == 204:
        return (
            notice(
                "success",
                "Document deleted",
                "The document and indexed content were removed.",
            ),
            rows,
            selected,
            delete_choice,
            stats,
            False,
        )

    return (
        notice("error", "Delete failed", api_error(response)),
        rows,
        selected,
        delete_choice,
        stats,
        False,
    )


def render_sources(sources: list[dict[str, Any]]) -> str:
    """Render compact source items"""

    if not sources:
        return notice(
            "info",
            "No sources yet",
            "Sources used by the assistant will appear here.",
        )

    items: list[str] = []

    for source in sources:
        page_number = source.get("page_number")
        chunk_index = source.get("chunk_index")
        location = f"Page {page_number}" if page_number is not None else f"Chunk {chunk_index}"

        filename = html.escape(str(source.get("filename", "Untitled")))
        score = source.get("score")
        score_text = f"{float(score):.3f}" if score is not None else "—"
        source_text = html.escape(str(source.get("text", "")))

        items.append(
            '<article class="source-item">'
            f'<div class="source-title">{filename}</div>'
            f'<div class="source-meta">{location} · relevance {score_text}</div>'
            f'<div class="source-text">{source_text}</div>'
            "</article>"
        )

    return "".join(items)


def chat_action(
    token: str,
    message: str,
    history: list[dict[str, str]] | None,
    selected_documents: list[str] | None,
    conversation_id: str,
) -> tuple[list[dict[str, str]], str, str, str, str]:
    """Send a grounded question"""

    history = list(history or [])

    if not token.strip():
        return (
            history,
            message,
            notice(
                "warning",
                "Token required",
                "Paste your access token before asking a question.",
            ),
            conversation_id,
            notice("warning", "Not connected", "The request was not sent."),
        )

    clean_message = message.strip()

    if not clean_message:
        return (
            history,
            "",
            notice("info", "No sources yet", "Ask a question first."),
            conversation_id,
            notice("warning", "Question required", "The message box is empty."),
        )

    payload: dict[str, Any] = {
        "message": clean_message,
        "top_k": 3,
        "document_ids": selected_documents or None,
    }

    if conversation_id:
        payload["conversation_id"] = conversation_id

    history.append({"role": "user", "content": clean_message})

    try:
        response = httpx.post(
            f"{BACKEND_URL}/chat",
            json=payload,
            headers=request_headers(token),
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        history.append(
            {
                "role": "assistant",
                "content": (
                    "I could not reach the backend. Check that the API server is still running."
                ),
            }
        )
        return (
            history,
            "",
            notice("error", "No sources retrieved", str(exc)),
            conversation_id,
            notice("error", "Connection failed", str(exc)),
        )

    if response.status_code != 200:
        error_message = api_error(response)
        history.append(
            {
                "role": "assistant",
                "content": f"I could not complete that request: {error_message}",
            }
        )
        return (
            history,
            "",
            notice("error", "No sources retrieved", error_message),
            conversation_id,
            notice("error", "Question failed", error_message),
        )

    data = response.json()
    answer = str(data.get("answer", "No answer was returned."))

    history.append({"role": "assistant", "content": answer})

    sources = data.get("retrieved_sources", [])

    return (
        history,
        "",
        render_sources(sources if isinstance(sources, list) else []),
        str(data.get("conversation_id", conversation_id)),
        notice(
            "success",
            "Answer ready",
            "The response was generated from your document context.",
        ),
    )


def clear_conversation() -> tuple[list[dict[str, str]], str, str, str]:
    """Clear the visible conversation"""

    return (
        [],
        "",
        notice(
            "info",
            "No sources yet",
            "Sources used by the assistant will appear here.",
        ),
        notice("info", "Chat cleared", "Start a new question whenever you are ready."),
    )


def build_ui() -> gr.Blocks:
    """Build a focused document chat workspace"""

    theme = gr.themes.Base(
        primary_hue="amber",
        secondary_hue="stone",
        neutral_hue="stone",
        radius_size="md",
        spacing_size="sm",
        text_size="md",
    )

    with gr.Blocks(
        title="Corpus",
        theme=theme,
        css=CSS,
    ) as demo:
        conversation_state = gr.State("")

        with gr.Row(elem_id="shell"):
            with gr.Column(scale=2, min_width=300, elem_id="sidebar"):
                gr.HTML(
                    """
                    <div class="sidebar-header">
                        <div class="brand-row">
                            <div class="brand-mark">◈</div>
                            <div>
                                <h1 class="brand-title">Corpus</h1>
                                <p class="brand-copy">
                                    Grounded answers over your documents
                                </p>
                            </div>
                        </div>
                    </div>
                    <div class="sidebar-content">
                        <div class="section-label">Library</div>
                    """
                )

                library_stats = gr.HTML('<div class="library-summary">0 documents · 0 ready</div>')

                token_input = gr.Textbox(
                    label="Access token",
                    value=ACCESS_TOKEN,
                    type="password",
                    placeholder="Paste token",
                    elem_id="token-input",
                )

                refresh_button = gr.Button(
                    "Load documents",
                    elem_classes=["secondary-action"],
                )

                workspace_status = gr.HTML(
                    notice(
                        "warning",
                        "Not connected",
                        "Paste your token",
                    )
                )

                selected_documents = gr.CheckboxGroup(
                    label="Documents",
                    choices=[],
                    info="Leave empty to search every ready document.",
                    elem_id="document-picker",
                )

                gr.HTML(
                    """
                    <div class="upload-panel">
                        <div class="upload-title">Add a document</div>
                        <div class="upload-copy">
                            PDF, DOCX, TXT, MD, CSV, HTML, and JSON
                        </div>
                    """
                )

                file_input = gr.File(
                    label="Drop or choose a file",
                    type="filepath",
                    file_types=SUPPORTED_FILE_TYPES,
                    elem_id="file-upload",
                )

                upload_button = gr.Button(
                    "Upload",
                    variant="primary",
                    elem_classes=["primary-action"],
                )

                upload_status = gr.HTML(
                    notice(
                        "info",
                        "Upload",
                        "Waiting for a file",
                    )
                )

                with gr.Accordion("Manage library", open=False):
                    document_table = gr.Dataframe(
                        headers=["Document", "Status", "Size", "Updated"],
                        datatype=["str", "str", "str", "str"],
                        value=[],
                        interactive=False,
                        wrap=True,
                        max_height=220,
                    )

                    delete_document = gr.Dropdown(
                        label="Delete document",
                        choices=[],
                        value=None,
                    )

                    delete_confirm = gr.Checkbox(label="I understand this cannot be undone")

                    delete_button = gr.Button(
                        "Delete selected",
                        elem_classes=["danger-action"],
                    )

                    delete_status = gr.HTML(
                        notice(
                            "info",
                            "Delete",
                            "Nothing selected",
                        )
                    )

                gr.HTML("</div></div>")

            with gr.Column(scale=8, min_width=650, elem_id="main"):
                gr.HTML(
                    """
                    <div class="topbar">
                        <div class="topbar-title">Ask your documents</div>
                        <div class="topbar-badge">Grounded answers</div>
                    </div>
                    <div class="hero">
                        <div class="hero-icon">◈</div>
                        <h2 class="hero-title">Ask the corpus anything</h2>
                        <p class="hero-copy">
                            Answers are generated from passages retrieved from your
                            indexed documents. Select files on the left to narrow the search.
                        </p>
                    </div>
                    """
                )

                chatbot = gr.Chatbot(
                    value=[],
                    elem_id="chatbot",
                    height=540,
                )

                with gr.Column(elem_classes=["composer"]):
                    message = gr.Textbox(
                        label=None,
                        placeholder="Ask a question about your documents...",
                        lines=3,
                        elem_id="message-box",
                    )

                    with gr.Row():
                        send_button = gr.Button(
                            "Ask",
                            variant="primary",
                            elem_classes=["primary-action"],
                        )

                        clear_button = gr.Button(
                            "New conversation",
                            elem_classes=["secondary-action"],
                        )

                    chat_status = gr.HTML(
                        notice(
                            "info",
                            "Ready",
                            "Ask a question when your documents are indexed",
                        )
                    )

                    with gr.Accordion("Sources used", open=False):
                        sources = gr.HTML(
                            notice(
                                "info",
                                "Sources",
                                "No sources yet",
                            ),
                            elem_id="sources-box",
                        )

        refresh_button.click(
            load_documents,
            inputs=[token_input],
            outputs=[
                document_table,
                selected_documents,
                delete_document,
                library_stats,
                workspace_status,
            ],
        )

        upload_button.click(
            upload_file_action,
            inputs=[token_input, file_input],
            outputs=[
                upload_status,
                document_table,
                selected_documents,
                delete_document,
                library_stats,
            ],
        )

        delete_button.click(
            delete_document_action,
            inputs=[token_input, delete_document, delete_confirm],
            outputs=[
                delete_status,
                document_table,
                selected_documents,
                delete_document,
                library_stats,
                delete_confirm,
            ],
        )

        send_button.click(
            chat_action,
            inputs=[
                token_input,
                message,
                chatbot,
                selected_documents,
                conversation_state,
            ],
            outputs=[
                chatbot,
                message,
                sources,
                conversation_state,
                chat_status,
            ],
        )

        message.submit(
            chat_action,
            inputs=[
                token_input,
                message,
                chatbot,
                selected_documents,
                conversation_state,
            ],
            outputs=[
                chatbot,
                message,
                sources,
                conversation_state,
                chat_status,
            ],
        )

        clear_button.click(
            clear_conversation,
            outputs=[
                chatbot,
                conversation_state,
                sources,
                chat_status,
            ],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(
        server_name="0.0.0.0",
        server_port=7860,
    )
