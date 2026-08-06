import html
import os
from pathlib import Path
from typing import Any

import gradio as gr
import httpx

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000/api/v1",
).rstrip("/")

REQUEST_TIMEOUT = httpx.Timeout(timeout=240.0, connect=10.0)
SUPPORTED_FILE_TYPES = [".pdf", ".docx", ".txt", ".md", ".json"]

EMPTY_STATE: dict[str, Any] = {
    "access_token": "",
    "user": None,
    "conversation_id": None,
}

THEME = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="slate",
    neutral_hue="slate",
    radius_size="md",
    text_size="md",
)

CSS = r"""
:root {
    color-scheme: dark !important;
    --page: #08111f;
    --surface: #0d1728;
    --surface-raised: #132036;
    --surface-soft: #1a2940;
    --surface-hover: #22334d;
    --line: #2b3b55;
    --line-strong: #3b4f6f;
    --text: #f8fafc;
    --text-soft: #d9e3f0;
    --muted: #9fb0c7;
    --accent: #6d5dfc;
    --accent-dark: #5746ea;
    --accent-soft: rgba(109, 93, 252, .18);
    --danger: #fb7185;
    --success: #34d399;
    --warning: #fbbf24;
    --sidebar: #070d18;
    --sidebar-soft: #111b2d;
}

html,
body {
    width: 100%;
    height: 100%;
    margin: 0;
    overflow: hidden;
    background: var(--page) !important;
}

body,
.gradio-container {
    color: var(--text) !important;
    background: var(--page) !important;
}

.gradio-container {
    width: 100vw !important;
    max-width: none !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

.gradio-container,
.gradio-container * {
    box-sizing: border-box;
}

footer {
    display: none !important;
}

#auth-shell {
    width: 100vw !important;
    min-height: 100vh !important;
    padding: 32px !important;
    align-items: center !important;
    justify-content: center !important;
    background:
        radial-gradient(circle at 14% 16%, rgba(109, 93, 252, .22), transparent 28%),
        radial-gradient(circle at 84% 82%, rgba(14, 165, 233, .16), transparent 25%),
        var(--page) !important;
}

#auth-card {
    width: min(470px, calc(100vw - 40px)) !important;
    padding: 34px !important;
    border: 1px solid var(--line) !important;
    border-radius: 24px !important;
    background: rgba(19, 32, 54, .98) !important;
    box-shadow: 0 28px 80px rgba(0, 0, 0, .38) !important;
}

#auth-card h1 {
    margin: 0 0 8px !important;
    color: var(--text) !important;
    font-size: 2rem !important;
    letter-spacing: -.045em !important;
}

#auth-card label,
#auth-card span,
#auth-card p {
    color: var(--text-soft) !important;
}

#auth-card input,
#auth-card textarea {
    border-color: var(--line-strong) !important;
    background: #0b1424 !important;
    color: var(--text) !important;
}

.auth-copy {
    margin-bottom: 20px !important;
    color: var(--muted) !important;
    line-height: 1.55 !important;
}

.auth-error {
    min-height: 24px !important;
    color: #fda4af !important;
    font-size: .92rem !important;
}

#workspace {
    width: 100vw !important;
    height: 100vh !important;
    min-height: 100vh !important;
    max-height: 100vh !important;
    gap: 0 !important;
    overflow: hidden !important;
    background: var(--surface) !important;
}

#sidebar {
    width: 304px !important;
    min-width: 304px !important;
    max-width: 304px !important;
    height: 100vh !important;
    padding: 18px 16px !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    background: linear-gradient(180deg, #070d18 0%, #0a1322 100%) !important;
    border-right: 1px solid rgba(148, 163, 184, .16) !important;
}

#sidebar::-webkit-scrollbar {
    width: 6px;
}

#sidebar::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(255, 255, 255, .16);
}

.brand {
    padding: 4px 6px 12px !important;
}

.brand h2 {
    margin: 0 !important;
    color: #ffffff !important;
    font-size: 1.12rem !important;
    letter-spacing: -.025em !important;
}

.brand p {
    margin: 5px 0 0 !important;
    color: var(--muted) !important;
    font-size: .82rem !important;
}

.sidebar-heading {
    margin: 16px 4px 8px !important;
    color: #aebdd2 !important;
    font-size: .72rem !important;
    font-weight: 750 !important;
    letter-spacing: .095em !important;
    text-transform: uppercase !important;
}

#sidebar button {
    min-height: 38px !important;
    border-radius: 10px !important;
    font-weight: 650 !important;
    box-shadow: none !important;
}

#new-chat button,
#upload-button button {
    border: 1px solid rgba(255, 255, 255, .12) !important;
    background: linear-gradient(135deg, #6d5dfc, #5144e5) !important;
    color: #ffffff !important;
}

#new-chat button:hover,
#upload-button button:hover {
    background: linear-gradient(135deg, #7c6cff, #5d50ee) !important;
}

#conversation-list {
    max-height: 134px !important;
    overflow-y: auto !important;
    padding: 2px !important;
}

#conversation-list label {
    margin-bottom: 5px !important;
    padding: 9px 10px !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    background: transparent !important;
    color: #dbe4f0 !important;
}

#conversation-list label:hover {
    background: rgba(255, 255, 255, .07) !important;
}

#conversation-list label:has(input:checked) {
    border-color: rgba(129, 140, 248, .34) !important;
    background: rgba(109, 93, 252, .24) !important;
    color: #ffffff !important;
}

#document-upload {
    height: 108px !important;
    min-height: 108px !important;
    max-height: 108px !important;
    overflow: hidden !important;
    border: 1px dashed rgba(148, 163, 184, .35) !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, .045) !important;
}

#document-upload * {
    color: #d6e0ed !important;
}

#selected-documents,
#manage-document {
    margin-top: 8px !important;
}

#sidebar .form,
#sidebar .block,
#sidebar .wrap {
    border-color: rgba(148, 163, 184, .20) !important;
    background: rgba(255, 255, 255, .055) !important;
    color: #e5edf7 !important;
}

#sidebar input,
#sidebar textarea,
#sidebar select {
    color: #ffffff !important;
    background: #101a2b !important;
}

#sidebar label,
#sidebar span,
#sidebar p {
    color: #dbe4f0 !important;
}

.sidebar-actions {
    gap: 8px !important;
    margin-top: 8px !important;
}

.sidebar-actions button {
    border: 1px solid rgba(255, 255, 255, .14) !important;
    background: rgba(255, 255, 255, .07) !important;
    color: #e5edf7 !important;
}

.danger-action button {
    color: #fecdd3 !important;
}

#account-card {
    margin-top: 16px !important;
    padding: 12px 13px !important;
    border: 1px solid rgba(255, 255, 255, .10) !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, .05) !important;
}

#account-card h3 {
    margin: 0 !important;
    color: #ffffff !important;
    font-size: .92rem !important;
}

#account-card p {
    margin: 3px 0 0 !important;
    color: var(--muted) !important;
    font-size: .78rem !important;
}

#logout button {
    margin-top: 8px !important;
    border: 1px solid rgba(255, 255, 255, .14) !important;
    background: transparent !important;
    color: #dbe4f0 !important;
}

#main-panel {
    min-width: 0 !important;
    height: 100vh !important;
    padding: 0 !important;
    overflow-y: auto !important;
    background: linear-gradient(180deg, #0d1728 0%, #0b1424 100%) !important;
}

#main-panel > .gap,
#main-panel > .form,
#main-panel > .block,
#main-panel > .wrap {
    background: transparent !important;
}

#chat-header {
    min-height: 76px !important;
    padding: 0 28px !important;
    align-items: center !important;
    border-bottom: 1px solid var(--line) !important;
    background: rgba(19, 32, 54, .97) !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, .16) !important;
}

#chat-header h3 {
    margin: 0 !important;
    color: var(--text) !important;
    font-size: 1.05rem !important;
}

#chat-header p {
    margin: 3px 0 0 !important;
    color: var(--muted) !important;
    font-size: .82rem !important;
}

#chatbot,
#chatbot > div,
#chatbot .bubble-wrap,
#chatbot .chatbot,
#chatbot .messages,
#chatbot .scroll-hide {
    width: 100% !important;
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
}

#chatbot {
    color: var(--text) !important;
}

#chatbot .message,
#chatbot .message * {
    color: var(--text) !important;
}

#chatbot .message {
    max-width: 860px !important;
    border-radius: 16px !important;
    line-height: 1.62 !important;
    box-shadow: 0 10px 28px rgba(0, 0, 0, .13) !important;
}

#chatbot .message.user,
#chatbot [data-testid="user"] .message,
#chatbot .user .message {
    border: 1px solid rgba(255, 255, 255, .12) !important;
    background: linear-gradient(135deg, #6d5dfc, #5144e5) !important;
    color: #ffffff !important;
}

#chatbot .message.user *,
#chatbot [data-testid="user"] .message *,
#chatbot .user .message * {
    color: #ffffff !important;
}

#chatbot .message.bot,
#chatbot .message.assistant,
#chatbot [data-testid="bot"] .message,
#chatbot [data-testid="assistant"] .message,
#chatbot .bot .message,
#chatbot .assistant .message {
    border: 1px solid var(--line) !important;
    background: #1a2940 !important;
    color: #f8fafc !important;
}

#chatbot .message.bot *,
#chatbot .message.assistant *,
#chatbot [data-testid="bot"] .message *,
#chatbot [data-testid="assistant"] .message *,
#chatbot .bot .message *,
#chatbot .assistant .message * {
    color: #f8fafc !important;
}

#chatbot code {
    border: 1px solid #3a4d6c !important;
    background: #0b1424 !important;
    color: #e2e8f0 !important;
}

#chatbot pre {
    border: 1px solid #3a4d6c !important;
    background: #08111f !important;
    color: #e2e8f0 !important;
}

#chatbot .placeholder,
#chatbot .empty,
#chatbot [class*="placeholder"] {
    color: #c5d1df !important;
}

#sources-panel {
    margin: 0 7vw !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    background: #132036 !important;
    color: var(--text) !important;
}

#sources-panel summary,
#sources-panel span,
#sources-panel p,
#sources-panel strong {
    color: var(--text) !important;
}

#composer {
    min-height: 92px !important;
    padding: 14px 7vw 20px !important;
    align-items: end !important;
    gap: 10px !important;
    border-top: 1px solid var(--line) !important;
    background: rgba(12, 23, 40, .98) !important;
    box-shadow: 0 -10px 28px rgba(0, 0, 0, .18) !important;
}

#question-input,
#question-input > div,
#question-input .wrap,
#question-input .form {
    background: transparent !important;
}

#question-input textarea {
    min-height: 56px !important;
    max-height: 120px !important;
    padding: 15px 17px !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 16px !important;
    background: #16243a !important;
    color: #f8fafc !important;
    caret-color: #ffffff !important;
    box-shadow: 0 9px 24px rgba(0, 0, 0, .20) !important;
}

#question-input textarea::placeholder {
    color: #94a3b8 !important;
}

#question-input textarea:focus {
    border-color: #7c6cff !important;
    box-shadow: 0 0 0 3px rgba(109, 93, 252, .20) !important;
}

#send-button button {
    width: 56px !important;
    min-width: 56px !important;
    height: 56px !important;
    min-height: 56px !important;
    border: 1px solid rgba(255, 255, 255, .12) !important;
    border-radius: 16px !important;
    background: linear-gradient(135deg, #6d5dfc, #5144e5) !important;
    color: #ffffff !important;
    font-size: 1.12rem !important;
    box-shadow: 0 9px 24px rgba(0, 0, 0, .18) !important;
}

.toast-anchor {
    position: fixed !important;
    top: 18px !important;
    right: 20px !important;
    width: min(410px, calc(100vw - 40px)) !important;
    z-index: 9999 !important;
    pointer-events: none !important;
}

.toast {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 15px 17px;
    border: 1px solid var(--line-strong);
    border-radius: 15px;
    background: #17253a;
    color: var(--text);
    box-shadow: 0 22px 55px rgba(0, 0, 0, .38);
    pointer-events: auto;
}

.toast.error {
    border-left: 4px solid #fb7185;
}

.toast.success {
    border-left: 4px solid #34d399;
}

.toast.info {
    border-left: 4px solid #60a5fa;
}

.toast.working {
    border-left: 4px solid #fbbf24;
}

.toast strong {
    display: block;
    margin-bottom: 3px;
    color: #ffffff;
}

.toast span {
    color: #cbd5e1;
    font-size: .9rem;
    line-height: 1.45;
}

.toast-icon {
    flex: 0 0 auto;
    width: 24px;
    height: 24px;
    display: grid;
    place-items: center;
    color: #ffffff;
    font-weight: 800;
}

.spinner {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(255, 255, 255, .28);
    border-top-color: #fbbf24;
    border-radius: 50%;
    animation: spin .8s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

button,
input,
textarea,
select,
.gradio-container .wrap {
    transition: none !important;
}

@media (max-width: 980px) {
    #sidebar {
        width: 270px !important;
        min-width: 270px !important;
        max-width: 270px !important;
    }

    #sources-panel,
    #composer {
        margin-left: 18px !important;
        margin-right: 18px !important;
        padding-left: 18px !important;
        padding-right: 18px !important;
    }
}
"""

def empty_state() -> dict[str, Any]:
    return EMPTY_STATE.copy()


def safe_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def auth_headers(state: dict[str, Any] | None) -> dict[str, str]:
    token = safe_text((state or {}).get("access_token"))
    return {"Authorization": f"Bearer {token}"}


def toast(kind: str, title: str, message: str) -> str:
    safe_kind = kind if kind in {"success", "error", "info", "working"} else "info"
    icons = {"success": "✓", "error": "!", "info": "i"}
    icon_html = (
        '<div class="toast-icon"><div class="spinner"></div></div>'
        if safe_kind == "working"
        else f'<div class="toast-icon">{html.escape(icons[safe_kind])}</div>'
    )
    return (
        f'<div class="toast {safe_kind}">'
        f'{icon_html}<div><strong>{html.escape(title)}</strong>'
        f'<span>{html.escape(message)}</span></div></div>'
    )


def friendly_api_error(response: httpx.Response) -> str:
    defaults = {
        400: "Check the information and try again.",
        401: "Your session expired. Please log in again.",
        403: "You do not have permission to do that.",
        404: "The requested item could not be found.",
        409: "That account or document already exists.",
        413: "The selected file is too large.",
        422: "Some information is missing or invalid.",
        429: "Too many requests. Wait a moment and try again.",
        500: "Something went wrong while processing your request.",
        502: "The AI service is temporarily unavailable.",
        503: "The database, backend, or Ollama service is unavailable.",
    }

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    detail = payload.get("message") or payload.get("detail") or payload.get("error")

    if isinstance(detail, list):
        messages = []
        for item in detail:
            if not isinstance(item, dict):
                continue
            message = safe_text(item.get("msg"))
            location = item.get("loc") or []
            field = safe_text(location[-1]).replace("_", " ").title() if location else "Field"
            if message:
                messages.append(f"{field}: {message}")
        if messages:
            return " ".join(messages)

    if isinstance(detail, str):
        blocked = (
            "traceback",
            "sqlalchemy",
            "asyncpg",
            "integrityerror",
            "pendingrollback",
            "attributeerror",
            "typeerror",
            "exception in asgi",
        )
        clean = detail.strip()
        if clean and not any(word in clean.lower() for word in blocked):
            return clean

    return defaults.get(response.status_code, "The request could not be completed. Please try again.")


def backend_unavailable() -> str:
    return "Unable to reach FastAPI. Make sure the backend is running on port 8000."


def auth_mode_changed(mode: str | None):
    signup = safe_text(mode) == "Sign up"
    return (
        gr.update(visible=signup),
        gr.update(visible=signup),
        gr.update(value="Create account" if signup else "Log in"),
        "",
    )


def document_updates(documents: list[dict[str, Any]]):
    choices: list[tuple[str, str]] = []
    manage_choices: list[tuple[str, str]] = []

    for document in documents:
        filename = safe_text(document.get("filename")) or "Untitled document"
        document_id = safe_text(document.get("id"))
        status = safe_text(document.get("status") or "unknown").replace("_", " ").title()
        label = f"{filename}  ·  {status}"
        if document_id:
            choices.append((label, document_id))
            manage_choices.append((filename, document_id))

    return (
        gr.update(choices=choices, value=[value for _, value in choices]),
        gr.update(choices=manage_choices, value=None),
    )


def conversation_updates(conversations: list[dict[str, Any]], selected: str | None = None):
    choices = [
        (safe_text(item.get("title")) or "Untitled chat", safe_text(item.get("id")))
        for item in conversations
        if item.get("id")
    ]
    valid_values = {value for _, value in choices}
    value = selected if selected in valid_values else None
    return gr.update(choices=choices, value=value)


def load_documents(state: dict[str, Any] | None):
    current = state or empty_state()
    if not current.get("access_token"):
        return gr.update(choices=[], value=[]), gr.update(choices=[], value=None)

    try:
        response = httpx.get(
            f"{BACKEND_URL}/documents",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return gr.update(choices=[], value=[]), gr.update(choices=[], value=None)

    if response.status_code != 200:
        return gr.update(choices=[], value=[]), gr.update(choices=[], value=None)

    data = response.json()
    documents = data if isinstance(data, list) else []
    return document_updates(documents)


def load_conversations(state: dict[str, Any] | None):
    current = state or empty_state()
    if not current.get("access_token"):
        return gr.update(choices=[], value=None)

    try:
        response = httpx.get(
            f"{BACKEND_URL}/conversations",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return gr.update(choices=[], value=None)

    if response.status_code != 200:
        return gr.update(choices=[], value=None)

    data = response.json()
    conversations = data if isinstance(data, list) else []
    return conversation_updates(conversations, safe_text(current.get("conversation_id")) or None)


def authenticate(
    mode: str | None,
    name: str | None,
    email: str | None,
    password: str | None,
    confirmation: str | None,
):
    clean_mode = safe_text(mode) or "Log in"
    clean_name = safe_text(name)
    clean_email = safe_text(email).lower()
    clean_password = safe_text(password)
    clean_confirmation = safe_text(confirmation)

    def failure(message: str):
        return (
            empty_state(),
            gr.update(visible=True),
            gr.update(visible=False),
            message,
            "",
            "",
            gr.update(choices=[], value=None),
            gr.update(choices=[], value=[]),
            gr.update(choices=[], value=None),
        )

    if not clean_email:
        return failure("Enter your email address.")
    if not clean_password:
        return failure("Enter your password.")

    if clean_mode == "Sign up":
        if not clean_name:
            return failure("Enter your name.")
        if len(clean_password) < 8:
            return failure("Use at least 8 characters for your password.")
        if clean_password != clean_confirmation:
            return failure("The passwords do not match.")

    endpoint = "signup" if clean_mode == "Sign up" else "login"
    payload: dict[str, str] = {"email": clean_email, "password": clean_password}
    if clean_mode == "Sign up":
        payload["name"] = clean_name

    try:
        response = httpx.post(
            f"{BACKEND_URL}/auth/{endpoint}",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return failure(backend_unavailable())

    if response.status_code not in {200, 201}:
        return failure(friendly_api_error(response))

    data = response.json()
    user = data.get("user") or {}
    state = {
        "access_token": data.get("access_token", ""),
        "user": user,
        "conversation_id": None,
    }

    conversations = load_conversations(state)
    documents, manage_documents = load_documents(state)
    display_name = html.escape(safe_text(user.get("name") or user.get("email") or "User"))
    user_email = html.escape(safe_text(user.get("email")))

    return (
        state,
        gr.update(visible=False),
        gr.update(visible=True),
        "",
        f"### {display_name}\n{user_email}",
        toast("success", "Welcome", "You are signed in."),
        conversations,
        documents,
        manage_documents,
    )


def logout():
    return (
        empty_state(),
        gr.update(visible=True),
        gr.update(visible=False),
        "",
        "",
        [],
        "",
        gr.update(choices=[], value=None),
        gr.update(choices=[], value=[]),
        gr.update(choices=[], value=None),
    )


def normalize_files(files: list[Any] | Any | None) -> list[Path]:
    if not files:
        return []
    items = files if isinstance(files, list) else [files]
    paths: list[Path] = []
    for item in items:
        if isinstance(item, str):
            paths.append(Path(item))
            continue
        path_value = getattr(item, "path", None) or getattr(item, "name", None)
        if path_value:
            paths.append(Path(str(path_value)))
    return paths


def upload_documents(state: dict[str, Any] | None, files: list[Any] | Any | None):
    current = state or empty_state()
    if not current.get("access_token"):
        yield (
            gr.update(choices=[], value=[]),
            gr.update(choices=[], value=None),
            None,
            toast("error", "Session expired", "Please log in again."),
        )
        return

    paths = normalize_files(files)
    if not paths:
        documents, manage_documents = load_documents(current)
        yield (
            documents,
            manage_documents,
            None,
            toast("info", "No file selected", "Choose at least one document."),
        )
        return

    documents, manage_documents = load_documents(current)
    file_count = len(paths)
    yield (
        documents,
        manage_documents,
        gr.update(),
        toast(
            "working",
            "Processing documents",
            f"Uploading and indexing {file_count} file{'s' if file_count != 1 else ''}. This can take a moment.",
        ),
    )

    success = 0
    failures: list[str] = []

    for path in paths:
        if not path.exists():
            failures.append(f"{path.name} could not be found")
            continue
        try:
            with path.open("rb") as handle:
                response = httpx.post(
                    f"{BACKEND_URL}/documents/upload",
                    headers=auth_headers(current),
                    files={"file": (path.name, handle, "application/octet-stream")},
                    timeout=REQUEST_TIMEOUT,
                )
        except OSError:
            failures.append(f"{path.name} could not be opened")
            continue
        except httpx.HTTPError:
            failures.append(f"{path.name}: backend unavailable")
            continue

        if response.status_code in {200, 201}:
            success += 1
        else:
            failures.append(f"{path.name}: {friendly_api_error(response)}")

    documents, manage_documents = load_documents(current)
    if failures:
        message = "; ".join(failures[:3])
        title = "Upload completed with issues" if success else "Upload failed"
        kind = "info" if success else "error"
    else:
        title = "Upload complete"
        message = f"{success} document(s) are ready to use."
        kind = "success"

    yield documents, manage_documents, None, toast(kind, title, message)


def delete_document(state: dict[str, Any] | None, document_id: str | None):
    current = state or empty_state()
    clean_id = safe_text(document_id)
    if not clean_id:
        documents, manage_documents = load_documents(current)
        return documents, manage_documents, toast("info", "Choose a document", "Select a file before deleting it.")

    try:
        response = httpx.delete(
            f"{BACKEND_URL}/documents/{clean_id}",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        message = toast("error", "Delete failed", backend_unavailable())
    else:
        message = (
            toast("success", "Document deleted", "The file and its indexed content were removed.")
            if response.status_code == 204
            else toast("error", "Delete failed", friendly_api_error(response))
        )

    documents, manage_documents = load_documents(current)
    return documents, manage_documents, message


def reprocess_document(state: dict[str, Any] | None, document_id: str | None):
    current = state or empty_state()
    clean_id = safe_text(document_id)
    if not clean_id:
        documents, manage_documents = load_documents(current)
        yield (
            documents,
            manage_documents,
            toast("info", "Choose a document", "Select a file before reprocessing it."),
        )
        return

    documents, manage_documents = load_documents(current)
    yield (
        documents,
        manage_documents,
        toast(
            "working",
            "Reprocessing document",
            "Extracting text, rebuilding chunks, and refreshing embeddings.",
        ),
    )

    try:
        response = httpx.post(
            f"{BACKEND_URL}/documents/{clean_id}/reprocess",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        message = toast("error", "Reprocessing failed", backend_unavailable())
    else:
        message = (
            toast("success", "Document refreshed", "The file was extracted and indexed again.")
            if response.status_code == 200
            else toast("error", "Reprocessing failed", friendly_api_error(response))
        )

    documents, manage_documents = load_documents(current)
    yield documents, manage_documents, message


def new_chat(state: dict[str, Any] | None):
    current = state or empty_state()
    updated = {**current, "conversation_id": None}
    return (
        updated,
        gr.update(value=None),
        [],
        gr.update(visible=False),
        "",
        toast("info", "New chat", "Start with a question about your documents."),
    )


def load_conversation(state: dict[str, Any] | None, conversation_id: str | None):
    current = state or empty_state()
    clean_id = safe_text(conversation_id)
    if not clean_id:
        return current, [], gr.update(visible=False), ""

    try:
        response = httpx.get(
            f"{BACKEND_URL}/conversations/{clean_id}/messages",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return current, [], gr.update(visible=False), toast(
            "error", "Could not load chat", backend_unavailable()
        )

    if response.status_code != 200:
        return current, [], gr.update(visible=False), toast(
            "error", "Could not load chat", friendly_api_error(response)
        )

    data = response.json()
    messages = data if isinstance(data, list) else []
    history = [
        {
            "role": safe_text(item.get("role")) or "assistant",
            "content": safe_text(item.get("content")),
        }
        for item in messages
        if item.get("content")
    ]
    updated = {**current, "conversation_id": clean_id}
    return updated, history, gr.update(visible=False), ""


def delete_conversation(state: dict[str, Any] | None, conversation_id: str | None):
    current = state or empty_state()
    clean_id = safe_text(conversation_id)
    if not clean_id:
        return (
            current,
            load_conversations(current),
            [],
            gr.update(visible=False),
            toast("info", "Choose a chat", "Select a conversation before deleting it."),
        )

    try:
        response = httpx.delete(
            f"{BACKEND_URL}/conversations/{clean_id}",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return (
            current,
            load_conversations(current),
            [],
            gr.update(visible=False),
            toast("error", "Delete failed", backend_unavailable()),
        )

    if response.status_code != 204:
        return (
            current,
            load_conversations(current),
            [],
            gr.update(visible=False),
            toast("error", "Delete failed", friendly_api_error(response)),
        )

    updated = {**current, "conversation_id": None}
    return (
        updated,
        load_conversations(updated),
        [],
        gr.update(visible=False),
        toast("success", "Chat deleted", "The conversation was removed."),
    )


def format_sources(raw_sources: list[dict[str, Any]]) -> str:
    if not raw_sources:
        return '<p style="color:#9fb0c7;margin:0;">No sources were returned for this answer.</p>'

    cards: list[str] = []
    for source in raw_sources:
        filename = html.escape(safe_text(source.get("filename")) or "Document")
        page = source.get("page_number")
        chunk = source.get("chunk_index")
        location = (
            f"Page {page}"
            if page is not None
            else f"Chunk {chunk}"
            if chunk is not None
            else "Excerpt"
        )
        excerpt = safe_text(
            source.get("text_content")
            or source.get("text")
            or source.get("content")
        )
        if len(excerpt) > 360:
            excerpt = excerpt[:360].rstrip() + "…"
        try:
            score = float(source.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        score_label = f"{max(0, min(100, round(score * 100)))}% match"
        cards.append(
            '<div style="padding:13px;margin-bottom:10px;border:1px solid #2b3b55;border-radius:12px;background:#1a2940;color:#f8fafc;">'
            f'<div style="display:flex;justify-content:space-between;gap:12px;"><strong style="color:#ffffff;">{filename}</strong><span style="color:#9fb0c7;font-size:.82rem;">{score_label}</span></div>'
            f'<div style="color:#9fb0c7;font-size:.82rem;margin-top:3px;">{html.escape(location)}</div>'
            + (
                f'<p style="margin:8px 0 0;color:#d9e3f0;line-height:1.5;">{html.escape(excerpt)}</p>'
                if excerpt
                else ""
            )
            + "</div>"
        )
    return "".join(cards)


def ask_question(
    state: dict[str, Any] | None,
    question: str | None,
    selected_documents: list[str] | None,
    history: list[dict[str, str]] | None,
):
    current = state or empty_state()
    clean_question = safe_text(question)
    current_history = history or []

    if not current.get("access_token"):
        yield (
            current,
            safe_text(question),
            current_history,
            "",
            gr.update(visible=False),
            toast("error", "Session expired", "Please log in again."),
            load_conversations(current),
        )
        return

    if not clean_question:
        yield (
            current,
            "",
            current_history,
            "",
            gr.update(visible=False),
            toast("info", "Write a question", "Ask something about your uploaded documents."),
            load_conversations(current),
        )
        return

    working_history = [
        *current_history,
        {"role": "user", "content": clean_question},
        {"role": "assistant", "content": "Thinking… I am searching your selected documents."},
    ]
    yield (
        current,
        "",
        working_history,
        "",
        gr.update(visible=False),
        toast(
            "working",
            "Generating answer",
            "Searching relevant chunks and asking the model to prepare a grounded response.",
        ),
        load_conversations(current),
    )

    payload: dict[str, Any] = {"message": clean_question, "top_k": 5}
    if selected_documents:
        payload["document_ids"] = selected_documents
    if current.get("conversation_id"):
        payload["conversation_id"] = current["conversation_id"]

    try:
        response = httpx.post(
            f"{BACKEND_URL}/chat",
            headers=auth_headers(current),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        error_message = backend_unavailable()
        error_history = [
            *current_history,
            {"role": "user", "content": clean_question},
            {
                "role": "assistant",
                "content": "I could not reach the backend. Make sure FastAPI is running, then try again.",
            },
        ]
        yield (
            current,
            "",
            error_history,
            "",
            gr.update(visible=False),
            toast("error", "Could not generate an answer", error_message),
            load_conversations(current),
        )
        return

    if response.status_code != 200:
        error_message = friendly_api_error(response)
        error_history = [
            *current_history,
            {"role": "user", "content": clean_question},
            {
                "role": "assistant",
                "content": f"I could not complete that request. {error_message}",
            },
        ]
        yield (
            current,
            "",
            error_history,
            "",
            gr.update(visible=False),
            toast("error", "Could not generate an answer", error_message),
            load_conversations(current),
        )
        return

    data = response.json()
    answer = safe_text(data.get("answer")) or "No answer was generated."
    updated_history = [
        *current_history,
        {"role": "user", "content": clean_question},
        {"role": "assistant", "content": answer},
    ]
    updated = {
        **current,
        "conversation_id": safe_text(data.get("conversation_id"))
        or current.get("conversation_id"),
    }
    raw_sources = data.get("retrieved_sources") or data.get("sources") or []
    sources_html = format_sources(
        raw_sources if isinstance(raw_sources, list) else []
    )

    yield (
        updated,
        "",
        updated_history,
        sources_html,
        gr.update(visible=bool(raw_sources)),
        toast("success", "Answer ready", "The response is grounded in your selected documents."),
        load_conversations(updated),
    )


with gr.Blocks(
    title="Document Assistant",
    fill_width=True,
    fill_height=True,
) as demo:
    auth_state = gr.State(empty_state())
    toast_box = gr.HTML("", elem_classes=["toast-anchor"])

    with gr.Row(
        visible=True,
        height="100vh",
        elem_id="auth-shell",
    ) as auth_panel:
        with gr.Column(
            scale=0,
            min_width=470,
            elem_id="auth-card",
        ):
            gr.Markdown("# Document Assistant")
            gr.Markdown(
                "A private workspace for asking grounded questions about your own documents.",
                elem_classes=["auth-copy"],
            )
            auth_mode = gr.Radio(
                choices=["Log in", "Sign up"],
                value="Log in",
                label="",
                show_label=False,
                container=False,
            )
            signup_name = gr.Textbox(
                label="Name",
                placeholder="Your name",
                value="",
                visible=False,
            )
            auth_email = gr.Textbox(
                label="Email",
                placeholder="you@example.com",
                value="",
            )
            auth_password = gr.Textbox(
                label="Password",
                type="password",
                placeholder="Enter your password",
                value="",
            )
            auth_confirmation = gr.Textbox(
                label="Confirm password",
                type="password",
                placeholder="Enter your password again",
                value="",
                visible=False,
            )
            auth_button = gr.Button("Log in", variant="primary")
            auth_error = gr.Markdown("", elem_classes=["auth-error"])

    with gr.Row(
        visible=False,
        height="100vh",
        max_height="100vh",
        equal_height=True,
        elem_id="workspace",
    ) as workspace:
        with gr.Column(
            scale=0,
            min_width=304,
            elem_id="sidebar",
        ):
            gr.Markdown(
                "## Document AI\nYour private knowledge space",
                elem_classes=["brand"],
            )

            new_chat_button = gr.Button(
                "＋ New chat",
                variant="primary",
                elem_id="new-chat",
            )

            gr.Markdown("Conversations", elem_classes=["sidebar-heading"])
            conversation_list = gr.Radio(
                choices=[],
                value=None,
                label="",
                show_label=False,
                container=False,
                elem_id="conversation-list",
            )
            delete_conversation_button = gr.Button(
                "Delete selected chat",
                elem_classes=["danger-action"],
            )

            gr.Markdown("Documents", elem_classes=["sidebar-heading"])
            upload_files = gr.File(
                label="Drop files or browse",
                show_label=False,
                container=False,
                file_count="multiple",
                file_types=SUPPORTED_FILE_TYPES,
                type="filepath",
                height=108,
                elem_id="document-upload",
            )
            upload_button = gr.Button(
                "Upload documents",
                variant="primary",
                elem_id="upload-button",
            )

            gr.Markdown("Use in answers", elem_classes=["sidebar-heading"])
            selected_documents = gr.Dropdown(
                choices=[],
                value=[],
                multiselect=True,
                allow_custom_value=False,
                label="Selected documents",
                show_label=False,
                container=False,
                elem_id="selected-documents",
            )

            manage_document = gr.Dropdown(
                choices=[],
                value=None,
                label="Manage a document",
                elem_id="manage-document",
            )
            with gr.Row(elem_classes=["sidebar-actions"]):
                reprocess_document_button = gr.Button("Reprocess")
                delete_document_button = gr.Button(
                    "Delete",
                    elem_classes=["danger-action"],
                )

            account_summary = gr.Markdown("", elem_id="account-card")
            logout_button = gr.Button("Log out", elem_id="logout")

        with gr.Column(
            scale=1,
            min_width=500,
            elem_id="main-panel",
        ):
            with gr.Row(elem_id="chat-header"):
                gr.Markdown(
                    "### Chat with your documents\n"
                    "Answers are grounded in your selected files"
                )

            chatbot = gr.Chatbot(
                value=[],
                label="",
                show_label=False,
                container=False,
                height="calc(100vh - 240px)",
                min_height=420,
                max_height="calc(100vh - 240px)",
                placeholder=(
                    "Ask questions about your documents\n\n"
                    "Try: Summarize the key findings · Compare the reports · "
                    "What are the project objectives?"
                ),
                elem_id="chatbot",
            )

            with gr.Accordion(
                "Sources",
                open=False,
                visible=False,
                elem_id="sources-panel",
            ) as sources_panel:
                sources_html = gr.HTML("")

            with gr.Row(elem_id="composer"):
                question_input = gr.Textbox(
                    label="",
                    show_label=False,
                    container=False,
                    placeholder="Ask about your documents…",
                    lines=1,
                    max_lines=4,
                    value="",
                    autofocus=True,
                    scale=12,
                    elem_id="question-input",
                )
                send_button = gr.Button(
                    "➜",
                    variant="primary",
                    scale=0,
                    min_width=56,
                    elem_id="send-button",
                )

    auth_mode.change(
        auth_mode_changed,
        inputs=[auth_mode],
        outputs=[signup_name, auth_confirmation, auth_button, auth_error],
        show_progress="hidden",
    )

    auth_button.click(
        authenticate,
        inputs=[
            auth_mode,
            signup_name,
            auth_email,
            auth_password,
            auth_confirmation,
        ],
        outputs=[
            auth_state,
            auth_panel,
            workspace,
            auth_error,
            account_summary,
            toast_box,
            conversation_list,
            selected_documents,
            manage_document,
        ],
        show_progress="hidden",
    )

    logout_button.click(
        logout,
        outputs=[
            auth_state,
            auth_panel,
            workspace,
            account_summary,
            toast_box,
            chatbot,
            sources_html,
            conversation_list,
            selected_documents,
            manage_document,
        ],
        show_progress="hidden",
    )

    upload_button.click(
        upload_documents,
        inputs=[auth_state, upload_files],
        outputs=[selected_documents, manage_document, upload_files, toast_box],
        show_progress="hidden",
    )

    delete_document_button.click(
        delete_document,
        inputs=[auth_state, manage_document],
        outputs=[selected_documents, manage_document, toast_box],
        show_progress="hidden",
    )

    reprocess_document_button.click(
        reprocess_document,
        inputs=[auth_state, manage_document],
        outputs=[selected_documents, manage_document, toast_box],
        show_progress="hidden",
    )

    new_chat_button.click(
        new_chat,
        inputs=[auth_state],
        outputs=[
            auth_state,
            conversation_list,
            chatbot,
            sources_panel,
            sources_html,
            toast_box,
        ],
        show_progress="hidden",
    )

    conversation_list.change(
        load_conversation,
        inputs=[auth_state, conversation_list],
        outputs=[auth_state, chatbot, sources_panel, toast_box],
        show_progress="hidden",
    )

    delete_conversation_button.click(
        delete_conversation,
        inputs=[auth_state, conversation_list],
        outputs=[
            auth_state,
            conversation_list,
            chatbot,
            sources_panel,
            toast_box,
        ],
        show_progress="hidden",
    )

    send_button.click(
        ask_question,
        inputs=[auth_state, question_input, selected_documents, chatbot],
        outputs=[
            auth_state,
            question_input,
            chatbot,
            sources_html,
            sources_panel,
            toast_box,
            conversation_list,
        ],
        show_progress="hidden",
    )

    question_input.submit(
        ask_question,
        inputs=[auth_state, question_input, selected_documents, chatbot],
        outputs=[
            auth_state,
            question_input,
            chatbot,
            sources_html,
            sources_panel,
            toast_box,
            conversation_list,
        ],
        show_progress="hidden",
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=8).launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=False,
        inbrowser=False,
        theme=THEME,
        css=CSS,
    )