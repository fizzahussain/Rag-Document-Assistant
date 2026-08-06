import html
import os
from datetime import datetime, timezone
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
READY_STATUSES = {"ready", "completed", "indexed", "processed"}
PROCESSING_STATUSES = {"processing", "pending", "queued", "uploading", "indexing"}

EMPTY_STATE: dict[str, Any] = {
    "access_token": "",
    "user": None,
    "conversation_id": None,
}

THEME = gr.themes.Soft(
    primary_hue="red",
    secondary_hue="stone",
    neutral_hue="stone",
    radius_size="md",
    text_size="md",
)

CSS = r"""
:root {
    color-scheme: dark !important;
    --camel: #c6b39a;
    --boho: #7b694e;
    --rubine: #8d3a3c;
    --rubine-light: #ad5658;
    --tamarind: #3b1319;
    --italian-roast: #280b0f;
    --page: #1f080b;
    --surface: #280b0f;
    --surface-raised: #351117;
    --surface-soft: #421820;
    --surface-hover: #51212a;
    --line: #67333a;
    --line-soft: rgba(198, 179, 154, .18);
    --text: #f7ecdf;
    --text-soft: #ead9c7;
    --muted: #c6b39a;
    --muted-deep: #a79379;
    --accent: #8d3a3c;
    --accent-dark: #6f292d;
    --accent-soft: rgba(141, 58, 60, .24);
    --danger: #e48784;
    --success: #b8c59a;
    --warning: #d8b579;
    --sidebar: #21080c;
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
        radial-gradient(circle at 15% 18%, rgba(141, 58, 60, .30), transparent 30%),
        radial-gradient(circle at 84% 80%, rgba(123, 105, 78, .20), transparent 27%),
        linear-gradient(145deg, #1d070a 0%, #280b0f 52%, #321017 100%) !important;
}

#auth-card {
    width: min(470px, calc(100vw - 40px)) !important;
    padding: 34px !important;
    border: 1px solid rgba(198, 179, 154, .26) !important;
    border-radius: 24px !important;
    background: rgba(59, 19, 25, .96) !important;
    box-shadow: 0 30px 85px rgba(0, 0, 0, .48) !important;
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
    border-color: rgba(198, 179, 154, .30) !important;
    background: #280b0f !important;
    color: var(--text) !important;
}

#auth-card button.primary {
    border-color: rgba(198, 179, 154, .18) !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
    color: #fff8ef !important;
}

.auth-copy {
    margin-bottom: 20px !important;
    color: var(--muted) !important;
    line-height: 1.55 !important;
}

.auth-error {
    min-height: 24px !important;
    color: #f0aaa6 !important;
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
    width: 320px !important;
    min-width: 320px !important;
    max-width: 320px !important;
    height: 100vh !important;
    padding: 18px 16px !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    background:
        linear-gradient(180deg, #21080c 0%, #280b0f 55%, #1d070a 100%) !important;
    border-right: 1px solid rgba(198, 179, 154, .16) !important;
}

#sidebar::-webkit-scrollbar,
#document-cards::-webkit-scrollbar,
#conversation-list::-webkit-scrollbar {
    width: 6px;
}

#sidebar::-webkit-scrollbar-thumb,
#document-cards::-webkit-scrollbar-thumb,
#conversation-list::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(198, 179, 154, .24);
}

.brand {
    padding: 4px 6px 12px !important;
}

.brand h2 {
    margin: 0 !important;
    color: #fff8ef !important;
    font-size: 1.16rem !important;
    letter-spacing: -.025em !important;
}

.brand p {
    margin: 5px 0 0 !important;
    color: var(--camel) !important;
    font-size: .82rem !important;
}

.sidebar-heading {
    margin: 17px 4px 8px !important;
    color: var(--camel) !important;
    font-size: .71rem !important;
    font-weight: 760 !important;
    letter-spacing: .105em !important;
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
    border: 1px solid rgba(198, 179, 154, .18) !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
    color: #fff8ef !important;
}

#new-chat button:hover,
#upload-button button:hover {
    background: linear-gradient(135deg, #a1494b, var(--rubine)) !important;
}

#conversation-list {
    max-height: 176px !important;
    overflow-y: auto !important;
    padding: 2px !important;
}

#conversation-list label {
    margin-bottom: 5px !important;
    padding: 9px 10px !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    background: transparent !important;
    color: var(--text-soft) !important;
    font-size: .84rem !important;
}

#conversation-list label:hover {
    background: rgba(198, 179, 154, .08) !important;
}

#conversation-list label:has(input:checked) {
    border-color: rgba(198, 179, 154, .28) !important;
    background: rgba(141, 58, 60, .34) !important;
    color: #fff8ef !important;
}

#document-upload {
    height: 106px !important;
    min-height: 106px !important;
    max-height: 106px !important;
    overflow: hidden !important;
    border: 1px dashed rgba(198, 179, 154, .38) !important;
    border-radius: 13px !important;
    background: rgba(198, 179, 154, .055) !important;
}

#document-upload * {
    color: var(--text-soft) !important;
}

#document-cards {
    max-height: 222px !important;
    margin-top: 10px !important;
    overflow-y: auto !important;
}

.document-card {
    display: grid;
    grid-template-columns: 38px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    margin-bottom: 8px;
    padding: 10px;
    border: 1px solid rgba(198, 179, 154, .16);
    border-radius: 12px;
    background: rgba(198, 179, 154, .055);
}

.document-icon {
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    border: 1px solid rgba(198, 179, 154, .20);
    border-radius: 10px;
    background: rgba(141, 58, 60, .22);
    color: #f7ecdf;
    font-size: .69rem;
    font-weight: 800;
    letter-spacing: .04em;
}

.document-info {
    min-width: 0;
}

.document-name {
    overflow: hidden;
    color: #fff8ef;
    font-size: .82rem;
    font-weight: 680;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.document-meta {
    margin-top: 3px;
    overflow: hidden;
    color: var(--camel);
    font-size: .71rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.status-badge {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    padding: 4px 7px;
    border-radius: 999px;
    font-size: .66rem;
    font-weight: 760;
    white-space: nowrap;
}

.status-ready {
    background: rgba(184, 197, 154, .14);
    color: #d9e3bc;
}

.status-processing,
.status-pending {
    background: rgba(216, 181, 121, .15);
    color: #f0ce93;
}

.status-failed,
.status-error {
    background: rgba(228, 135, 132, .16);
    color: #f4aaa7;
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
}

.status-processing .status-dot,
.status-pending .status-dot {
    animation: statusPulse 1.15s ease-in-out infinite;
}

.document-empty {
    padding: 15px 12px;
    border: 1px dashed rgba(198, 179, 154, .20);
    border-radius: 12px;
    color: var(--camel);
    font-size: .78rem;
    line-height: 1.45;
    text-align: center;
}

#selected-documents,
#manage-document {
    margin-top: 8px !important;
}

#sidebar .form,
#sidebar .block,
#sidebar .wrap {
    border-color: rgba(198, 179, 154, .18) !important;
    background: rgba(198, 179, 154, .055) !important;
    color: var(--text-soft) !important;
}

#sidebar input,
#sidebar textarea,
#sidebar select {
    color: #fff8ef !important;
    background: var(--tamarind) !important;
}

#sidebar label,
#sidebar span,
#sidebar p {
    color: var(--text-soft) !important;
}

.sidebar-actions {
    gap: 8px !important;
    margin-top: 8px !important;
}

.sidebar-actions button,
#refresh-documents button,
#delete-conversation button {
    border: 1px solid rgba(198, 179, 154, .18) !important;
    background: rgba(198, 179, 154, .075) !important;
    color: var(--text-soft) !important;
}

.sidebar-actions button:hover,
#refresh-documents button:hover,
#delete-conversation button:hover {
    background: rgba(198, 179, 154, .13) !important;
}

.danger-action button {
    color: #f1b0ad !important;
}

#account-card {
    margin-top: 16px !important;
    padding: 12px 13px !important;
    border: 1px solid rgba(198, 179, 154, .15) !important;
    border-radius: 12px !important;
    background: rgba(198, 179, 154, .055) !important;
}

#account-card h3 {
    margin: 0 !important;
    color: #fff8ef !important;
    font-size: .92rem !important;
}

#account-card p {
    margin: 3px 0 0 !important;
    color: var(--camel) !important;
    font-size: .78rem !important;
}

#logout button {
    margin-top: 8px !important;
    border: 1px solid rgba(198, 179, 154, .18) !important;
    background: transparent !important;
    color: var(--text-soft) !important;
}

#main-panel {
    position: relative !important;
    min-width: 0 !important;
    height: 100vh !important;
    padding: 0 !important;
    overflow-y: auto !important;
    background:
        radial-gradient(circle at 50% 25%, rgba(141, 58, 60, .11), transparent 34%),
        linear-gradient(180deg, #2b0d12 0%, #280b0f 54%, #23090d 100%) !important;
}

#main-panel > .gap,
#main-panel > .form,
#main-panel > .block,
#main-panel > .wrap {
    background: transparent !important;
}

#chat-header {
    min-height: 76px !important;
    padding: 0 30px !important;
    align-items: center !important;
    border-bottom: 1px solid rgba(198, 179, 154, .16) !important;
    background: rgba(53, 17, 23, .97) !important;
    box-shadow: 0 8px 25px rgba(0, 0, 0, .22) !important;
}

#chat-header h3 {
    margin: 0 !important;
    color: #fff8ef !important;
    font-size: 1.06rem !important;
}

#chat-header p {
    margin: 3px 0 0 !important;
    color: var(--camel) !important;
    font-size: .82rem !important;
}

#empty-state-panel {
    position: absolute !important;
    top: 76px !important;
    right: 0 !important;
    bottom: 140px !important;
    left: 0 !important;
    z-index: 4 !important;
    display: grid !important;
    place-items: center !important;
    padding: 28px !important;
    pointer-events: none !important;
    background: transparent !important;
}

.empty-state-card {
    width: min(720px, 92%);
    padding: 30px;
    border: 1px solid rgba(198, 179, 154, .18);
    border-radius: 22px;
    background: rgba(59, 19, 25, .78);
    box-shadow: 0 22px 65px rgba(0, 0, 0, .24);
    text-align: center;
    backdrop-filter: blur(10px);
}

.empty-eyebrow {
    color: var(--camel);
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .13em;
    text-transform: uppercase;
}

.empty-state-card h2 {
    margin: 9px 0 8px;
    color: #fff8ef;
    font-size: clamp(1.6rem, 2.3vw, 2.2rem);
    letter-spacing: -.035em;
}

.empty-state-card p {
    max-width: 560px;
    margin: 0 auto;
    color: var(--text-soft);
    line-height: 1.6;
}

.prompt-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    justify-content: center;
    margin-top: 20px;
}

.prompt-pill {
    padding: 8px 12px;
    border: 1px solid rgba(198, 179, 154, .20);
    border-radius: 999px;
    background: rgba(198, 179, 154, .075);
    color: #ead9c7;
    font-size: .79rem;
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
    border-radius: 17px !important;
    line-height: 1.64 !important;
    box-shadow: 0 11px 30px rgba(0, 0, 0, .18) !important;
}

#chatbot .message.user,
#chatbot [data-testid="user"] .message,
#chatbot .user .message {
    border: 1px solid rgba(255, 248, 239, .10) !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
    color: #fff8ef !important;
}

#chatbot .message.user *,
#chatbot [data-testid="user"] .message *,
#chatbot .user .message * {
    color: #fff8ef !important;
}

#chatbot .message.bot,
#chatbot .message.assistant,
#chatbot [data-testid="bot"] .message,
#chatbot [data-testid="assistant"] .message,
#chatbot .bot .message,
#chatbot .assistant .message {
    border: 1px solid rgba(198, 179, 154, .18) !important;
    background: rgba(59, 19, 25, .96) !important;
    color: #f7ecdf !important;
}

#chatbot .message.bot *,
#chatbot .message.assistant *,
#chatbot [data-testid="bot"] .message *,
#chatbot [data-testid="assistant"] .message *,
#chatbot .bot .message *,
#chatbot .assistant .message * {
    color: #f7ecdf !important;
}

#chatbot a {
    color: #e7c7a3 !important;
}

#chatbot code {
    border: 1px solid rgba(198, 179, 154, .20) !important;
    background: #23090d !important;
    color: #f1dfca !important;
}

#chatbot pre {
    border: 1px solid rgba(198, 179, 154, .20) !important;
    background: #1d070a !important;
    color: #f1dfca !important;
}

#sources-panel {
    margin: 0 7vw 12px !important;
    border: 1px solid rgba(198, 179, 154, .18) !important;
    border-radius: 14px !important;
    background: rgba(59, 19, 25, .96) !important;
    color: var(--text) !important;
}

#sources-panel summary,
#sources-panel span,
#sources-panel p,
#sources-panel strong {
    color: var(--text) !important;
}

.source-card {
    margin-bottom: 10px;
    padding: 13px;
    border: 1px solid rgba(198, 179, 154, .17);
    border-radius: 12px;
    background: rgba(40, 11, 15, .72);
}

.source-head {
    display: flex;
    gap: 12px;
    justify-content: space-between;
}

.source-name {
    color: #fff8ef;
    font-weight: 700;
}

.source-score,
.source-location {
    color: var(--camel);
    font-size: .81rem;
}

.source-excerpt {
    margin: 8px 0 0;
    color: var(--text-soft);
    line-height: 1.52;
}

#selection-chips {
    position: sticky !important;
    bottom: 88px !important;
    z-index: 8 !important;
    min-height: 42px !important;
    padding: 8px 7vw 4px !important;
    border-top: 1px solid rgba(198, 179, 154, .12) !important;
    background: rgba(40, 11, 15, .97) !important;
}

.selection-row {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    align-items: center;
}

.selection-label {
    margin-right: 2px;
    color: var(--camel);
    font-size: .72rem;
    font-weight: 760;
    letter-spacing: .06em;
    text-transform: uppercase;
}

.document-chip {
    max-width: 220px;
    overflow: hidden;
    padding: 6px 9px;
    border: 1px solid rgba(198, 179, 154, .17);
    border-radius: 999px;
    background: rgba(123, 105, 78, .22);
    color: #ead9c7;
    font-size: .76rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.selection-empty {
    color: var(--camel);
    font-size: .77rem;
}

#composer {
    position: sticky !important;
    bottom: 0 !important;
    z-index: 9 !important;
    min-height: 88px !important;
    padding: 12px 7vw 18px !important;
    align-items: end !important;
    gap: 10px !important;
    border-top: 1px solid rgba(198, 179, 154, .14) !important;
    background: rgba(40, 11, 15, .98) !important;
    box-shadow: 0 -12px 32px rgba(0, 0, 0, .25) !important;
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
    border: 1px solid rgba(198, 179, 154, .30) !important;
    border-radius: 16px !important;
    background: var(--tamarind) !important;
    color: #fff8ef !important;
    caret-color: #fff8ef !important;
    box-shadow: 0 9px 25px rgba(0, 0, 0, .22) !important;
}

#question-input textarea::placeholder {
    color: #bba991 !important;
}

#question-input textarea:focus {
    border-color: var(--rubine-light) !important;
    box-shadow: 0 0 0 3px rgba(141, 58, 60, .24) !important;
}

#send-button button {
    width: 56px !important;
    min-width: 56px !important;
    height: 56px !important;
    min-height: 56px !important;
    border: 1px solid rgba(255, 248, 239, .12) !important;
    border-radius: 16px !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
    color: #fff8ef !important;
    font-size: 1.12rem !important;
    box-shadow: 0 9px 24px rgba(0, 0, 0, .22) !important;
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
    border: 1px solid rgba(198, 179, 154, .25);
    border-radius: 15px;
    background: #3b1319;
    color: var(--text);
    box-shadow: 0 22px 55px rgba(0, 0, 0, .45);
    pointer-events: auto;
}

.toast.error {
    border-left: 4px solid var(--danger);
}

.toast.success {
    border-left: 4px solid var(--success);
}

.toast.info {
    border-left: 4px solid var(--rubine-light);
}

.toast.working {
    border-left: 4px solid var(--warning);
}

.toast strong {
    display: block;
    margin-bottom: 3px;
    color: #fff8ef;
}

.toast span {
    color: var(--text-soft);
    font-size: .9rem;
    line-height: 1.45;
}

.toast-icon {
    flex: 0 0 auto;
    width: 24px;
    height: 24px;
    display: grid;
    place-items: center;
    color: #fff8ef;
    font-weight: 800;
}

.spinner {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(255, 248, 239, .24);
    border-top-color: var(--warning);
    border-radius: 50%;
    animation: spin .8s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

@keyframes statusPulse {
    0%, 100% {
        opacity: .4;
        transform: scale(.85);
    }
    50% {
        opacity: 1;
        transform: scale(1.15);
    }
}

button,
input,
textarea,
select,
.gradio-container .wrap {
    transition: none !important;
}

@media (max-width: 1050px) {
    #sidebar {
        width: 286px !important;
        min-width: 286px !important;
        max-width: 286px !important;
    }

    #sources-panel {
        margin-left: 22px !important;
        margin-right: 22px !important;
    }

    #selection-chips,
    #composer {
        padding-left: 22px !important;
        padding-right: 22px !important;
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
        f"{icon_html}<div><strong>{html.escape(title)}</strong>"
        f"<span>{html.escape(message)}</span></div></div>"
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


def parse_api_datetime(value: Any) -> datetime | None:
    text = safe_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_file_size(value: Any) -> str:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return ""
    units = ["B", "KB", "MB", "GB"]
    amount = float(max(size, 0))
    unit = units[0]
    for candidate in units:
        unit = candidate
        if amount < 1024 or candidate == units[-1]:
            break
        amount /= 1024
    precision = 0 if unit == "B" else 1
    return f"{amount:.{precision}f} {unit}"


def document_status(document: dict[str, Any]) -> str:
    return safe_text(document.get("status") or "unknown").lower().replace(" ", "_")


def is_ready(document: dict[str, Any]) -> bool:
    return document_status(document) in READY_STATUSES


def document_icon(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return (suffix or "FILE")[:4].upper()


def render_document_cards(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return (
            '<div class="document-empty">No documents yet.<br>'
            "Upload a PDF, DOCX, TXT, MD, or JSON file.</div>"
        )

    cards: list[str] = []
    for document in documents:
        filename = safe_text(document.get("filename")) or "Untitled document"
        status_key = document_status(document)
        status_label = status_key.replace("_", " ").title()
        status_class = (
            "ready"
            if status_key in READY_STATUSES
            else "processing"
            if status_key in PROCESSING_STATUSES
            else "failed"
            if status_key in {"failed", "error"}
            else "pending"
        )
        size = format_file_size(
            document.get("size_bytes")
            or document.get("file_size")
            or document.get("size")
        )
        updated = parse_api_datetime(document.get("updated_at") or document.get("created_at"))
        date_label = updated.strftime("%d %b %Y") if updated else ""
        meta = " · ".join(part for part in (size, date_label) if part) or "Stored in your workspace"
        cards.append(
            '<div class="document-card">'
            f'<div class="document-icon">{html.escape(document_icon(filename))}</div>'
            '<div class="document-info">'
            f'<div class="document-name" title="{html.escape(filename)}">{html.escape(filename)}</div>'
            f'<div class="document-meta">{html.escape(meta)}</div>'
            "</div>"
            f'<span class="status-badge status-{status_class}">'
            '<span class="status-dot"></span>'
            f"{html.escape(status_label)}</span>"
            "</div>"
        )
    return "".join(cards)


def render_selected_chips(selected_ids: list[str] | None, catalog: dict[str, str] | None) -> str:
    selected = [safe_text(item) for item in (selected_ids or []) if safe_text(item)]
    names = catalog or {}
    if not selected:
        return '<div class="selection-empty">No documents selected. The assistant will search all ready documents.</div>'

    chips = []
    for document_id in selected:
        name = names.get(document_id, "Selected document")
        chips.append(f'<span class="document-chip" title="{html.escape(name)}">{html.escape(name)}</span>')
    return '<div class="selection-row"><span class="selection-label">Using</span>' + "".join(chips) + "</div>"


def render_empty_state(documents: list[dict[str, Any]]) -> str:
    ready_count = sum(1 for document in documents if is_ready(document))
    processing_count = sum(1 for document in documents if document_status(document) in PROCESSING_STATUSES)

    if ready_count:
        description = (
            f"{ready_count} document{'s are' if ready_count != 1 else ' is'} ready. "
            "Choose the files you want to search, then ask a focused question."
        )
        eyebrow = "Your knowledge workspace"
    elif processing_count:
        description = (
            f"{processing_count} document{'s are' if processing_count != 1 else ' is'} still processing. "
            "Refresh the status in a moment, then start asking questions."
        )
        eyebrow = "Indexing in progress"
    else:
        description = "Upload a document from the sidebar to build your private searchable knowledge space."
        eyebrow = "Start here"

    return (
        '<div class="empty-state-card">'
        f'<div class="empty-eyebrow">{html.escape(eyebrow)}</div>'
        "<h2>Ask better questions of your documents</h2>"
        f"<p>{html.escape(description)}</p>"
        '<div class="prompt-suggestions">'
        '<span class="prompt-pill">Summarize the key findings</span>'
        '<span class="prompt-pill">Compare the uploaded reports</span>'
        '<span class="prompt-pill">List decisions and action items</span>'
        '<span class="prompt-pill">Find evidence for a claim</span>'
        "</div></div>"
    )


def document_updates(
    documents: list[dict[str, Any]],
    selected_ids: list[str] | None = None,
):
    catalog: dict[str, str] = {}
    ready_choices: list[tuple[str, str]] = []
    manage_choices: list[tuple[str, str]] = []

    for document in documents:
        filename = safe_text(document.get("filename")) or "Untitled document"
        document_id = safe_text(document.get("id"))
        if not document_id:
            continue
        catalog[document_id] = filename
        manage_choices.append((filename, document_id))
        if is_ready(document):
            ready_choices.append((filename, document_id))

    ready_ids = [value for _, value in ready_choices]
    if selected_ids is None:
        selected = ready_ids
    else:
        selected = [value for value in selected_ids if value in ready_ids]

    return (
        gr.update(choices=ready_choices, value=selected),
        gr.update(choices=manage_choices, value=None),
        render_document_cards(documents),
        catalog,
        render_empty_state(documents),
        render_selected_chips(selected, catalog),
    )


def empty_document_outputs():
    return document_updates([], [])


def conversation_title(item: dict[str, Any]) -> str:
    title = safe_text(item.get("title"))
    if not title:
        title = safe_text(item.get("last_message") or item.get("first_message"))
    if not title:
        title = "New conversation"
    return title if len(title) <= 34 else title[:31].rstrip() + "…"


def conversation_group(item: dict[str, Any]) -> str:
    timestamp = parse_api_datetime(item.get("updated_at") or item.get("created_at"))
    if not timestamp:
        return "Older"
    today = datetime.now(timezone.utc).date()
    delta = (today - timestamp.astimezone(timezone.utc).date()).days
    if delta <= 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    if delta <= 7:
        return "This week"
    return "Older"


def conversation_updates(conversations: list[dict[str, Any]], selected: str | None = None):
    order = {"Today": 0, "Yesterday": 1, "This week": 2, "Older": 3}
    sorted_items = sorted(
        conversations,
        key=lambda item: (
            order.get(conversation_group(item), 4),
            -(parse_api_datetime(item.get("updated_at") or item.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)).timestamp(),
        ),
    )
    choices = [
        (
            f"{conversation_group(item)}  ·  {conversation_title(item)}",
            safe_text(item.get("id")),
        )
        for item in sorted_items
        if item.get("id")
    ]
    valid_values = {value for _, value in choices}
    value = selected if selected in valid_values else None
    return gr.update(choices=choices, value=value)


def load_documents(
    state: dict[str, Any] | None,
    selected_ids: list[str] | None = None,
):
    current = state or empty_state()
    if not current.get("access_token"):
        return empty_document_outputs()

    try:
        response = httpx.get(
            f"{BACKEND_URL}/documents",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return empty_document_outputs()

    if response.status_code != 200:
        return empty_document_outputs()

    data = response.json()
    documents = data if isinstance(data, list) else []
    return document_updates(documents, selected_ids)


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
        selected, manage, cards, catalog, empty_html, chips = empty_document_outputs()
        return (
            empty_state(),
            gr.update(visible=True),
            gr.update(visible=False),
            message,
            "",
            "",
            gr.update(choices=[], value=None),
            selected,
            manage,
            cards,
            catalog,
            gr.update(value=empty_html, visible=True),
            chips,
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
    selected, manage, cards, catalog, empty_html, chips = load_documents(state)
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
        selected,
        manage,
        cards,
        catalog,
        gr.update(value=empty_html, visible=True),
        chips,
    )


def logout():
    selected, manage, cards, catalog, empty_html, chips = empty_document_outputs()
    return (
        empty_state(),
        gr.update(visible=True),
        gr.update(visible=False),
        "",
        "",
        [],
        "",
        gr.update(visible=False),
        gr.update(choices=[], value=None),
        selected,
        manage,
        cards,
        catalog,
        gr.update(value=empty_html, visible=True),
        chips,
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


def upload_documents(
    state: dict[str, Any] | None,
    files: list[Any] | Any | None,
    selected_ids: list[str] | None,
):
    current = state or empty_state()
    if not current.get("access_token"):
        selected, manage, cards, catalog, empty_html, chips = empty_document_outputs()
        yield (
            selected,
            manage,
            cards,
            catalog,
            empty_html,
            chips,
            None,
            toast("error", "Session expired", "Please log in again."),
        )
        return

    paths = normalize_files(files)
    if not paths:
        selected, manage, cards, catalog, empty_html, chips = load_documents(current, selected_ids)
        yield (
            selected,
            manage,
            cards,
            catalog,
            empty_html,
            chips,
            None,
            toast("info", "No file selected", "Choose at least one document."),
        )
        return

    selected, manage, cards, catalog, empty_html, chips = load_documents(current, selected_ids)
    file_count = len(paths)
    yield (
        selected,
        manage,
        cards,
        catalog,
        empty_html,
        chips,
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

    selected, manage, cards, catalog, empty_html, chips = load_documents(current, None)
    if failures:
        message = "; ".join(failures[:3])
        title = "Upload completed with issues" if success else "Upload failed"
        kind = "info" if success else "error"
    else:
        title = "Upload complete"
        message = f"{success} document(s) were added to your workspace."
        kind = "success"

    yield selected, manage, cards, catalog, empty_html, chips, None, toast(kind, title, message)


def refresh_documents(
    state: dict[str, Any] | None,
    selected_ids: list[str] | None,
):
    selected, manage, cards, catalog, empty_html, chips = load_documents(state, selected_ids)
    return (
        selected,
        manage,
        cards,
        catalog,
        empty_html,
        chips,
        toast("success", "Status refreshed", "Document processing states are up to date."),
    )


def delete_document(
    state: dict[str, Any] | None,
    document_id: str | None,
    selected_ids: list[str] | None,
):
    current = state or empty_state()
    clean_id = safe_text(document_id)
    if not clean_id:
        outputs = load_documents(current, selected_ids)
        return (*outputs, toast("info", "Choose a document", "Select a file before deleting it."))

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

    remaining = [item for item in (selected_ids or []) if item != clean_id]
    outputs = load_documents(current, remaining)
    return (*outputs, message)


def reprocess_document(
    state: dict[str, Any] | None,
    document_id: str | None,
    selected_ids: list[str] | None,
):
    current = state or empty_state()
    clean_id = safe_text(document_id)
    if not clean_id:
        outputs = load_documents(current, selected_ids)
        yield (*outputs, toast("info", "Choose a document", "Select a file before reprocessing it."))
        return

    outputs = load_documents(current, selected_ids)
    yield (
        *outputs,
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

    outputs = load_documents(current, selected_ids)
    yield (*outputs, message)


def update_selected_chips(
    selected_ids: list[str] | None,
    catalog: dict[str, str] | None,
):
    return render_selected_chips(selected_ids, catalog)


def new_chat(state: dict[str, Any] | None):
    current = state or empty_state()
    updated = {**current, "conversation_id": None}
    return (
        updated,
        gr.update(value=None),
        [],
        gr.update(visible=False),
        "",
        gr.update(visible=True),
        toast("info", "New chat", "Start with a question about your documents."),
    )


def load_conversation(state: dict[str, Any] | None, conversation_id: str | None):
    current = state or empty_state()
    clean_id = safe_text(conversation_id)
    if not clean_id:
        return current, [], gr.update(visible=False), gr.update(visible=True), ""

    try:
        response = httpx.get(
            f"{BACKEND_URL}/conversations/{clean_id}/messages",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return current, [], gr.update(visible=False), gr.update(visible=True), toast(
            "error", "Could not load chat", backend_unavailable()
        )

    if response.status_code != 200:
        return current, [], gr.update(visible=False), gr.update(visible=True), toast(
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
    return (
        updated,
        history,
        gr.update(visible=False),
        gr.update(visible=not bool(history)),
        "",
    )


def delete_conversation(state: dict[str, Any] | None, conversation_id: str | None):
    current = state or empty_state()
    clean_id = safe_text(conversation_id)
    if not clean_id:
        return (
            current,
            load_conversations(current),
            [],
            gr.update(visible=False),
            gr.update(visible=True),
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
            gr.update(visible=True),
            toast("error", "Delete failed", backend_unavailable()),
        )

    if response.status_code != 204:
        return (
            current,
            load_conversations(current),
            [],
            gr.update(visible=False),
            gr.update(visible=True),
            toast("error", "Delete failed", friendly_api_error(response)),
        )

    updated = {**current, "conversation_id": None}
    return (
        updated,
        load_conversations(updated),
        [],
        gr.update(visible=False),
        gr.update(visible=True),
        toast("success", "Chat deleted", "The conversation was removed."),
    )


def escape_markdown(value: str) -> str:
    escaped = value
    for character in ("\\", "`", "*", "_", "{", "}", "[", "]", "<", ">", "#", "+", "-", ".", "!", "|"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def source_location(source: dict[str, Any]) -> str:
    page = source.get("page_number")
    chunk = source.get("chunk_index")
    if page is not None:
        return f"Page {page}"
    if chunk is not None:
        return f"Chunk {chunk}"
    return "Excerpt"


def source_citations(raw_sources: list[dict[str, Any]]) -> str:
    if not raw_sources:
        return ""
    rows: list[str] = []
    seen: set[tuple[str, str]] = set()
    for source in raw_sources[:5]:
        filename = safe_text(source.get("filename")) or "Document"
        location = source_location(source)
        key = (filename, location)
        if key in seen:
            continue
        seen.add(key)
        rows.append(f"- {escape_markdown(filename)} — {escape_markdown(location)}")
    if not rows:
        return ""
    return "\n\n---\n**Sources used**\n" + "\n".join(rows)


def format_sources(raw_sources: list[dict[str, Any]]) -> str:
    if not raw_sources:
        return '<p class="selection-empty">No sources were returned for this answer.</p>'

    cards: list[str] = []
    for source in raw_sources:
        filename = html.escape(safe_text(source.get("filename")) or "Document")
        location = html.escape(source_location(source))
        excerpt = safe_text(
            source.get("text_content")
            or source.get("text")
            or source.get("content")
        )
        if len(excerpt) > 420:
            excerpt = excerpt[:420].rstrip() + "…"
        try:
            score = float(source.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        score_label = f"{max(0, min(100, round(score * 100)))}% match"
        cards.append(
            '<div class="source-card">'
            '<div class="source-head">'
            f'<span class="source-name">{filename}</span>'
            f'<span class="source-score">{html.escape(score_label)}</span>'
            "</div>"
            f'<div class="source-location">{location}</div>'
            + (
                f'<p class="source-excerpt">{html.escape(excerpt)}</p>'
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
            gr.update(visible=not bool(current_history)),
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
            gr.update(visible=not bool(current_history)),
            toast("info", "Write a question", "Ask something about your uploaded documents."),
            load_conversations(current),
        )
        return

    working_history = [
        *current_history,
        {"role": "user", "content": clean_question},
        {"role": "assistant", "content": "Searching your documents and preparing a grounded answer…"},
    ]
    yield (
        current,
        "",
        working_history,
        "",
        gr.update(visible=False),
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
            gr.update(visible=False),
            toast("error", "Could not generate an answer", error_message),
            load_conversations(current),
        )
        return

    data = response.json()
    answer = safe_text(data.get("answer")) or "No answer was generated."
    raw_sources = data.get("retrieved_sources") or data.get("sources") or []
    source_list = raw_sources if isinstance(raw_sources, list) else []
    answer_with_sources = answer + source_citations(source_list)
    updated_history = [
        *current_history,
        {"role": "user", "content": clean_question},
        {"role": "assistant", "content": answer_with_sources},
    ]
    updated = {
        **current,
        "conversation_id": safe_text(data.get("conversation_id"))
        or current.get("conversation_id"),
    }

    yield (
        updated,
        "",
        updated_history,
        format_sources(source_list),
        gr.update(visible=bool(source_list)),
        gr.update(visible=False),
        toast("success", "Answer ready", "The response is grounded in your selected documents."),
        load_conversations(updated),
    )


with gr.Blocks(
    title="Document Assistant",
    fill_width=True,
    fill_height=True,
) as demo:
    auth_state = gr.State(empty_state())
    document_catalog = gr.State({})
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
            min_width=320,
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
                elem_id="delete-conversation",
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
                height=106,
                elem_id="document-upload",
            )
            upload_button = gr.Button(
                "Upload documents",
                variant="primary",
                elem_id="upload-button",
            )
            document_cards = gr.HTML(
                render_document_cards([]),
                elem_id="document-cards",
            )
            refresh_documents_button = gr.Button(
                "Refresh document status",
                elem_id="refresh-documents",
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
                label="Document actions",
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
                    "Grounded answers with the sources shown beneath each response"
                )

            empty_panel = gr.HTML(
                render_empty_state([]),
                visible=True,
                elem_id="empty-state-panel",
            )

            chatbot = gr.Chatbot(
                value=[],
                label="",
                show_label=False,
                container=False,
                height="calc(100vh - 248px)",
                min_height=420,
                max_height="calc(100vh - 248px)",
                placeholder="",
                buttons=["copy", "copy_all"],
                autoscroll=True,
                layout="bubble",
                feedback_options=None,
                group_consecutive_messages=False,
                elem_id="chatbot",
            )

            with gr.Accordion(
                "Source details",
                open=False,
                visible=False,
                elem_id="sources-panel",
            ) as sources_panel:
                sources_html = gr.HTML("")

            selection_chips = gr.HTML(
                render_selected_chips([], {}),
                elem_id="selection-chips",
            )

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
            document_cards,
            document_catalog,
            empty_panel,
            selection_chips,
        ],
        show_progress="minimal",
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
            sources_panel,
            conversation_list,
            selected_documents,
            manage_document,
            document_cards,
            document_catalog,
            empty_panel,
            selection_chips,
        ],
        show_progress="hidden",
    )

    upload_button.click(
        upload_documents,
        inputs=[auth_state, upload_files, selected_documents],
        outputs=[
            selected_documents,
            manage_document,
            document_cards,
            document_catalog,
            empty_panel,
            selection_chips,
            upload_files,
            toast_box,
        ],
        show_progress="hidden",
    )

    refresh_documents_button.click(
        refresh_documents,
        inputs=[auth_state, selected_documents],
        outputs=[
            selected_documents,
            manage_document,
            document_cards,
            document_catalog,
            empty_panel,
            selection_chips,
            toast_box,
        ],
        show_progress="hidden",
    )

    delete_document_button.click(
        delete_document,
        inputs=[auth_state, manage_document, selected_documents],
        outputs=[
            selected_documents,
            manage_document,
            document_cards,
            document_catalog,
            empty_panel,
            selection_chips,
            toast_box,
        ],
        show_progress="minimal",
    )

    reprocess_document_button.click(
        reprocess_document,
        inputs=[auth_state, manage_document, selected_documents],
        outputs=[
            selected_documents,
            manage_document,
            document_cards,
            document_catalog,
            empty_panel,
            selection_chips,
            toast_box,
        ],
        show_progress="hidden",
    )

    selected_documents.change(
        update_selected_chips,
        inputs=[selected_documents, document_catalog],
        outputs=[selection_chips],
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
            empty_panel,
            toast_box,
        ],
        show_progress="hidden",
    )

    conversation_list.change(
        load_conversation,
        inputs=[auth_state, conversation_list],
        outputs=[auth_state, chatbot, sources_panel, empty_panel, toast_box],
        show_progress="minimal",
    )

    delete_conversation_button.click(
        delete_conversation,
        inputs=[auth_state, conversation_list],
        outputs=[
            auth_state,
            conversation_list,
            chatbot,
            sources_panel,
            empty_panel,
            toast_box,
        ],
        show_progress="minimal",
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
            empty_panel,
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
            empty_panel,
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