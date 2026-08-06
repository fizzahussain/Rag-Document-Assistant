import html
import mimetypes
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gradio as gr
import httpx


def load_project_env() -> None:
    """Load simple project environment values without overriding the shell"""

    candidates = [
        Path(__file__).resolve().parents[1] / ".env",
        Path.cwd() / ".env",
    ]
    seen: set[Path] = set()

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)

        try:
            lines = resolved.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
                value = value[1:-1]
            if key:
                os.environ.setdefault(key, value)


load_project_env()

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://127.0.0.1:8000/api/v1",
).rstrip("/")

REQUEST_TIMEOUT = httpx.Timeout(timeout=240.0, connect=10.0)
STT_TIMEOUT = httpx.Timeout(timeout=180.0, connect=10.0)
STT_API_URL = os.getenv(
    "STT_API_URL",
    "https://api.openai.com/v1/audio/transcriptions",
).rstrip("/")
STT_API_KEY = os.getenv("STT_API_KEY") or os.getenv("OPENAI_API_KEY", "")
STT_MODEL = os.getenv("STT_MODEL", "gpt-4o-mini-transcribe")
SUPPORTED_FILE_TYPES = [".pdf", ".docx", ".txt", ".md", ".json"]
READY_STATUSES = {
    "ready",
    "completed",
    "complete",
    "indexed",
    "processed",
    "succeeded",
    "success",
    "available",
}
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
    --cream: #f4e7d7;
    --cream-soft: #ead8c4;
    --camel: #c6b39a;
    --camel-deep: #a88f72;
    --boho: #7b694e;
    --rubine: #8d3a3c;
    --rubine-light: #ad5658;
    --tamarind: #3b1319;
    --italian-roast: #280b0f;
    --page: #1c080b;
    --surface: #280b0f;
    --surface-raised: #351117;
    --surface-soft: #421820;
    --surface-hover: #51212a;
    --line: rgba(198, 179, 154, .20);
    --line-strong: rgba(198, 179, 154, .36);
    --text: #fff8ef;
    --text-soft: #f0dfcc;
    --muted: #c6b39a;
    --muted-deep: #aa967d;
    --accent: #8d3a3c;
    --accent-hover: #a84c4f;
    --danger: #f0aaa6;
    --success: #bdd0a3;
    --warning: #dfbd7f;
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
    height: 100vh !important;
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
        radial-gradient(circle at 15% 18%, rgba(141, 58, 60, .30), transparent 31%),
        radial-gradient(circle at 84% 79%, rgba(123, 105, 78, .22), transparent 28%),
        linear-gradient(145deg, #1b070a 0%, #280b0f 52%, #341017 100%) !important;
}

#auth-card {
    width: min(470px, calc(100vw - 40px)) !important;
    padding: 36px !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 26px !important;
    background: rgba(59, 19, 25, .96) !important;
    box-shadow: 0 32px 90px rgba(0, 0, 0, .48) !important;
    backdrop-filter: blur(14px);
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
    background: var(--italian-roast) !important;
    color: var(--text) !important;
}

#auth-card button.primary {
    border-color: rgba(255, 248, 239, .10) !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
    color: var(--text) !important;
}

.auth-copy {
    margin-bottom: 20px !important;
    color: var(--muted) !important;
    line-height: 1.55 !important;
}

.auth-error {
    min-height: 24px !important;
    color: var(--danger) !important;
    font-size: .92rem !important;
}

#workspace {
    display: flex !important;
    width: 100vw !important;
    height: 100vh !important;
    min-height: 100vh !important;
    max-height: 100vh !important;
    gap: 0 !important;
    overflow: hidden !important;
    background: var(--surface) !important;
}

#sidebar {
    display: flex !important;
    flex: 0 0 342px !important;
    flex-direction: column !important;
    width: 342px !important;
    min-width: 342px !important;
    max-width: 342px !important;
    height: 100vh !important;
    min-height: 0 !important;
    padding: 17px 15px 14px !important;
    overflow: hidden !important;
    background:
        radial-gradient(circle at 18% 4%, rgba(141, 58, 60, .20), transparent 27%),
        linear-gradient(180deg, #23090d 0%, #280b0f 54%, #1c070a 100%) !important;
    border-right: 1px solid var(--line) !important;
}

#sidebar-scroll {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    margin-top: 8px !important;
    padding-right: 5px !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
}

#sidebar-scroll::-webkit-scrollbar,
#document-cards::-webkit-scrollbar,
#conversation-list::-webkit-scrollbar,
#selected-documents::-webkit-scrollbar,
#chatbot .messages::-webkit-scrollbar,
#sources-panel::-webkit-scrollbar {
    width: 6px;
}

#sidebar-scroll::-webkit-scrollbar-thumb,
#document-cards::-webkit-scrollbar-thumb,
#conversation-list::-webkit-scrollbar-thumb,
#selected-documents::-webkit-scrollbar-thumb,
#chatbot .messages::-webkit-scrollbar-thumb,
#sources-panel::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(198, 179, 154, .24);
}

.brand {
    flex: 0 0 auto !important;
    padding: 4px 7px 10px !important;
}

.brand h2 {
    margin: 0 !important;
    color: var(--text) !important;
    font-size: 1.18rem !important;
    letter-spacing: -.025em !important;
}

.brand p {
    margin: 5px 0 0 !important;
    color: var(--camel) !important;
    font-size: .81rem !important;
}

#sidebar button {
    min-height: 38px !important;
    border-radius: 11px !important;
    font-weight: 680 !important;
    box-shadow: none !important;
}

#new-chat button,
#upload-button button {
    border: 1px solid rgba(255, 248, 239, .10) !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
    color: var(--text) !important;
}

#new-chat button:hover,
#upload-button button:hover {
    background: linear-gradient(135deg, var(--rubine-light), var(--rubine)) !important;
}

.sidebar-section {
    margin-bottom: 12px !important;
    padding: 13px !important;
    border: 1px solid var(--line) !important;
    border-radius: 16px !important;
    background: rgba(59, 19, 25, .56) !important;
    box-shadow: 0 12px 34px rgba(0, 0, 0, .14) !important;
}

.section-title {
    margin: 0 0 4px !important;
    color: var(--cream) !important;
    font-size: .84rem !important;
    font-weight: 760 !important;
    letter-spacing: -.01em !important;
}

.section-copy {
    margin: 0 0 10px !important;
    color: var(--camel) !important;
    font-size: .72rem !important;
    line-height: 1.45 !important;
}

#conversation-list {
    max-height: 208px !important;
    overflow-y: auto !important;
    padding: 2px !important;
}

#conversation-list label {
    display: flex !important;
    min-height: 42px !important;
    margin: 0 0 6px !important;
    padding: 9px 10px !important;
    align-items: center !important;
    border: 1px solid transparent !important;
    border-radius: 11px !important;
    background: rgba(198, 179, 154, .055) !important;
    color: var(--text-soft) !important;
    font-size: .78rem !important;
    line-height: 1.35 !important;
}

#conversation-list label:hover {
    border-color: rgba(198, 179, 154, .16) !important;
    background: rgba(198, 179, 154, .10) !important;
}

#conversation-list label:has(input:checked) {
    border-color: rgba(173, 86, 88, .48) !important;
    background: linear-gradient(135deg, rgba(141, 58, 60, .40), rgba(123, 105, 78, .17)) !important;
    color: var(--text) !important;
}

#document-upload {
    height: 88px !important;
    min-height: 88px !important;
    max-height: 88px !important;
    overflow: hidden !important;
    border: 1px dashed var(--line-strong) !important;
    border-radius: 13px !important;
    background: rgba(198, 179, 154, .055) !important;
}

#document-upload * {
    color: var(--text-soft) !important;
}

#document-cards {
    max-height: 150px !important;
    margin-top: 9px !important;
    overflow-y: auto !important;
    background: transparent !important;
}

.document-card {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr) auto;
    gap: 9px;
    min-height: 54px;
    margin-bottom: 7px;
    padding: 9px;
    align-items: center;
    border: 1px solid rgba(198, 179, 154, .14);
    border-radius: 11px;
    background: rgba(40, 11, 15, .66);
}

.document-icon {
    width: 34px;
    height: 34px;
    display: grid;
    place-items: center;
    border: 1px solid rgba(198, 179, 154, .18);
    border-radius: 9px;
    background: rgba(123, 105, 78, .20);
    color: var(--cream);
    font-size: .63rem;
    font-weight: 820;
}

.document-info {
    min-width: 0;
}

.document-name {
    overflow: hidden;
    color: var(--text);
    font-size: .76rem;
    font-weight: 690;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.document-meta {
    margin-top: 3px;
    overflow: hidden;
    color: var(--camel);
    font-size: .65rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.status-badge {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    padding: 4px 7px;
    border: 1px solid rgba(198, 179, 154, .14);
    border-radius: 999px;
    font-size: .61rem;
    font-weight: 760;
    white-space: nowrap;
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
}

.status-ready {
    color: var(--success);
    background: rgba(189, 208, 163, .08);
}

.status-processing,
.status-pending {
    color: var(--warning);
    background: rgba(223, 189, 127, .08);
}

.status-failed {
    color: var(--danger);
    background: rgba(240, 170, 166, .08);
}

.status-processing .status-dot,
.status-pending .status-dot {
    animation: statusPulse 1.15s ease-in-out infinite;
}

.document-empty {
    padding: 12px 10px;
    border: 1px dashed rgba(198, 179, 154, .20);
    border-radius: 11px;
    color: var(--camel);
    font-size: .72rem;
    line-height: 1.42;
    text-align: center;
}

#selected-documents {
    max-height: 190px !important;
    overflow-y: auto !important;
    padding: 2px !important;
}

#selected-documents label {
    margin: 0 0 6px !important;
    padding: 8px 9px !important;
    border: 1px solid rgba(198, 179, 154, .13) !important;
    border-radius: 10px !important;
    background: rgba(40, 11, 15, .56) !important;
    color: var(--text-soft) !important;
    font-size: .75rem !important;
}

#selected-documents label:has(input:checked) {
    border-color: rgba(173, 86, 88, .52) !important;
    background: rgba(141, 58, 60, .27) !important;
    color: var(--text) !important;
}

#sidebar .form,
#sidebar .block,
#sidebar .wrap {
    border-color: var(--line) !important;
    background: rgba(198, 179, 154, .04) !important;
    color: var(--text-soft) !important;
}

#sidebar input,
#sidebar textarea,
#sidebar select {
    color: var(--text) !important;
    background: var(--italian-roast) !important;
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
    border: 1px solid var(--line) !important;
    background: rgba(198, 179, 154, .07) !important;
    color: var(--text-soft) !important;
}

.sidebar-actions button:hover,
#refresh-documents button:hover,
#delete-conversation button:hover {
    background: rgba(198, 179, 154, .13) !important;
}

#delete-document button,
.danger-action button {
    border-color: rgba(240, 170, 166, .23) !important;
    background: rgba(141, 58, 60, .20) !important;
    color: #f6bfbc !important;
}

#document-actions {
    margin-top: 8px !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    background: rgba(40, 11, 15, .52) !important;
}

#document-actions summary,
#document-actions span,
#document-actions p {
    color: var(--text-soft) !important;
}

#account-area {
    flex: 0 0 auto !important;
    padding-top: 10px !important;
    border-top: 1px solid var(--line) !important;
    background: transparent !important;
}

#account-card {
    margin: 0 !important;
    padding: 10px 12px !important;
    border: 1px solid var(--line) !important;
    border-radius: 12px !important;
    background: rgba(198, 179, 154, .055) !important;
}

#account-card h3 {
    margin: 0 !important;
    color: var(--cream) !important;
    font-size: .87rem !important;
}

#account-card p {
    margin: 2px 0 0 !important;
    color: var(--camel) !important;
    font-size: .72rem !important;
}

#logout button {
    margin-top: 7px !important;
    border: 1px solid var(--line) !important;
    background: transparent !important;
    color: var(--text-soft) !important;
}

#main-panel {
    position: relative !important;
    display: flex !important;
    flex: 1 1 auto !important;
    flex-direction: column !important;
    min-width: 0 !important;
    height: 100vh !important;
    min-height: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    background:
        radial-gradient(circle at 52% 18%, rgba(141, 58, 60, .13), transparent 35%),
        radial-gradient(circle at 86% 72%, rgba(123, 105, 78, .08), transparent 30%),
        linear-gradient(180deg, #2c0d12 0%, #280b0f 55%, #22090d 100%) !important;
}

#chat-header {
    flex: 0 0 76px !important;
    min-height: 76px !important;
    padding: 0 30px !important;
    align-items: center !important;
    border-bottom: 1px solid var(--line) !important;
    background: rgba(53, 17, 23, .97) !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, .20) !important;
}

#chat-header h3 {
    margin: 0 !important;
    color: var(--text) !important;
    font-size: 1.06rem !important;
}

#chat-header p {
    margin: 3px 0 0 !important;
    color: var(--camel) !important;
    font-size: .81rem !important;
}

#chat-stage {
    position: relative !important;
    display: flex !important;
    flex: 1 1 auto !important;
    flex-direction: column !important;
    min-height: 0 !important;
    overflow: hidden !important;
    background: transparent !important;
}

#empty-state-panel {
    position: absolute !important;
    inset: 0 !important;
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
    border: 1px solid var(--line);
    border-radius: 22px;
    background: rgba(59, 19, 25, .78);
    box-shadow: 0 24px 70px rgba(0, 0, 0, .27);
    text-align: center;
    backdrop-filter: blur(12px);
}

.empty-eyebrow {
    color: var(--camel);
    font-size: .71rem;
    font-weight: 810;
    letter-spacing: .13em;
    text-transform: uppercase;
}

.empty-state-card h2 {
    margin: 9px 0 8px;
    color: var(--text);
    font-size: clamp(1.55rem, 2.2vw, 2.15rem);
    letter-spacing: -.035em;
}

.empty-state-card p {
    max-width: 570px;
    margin: 0 auto;
    color: var(--text-soft);
    line-height: 1.6;
}

.prompt-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    justify-content: center;
    margin-top: 19px;
}

.prompt-pill {
    padding: 8px 12px;
    border: 1px solid rgba(198, 179, 154, .20);
    border-radius: 999px;
    background: rgba(123, 105, 78, .20);
    color: var(--cream-soft);
    font-size: .78rem;
}

#chatbot {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    height: 100% !important;
    max-height: none !important;
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    overflow: hidden !important;
}

#chatbot > div,
#chatbot .bubble-wrap,
#chatbot .chatbot,
#chatbot .messages,
#chatbot .scroll-hide {
    width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
}

#chatbot .messages,
#chatbot .scroll-hide {
    overflow-y: auto !important;
    padding: 18px 5vw 24px !important;
    scroll-behavior: smooth;
}

#chatbot,
#chatbot .message,
#chatbot .message * {
    color: var(--text) !important;
}

#chatbot .message {
    max-width: 860px !important;
    border-radius: 18px !important;
    line-height: 1.64 !important;
    box-shadow: 0 11px 30px rgba(0, 0, 0, .18) !important;
}

#chatbot .message.user,
#chatbot [data-testid="user"] .message,
#chatbot .user .message {
    border: 1px solid rgba(255, 248, 239, .10) !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
    color: var(--text) !important;
}

#chatbot .message.user *,
#chatbot [data-testid="user"] .message *,
#chatbot .user .message * {
    color: var(--text) !important;
}

#chatbot .message.bot,
#chatbot .message.assistant,
#chatbot [data-testid="bot"] .message,
#chatbot [data-testid="assistant"] .message,
#chatbot .bot .message,
#chatbot .assistant .message {
    border: 1px solid var(--line) !important;
    background: rgba(59, 19, 25, .96) !important;
    color: var(--text) !important;
}

#chatbot .message.bot *,
#chatbot .message.assistant *,
#chatbot [data-testid="bot"] .message *,
#chatbot [data-testid="assistant"] .message *,
#chatbot .bot .message *,
#chatbot .assistant .message * {
    color: var(--text) !important;
}

#chatbot a {
    color: #edcfae !important;
}

#chatbot code {
    border: 1px solid var(--line) !important;
    background: var(--italian-roast) !important;
    color: var(--cream-soft) !important;
}

#chatbot pre {
    border: 1px solid var(--line) !important;
    background: #1c070a !important;
    color: var(--cream-soft) !important;
}

#sources-panel {
    flex: 0 0 auto !important;
    max-height: 180px !important;
    margin: 0 24px 12px !important;
    overflow-y: auto !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    background: rgba(59, 19, 25, .98) !important;
    color: var(--text) !important;
}

#sources-panel summary,
#sources-panel span,
#sources-panel p,
#sources-panel strong {
    color: var(--text) !important;
}

.source-card {
    margin-bottom: 9px;
    padding: 12px;
    border: 1px solid rgba(198, 179, 154, .17);
    border-radius: 11px;
    background: rgba(40, 11, 15, .72);
}

.source-head {
    display: flex;
    gap: 12px;
    justify-content: space-between;
}

.source-name {
    color: var(--cream);
    font-weight: 700;
}

.source-score,
.source-location {
    color: var(--camel);
    font-size: .8rem;
}

.source-excerpt {
    margin: 8px 0 0;
    color: var(--text-soft);
    line-height: 1.52;
}

#composer-shell {
    position: relative !important;
    flex: 0 0 auto !important;
    border-top: 1px solid var(--line) !important;
    background: rgba(40, 11, 15, .985) !important;
    box-shadow: 0 -14px 36px rgba(0, 0, 0, .24) !important;
}

#mention-menu {
    position: absolute !important;
    right: calc(5vw + 126px) !important;
    bottom: 89px !important;
    left: 5vw !important;
    z-index: 40 !important;
    max-height: 220px !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 14px !important;
    background: var(--surface-raised) !important;
    box-shadow: 0 22px 55px rgba(0, 0, 0, .40) !important;
}

#mention-menu * {
    color: var(--text-soft) !important;
}

#voice-panel {
    margin: 9px 5vw 0 !important;
    padding: 11px 12px !important;
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    background: rgba(59, 19, 25, .88) !important;
}

.voice-panel-head {
    margin-bottom: 8px;
}

.voice-panel-title {
    color: var(--cream);
    font-size: .82rem;
    font-weight: 740;
}

.voice-panel-copy {
    margin-top: 3px;
    color: var(--camel);
    font-size: .7rem;
    line-height: 1.4;
}

#voice-recorder {
    min-height: 68px !important;
    border: 1px solid rgba(198, 179, 154, .14) !important;
    border-radius: 11px !important;
    background: rgba(40, 11, 15, .72) !important;
}

#voice-recorder * {
    color: var(--text-soft) !important;
}

#voice-status {
    min-height: 22px !important;
    margin-top: 5px !important;
    background: transparent !important;
}

.voice-status {
    display: inline-flex;
    gap: 7px;
    align-items: center;
    color: var(--camel);
    font-size: .72rem;
}

.voice-status.recording {
    color: #f2b7b4;
}

.voice-status.transcribing {
    color: var(--warning);
}

.voice-status.ready {
    color: var(--success);
}

.voice-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: statusPulse 1s ease-in-out infinite;
}

#selection-chips {
    min-height: 34px !important;
    padding: 7px 5vw 2px !important;
    background: transparent !important;
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
    font-size: .7rem;
    font-weight: 780;
    letter-spacing: .06em;
    text-transform: uppercase;
}

.document-chip {
    max-width: 220px;
    overflow: hidden;
    padding: 5px 9px;
    border: 1px solid rgba(198, 179, 154, .19);
    border-radius: 999px;
    background: rgba(123, 105, 78, .23);
    color: var(--cream-soft);
    font-size: .74rem;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.selection-empty {
    color: var(--camel);
    font-size: .75rem;
}

#composer {
    min-height: 80px !important;
    padding: 8px 5vw 14px !important;
    align-items: end !important;
    gap: 9px !important;
    background: transparent !important;
}

#question-input,
#question-input > div,
#question-input .wrap,
#question-input .form {
    background: transparent !important;
}

#question-input textarea {
    min-height: 54px !important;
    max-height: 116px !important;
    padding: 14px 17px !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 16px !important;
    background: var(--tamarind) !important;
    color: var(--text) !important;
    caret-color: var(--text) !important;
    box-shadow: 0 9px 25px rgba(0, 0, 0, .22) !important;
}

#question-input textarea::placeholder {
    color: #bba990 !important;
}

#question-input textarea:focus {
    border-color: var(--rubine-light) !important;
    box-shadow: 0 0 0 3px rgba(141, 58, 60, .23) !important;
}

#mic-button button,
#send-button button {
    width: 54px !important;
    min-width: 54px !important;
    height: 54px !important;
    min-height: 54px !important;
    border-radius: 16px !important;
    color: var(--text) !important;
    font-size: 1.08rem !important;
    box-shadow: 0 9px 24px rgba(0, 0, 0, .22) !important;
}

#mic-button button {
    border: 1px solid var(--line-strong) !important;
    background: rgba(123, 105, 78, .20) !important;
}

#mic-button button:hover {
    background: rgba(123, 105, 78, .32) !important;
}

#send-button button {
    border: 1px solid rgba(255, 248, 239, .10) !important;
    background: linear-gradient(135deg, var(--rubine), #6f292d) !important;
}

#send-button button:hover {
    background: linear-gradient(135deg, var(--rubine-light), var(--rubine)) !important;
}

#mic-button button:disabled,
#send-button button:disabled {
    opacity: .48 !important;
    cursor: not-allowed !important;
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
    background: var(--tamarind);
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
    color: var(--text);
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
    color: var(--text);
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

@media (max-width: 1060px) {
    #sidebar {
        flex-basis: 308px !important;
        width: 308px !important;
        min-width: 308px !important;
        max-width: 308px !important;
    }

    #chatbot .messages,
    #selection-chips,
    #composer {
        padding-left: 24px !important;
        padding-right: 24px !important;
    }

    #voice-panel {
        margin-left: 24px !important;
        margin-right: 24px !important;
    }

    #mention-menu {
        right: 150px !important;
        left: 24px !important;
    }
}


/* Stable application shell overrides */
#sidebar > * {
    min-height: 0 !important;
}

#new-chat {
    flex: 0 0 44px !important;
    width: 100% !important;
    min-height: 44px !important;
    max-height: 44px !important;
    margin: 0 0 10px !important;
    overflow: visible !important;
}

#new-chat button {
    width: 100% !important;
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
    padding: 0 14px !important;
}

#sidebar-scroll {
    display: block !important;
    flex: 1 1 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: none !important;
}

#sidebar-scroll > *,
.sidebar-section,
#account-area {
    flex: 0 0 auto !important;
}

.sidebar-section {
    padding: 12px !important;
    background:
        linear-gradient(145deg, rgba(69, 25, 32, .88), rgba(45, 12, 17, .92)) !important;
}

#conversation-list {
    min-height: 44px !important;
    max-height: 196px !important;
}

#conversation-list > div,
#selected-documents > div {
    gap: 0 !important;
}

#document-cards {
    max-height: 184px !important;
}

#selected-documents {
    min-height: 42px !important;
    max-height: 176px !important;
}

#manage-document {
    flex: 0 0 auto !important;
}

#main-panel {
    flex: 1 1 0 !important;
    width: 0 !important;
}

#main-panel > * {
    min-height: 0 !important;
}

#chat-stage {
    flex: 1 1 0 !important;
    height: 0 !important;
    min-height: 0 !important;
}

#chatbot {
    flex: 1 1 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: none !important;
}

#chatbot > div,
#chatbot .bubble-wrap,
#chatbot .chatbot,
#chatbot .messages,
#chatbot .scroll-hide {
    min-height: 0 !important;
}

#sources-panel {
    flex: 0 0 auto !important;
    max-height: 132px !important;
}

#composer-shell {
    flex: 0 0 auto !important;
    min-height: 92px !important;
    max-height: 340px !important;
    overflow: visible !important;
}

#mention-menu {
    right: calc(5vw + 184px) !important;
    bottom: 92px !important;
    left: 5vw !important;
    max-height: 248px !important;
    padding: 10px !important;
    overflow-y: auto !important;
}

#mention-menu > label,
#mention-menu .label-wrap {
    color: var(--camel) !important;
    font-size: .72rem !important;
    font-weight: 720 !important;
}

#mention-menu label {
    display: flex !important;
    min-height: 38px !important;
    margin: 0 0 6px !important;
    padding: 8px 10px !important;
    align-items: center !important;
    border: 1px solid rgba(198, 179, 154, .15) !important;
    border-radius: 10px !important;
    background: rgba(40, 11, 15, .82) !important;
    color: var(--text-soft) !important;
    cursor: pointer !important;
}

#mention-menu label:hover,
#mention-menu label:has(input:checked) {
    border-color: rgba(173, 86, 88, .56) !important;
    background: rgba(141, 58, 60, .30) !important;
    color: var(--text) !important;
}

#mention-button,
#mic-button,
#send-button {
    flex: 0 0 54px !important;
    width: 54px !important;
    min-width: 54px !important;
    max-width: 54px !important;
}

#mention-button button,
#mic-button button,
#send-button button {
    width: 54px !important;
    min-width: 54px !important;
    max-width: 54px !important;
    height: 54px !important;
    min-height: 54px !important;
    max-height: 54px !important;
}

#mention-button button {
    border: 1px solid var(--line-strong) !important;
    background: rgba(123, 105, 78, .20) !important;
    color: var(--cream) !important;
    font-size: 1rem !important;
    font-weight: 820 !important;
}

#mention-button button:hover {
    background: rgba(123, 105, 78, .34) !important;
}

#question-input {
    min-width: 0 !important;
}

#question-input textarea {
    width: 100% !important;
}

@media (max-width: 760px) {
    #sidebar {
        flex-basis: 288px !important;
        width: 288px !important;
        min-width: 288px !important;
        max-width: 288px !important;
    }

    #mention-menu {
        right: 18px !important;
        left: 18px !important;
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

    return defaults.get(
        response.status_code, "The request could not be completed. Please try again."
    )


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
        parsed = parsed.replace(tzinfo=UTC)
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
            document.get("size_bytes") or document.get("file_size") or document.get("size")
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
        return '<div class="selection-empty">Using all ready documents. Type @ to choose a specific file.</div>'

    chips = []
    for document_id in selected:
        name = names.get(document_id, "Selected document")
        chips.append(
            f'<span class="document-chip" title="{html.escape(name)}">{html.escape(name)}</span>'
        )
    return (
        '<div class="selection-row"><span class="selection-label">Using</span>'
        + "".join(chips)
        + "</div>"
    )


def render_empty_state(documents: list[dict[str, Any]]) -> str:
    ready_count = sum(1 for document in documents if is_ready(document))
    processing_count = sum(
        1 for document in documents if document_status(document) in PROCESSING_STATUSES
    )

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
        description = (
            "Upload a document from the sidebar to build your private searchable knowledge space."
        )
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
        manage_choices.append((filename, document_id))
        if is_ready(document):
            catalog[document_id] = filename
            ready_choices.append((filename, document_id))

    ready_ids = [value for _, value in ready_choices]
    if selected_ids is None:
        selected = []
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
    today = datetime.now(UTC).date()
    delta = (today - timestamp.astimezone(UTC).date()).days
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
            -(
                parse_api_datetime(item.get("updated_at") or item.get("created_at"))
                or datetime.min.replace(tzinfo=UTC)
            ).timestamp(),
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
            if response.status_code in {200, 204}
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
        yield (
            *outputs,
            toast("info", "Choose a document", "Select a file before reprocessing it."),
        )
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
            if response.status_code in {200, 202}
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
        return (
            current,
            [],
            gr.update(visible=False),
            gr.update(visible=True),
            toast("error", "Could not load chat", backend_unavailable()),
        )

    if response.status_code != 200:
        return (
            current,
            [],
            gr.update(visible=False),
            gr.update(visible=True),
            toast("error", "Could not load chat", friendly_api_error(response)),
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

    if response.status_code not in {200, 204}:
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
    for character in (
        "\\",
        "`",
        "*",
        "_",
        "{",
        "}",
        "[",
        "]",
        "<",
        ">",
        "#",
        "+",
        "-",
        ".",
        "!",
        "|",
    ):
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
            source.get("text_content") or source.get("text") or source.get("content")
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
            + (f'<p class="source-excerpt">{html.escape(excerpt)}</p>' if excerpt else "")
            + "</div>"
        )
    return "".join(cards)


def render_voice_status(kind: str = "idle", message: str | None = None) -> str:
    messages = {
        "idle": "Open the recorder, speak, then stop to convert your voice into text.",
        "recording": "Recording… message sending is locked until you stop.",
        "transcribing": "Transcribing your recording…",
        "ready": "Transcript added to the prompt. Review it, then send.",
        "error": "Voice input could not be transcribed.",
    }
    safe_kind = kind if kind in messages else "idle"
    text = safe_text(message) or messages[safe_kind]
    pulse = (
        '<span class="voice-pulse"></span>' if safe_kind in {"recording", "transcribing"} else ""
    )
    return f'<div class="voice-status {safe_kind}">{pulse}<span>{html.escape(text)}</span></div>'


def toggle_voice_panel(is_open: bool | None):
    opened = not bool(is_open)
    return opened, gr.update(visible=opened)


def voice_recording_started():
    return (
        True,
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        render_voice_status("recording"),
        gr.update(visible=False, value=None),
        toast("working", "Listening", "Finish speaking and press stop before sending a message."),
    )


def transcribe_voice(audio_path: str | None, question: str | None):
    current_question = safe_text(question)

    yield (
        True,
        gr.update(value=current_question, interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        render_voice_status("transcribing"),
        toast("working", "Transcribing", "Converting your recording into text."),
        gr.update(),
    )

    path = Path(audio_path) if audio_path else None
    if not path or not path.exists():
        yield (
            False,
            gr.update(value=current_question, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            render_voice_status("error", "No recording was received. Try recording again."),
            toast("error", "No recording", "Record a voice prompt, then press stop."),
            None,
        )
        return

    api_key = STT_API_KEY
    if not api_key and "api.openai.com" in STT_API_URL:
        yield (
            False,
            gr.update(value=current_question, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            render_voice_status(
                "error", "Add OPENAI_API_KEY to your .env file to enable voice input."
            ),
            toast(
                "error",
                "Voice input is not configured",
                "Add OPENAI_API_KEY to the project .env file.",
            ),
            None,
        )
        return

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    mime_type = mimetypes.guess_type(path.name)[0] or "audio/wav"

    try:
        with path.open("rb") as audio_file:
            response = httpx.post(
                STT_API_URL,
                headers=headers,
                data={"model": STT_MODEL, "response_format": "json"},
                files={"file": (path.name, audio_file, mime_type)},
                timeout=STT_TIMEOUT,
            )
    except (OSError, httpx.HTTPError):
        yield (
            False,
            gr.update(value=current_question, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            render_voice_status("error", "The transcription service could not be reached."),
            toast(
                "error",
                "Transcription failed",
                "Check your internet connection and STT configuration.",
            ),
            None,
        )
        return

    if response.status_code not in {200, 201}:
        message = friendly_api_error(response)
        yield (
            False,
            gr.update(value=current_question, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            render_voice_status("error", message),
            toast("error", "Transcription failed", message),
            None,
        )
        return

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    transcript = safe_text(payload.get("text"))
    if not transcript:
        yield (
            False,
            gr.update(value=current_question, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            render_voice_status("error", "The service returned an empty transcript."),
            toast(
                "error", "Nothing was transcribed", "Try speaking more clearly or recording again."
            ),
            None,
        )
        return

    merged = f"{current_question} {transcript}".strip() if current_question else transcript
    yield (
        False,
        gr.update(value=merged, interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        render_voice_status("ready"),
        toast("success", "Voice prompt ready", "The transcript was added to the message box."),
        None,
    )


def ready_document_choices(catalog: dict[str, str] | None) -> list[tuple[str, str]]:
    names = catalog or {}
    return [
        (f"@ {name}", document_id)
        for document_id, name in sorted(names.items(), key=lambda item: item[1].lower())
    ]


def open_mention_menu(catalog: dict[str, str] | None):
    choices = ready_document_choices(catalog)
    if not choices:
        return (
            gr.update(visible=False, choices=[], value=None),
            toast(
                "info", "No ready documents", "Upload a document or wait for processing to finish."
            ),
        )
    return (
        gr.update(visible=True, choices=choices, value=None),
        "",
    )


def mention_suggestions(question: str | None, catalog: dict[str, str] | None):
    text = "" if question is None else str(question)
    match = re.search(r"(^|\s)@([^@\s]*)$", text)
    names = catalog or {}

    if not match or not names:
        return gr.update(visible=False, choices=[], value=None)

    query = match.group(2).strip().lower()
    choices = [
        (f"@ {name}", document_id)
        for document_id, name in sorted(names.items(), key=lambda item: item[1].lower())
        if not query or query in name.lower()
    ][:12]

    return gr.update(
        visible=bool(choices),
        choices=choices,
        value=None,
    )


def apply_document_mention(
    question: str | None,
    selected_ids: list[str] | None,
    mentioned_document_id: str | None,
    catalog: dict[str, str] | None,
):
    text = "" if question is None else str(question)
    document_id = safe_text(mentioned_document_id)
    names = catalog or {}
    name = names.get(document_id)

    if not document_id or not name:
        return (
            text,
            gr.update(),
            render_selected_chips(selected_ids, names),
            gr.update(visible=False, value=None),
        )

    match = re.search(r"(^|\s)@([^@\s]*)$", text)
    if match:
        prefix = text[: match.start()]
        leading = match.group(1)
        updated_text = f"{prefix}{leading}@{name} "
    else:
        spacer = "" if not text or text.endswith((" ", "\n")) else " "
        updated_text = f"{text}{spacer}@{name} "

    selected = [safe_text(item) for item in (selected_ids or []) if safe_text(item)]
    if document_id not in selected:
        selected.append(document_id)

    return (
        updated_text,
        gr.update(value=selected),
        render_selected_chips(selected, names),
        gr.update(visible=False, value=None),
    )


def ask_question(
    state: dict[str, Any] | None,
    question: str | None,
    selected_documents: list[str] | None,
    history: list[dict[str, str]] | None,
    voice_busy: bool | None,
):
    current = state or empty_state()
    clean_question = safe_text(question)
    current_history = history or []

    if voice_busy:
        yield (
            current,
            safe_text(question),
            current_history,
            "",
            gr.update(visible=False),
            gr.update(visible=not bool(current_history)),
            toast(
                "info",
                "Finish voice input",
                "Stop the recording and wait for transcription before sending.",
            ),
            load_conversations(current),
        )
        return

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
        {
            "role": "assistant",
            "content": "Searching your documents and preparing a grounded answer…",
        },
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
        "conversation_id": safe_text(data.get("conversation_id")) or current.get("conversation_id"),
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
    voice_busy_state = gr.State(False)
    voice_panel_state = gr.State(False)
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
                "A private workspace for grounded conversations with your documents.",
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
            min_width=342,
            elem_id="sidebar",
        ):
            gr.Markdown(
                "## Document AI\nYour private knowledge space",
                elem_classes=["brand"],
            )

            new_chat_button = gr.Button(
                "+ New conversation",
                variant="primary",
                scale=0,
                elem_id="new-chat",
            )

            with gr.Column(scale=1, min_width=0, elem_id="sidebar-scroll"):
                with gr.Column(elem_classes=["sidebar-section"]):
                    gr.HTML(
                        '<div class="section-title">Conversations</div>'
                        '<div class="section-copy">Everything stays here. Select a chat without leaving the workspace.</div>'
                    )
                    conversation_list = gr.Radio(
                        choices=[],
                        value=None,
                        label="",
                        show_label=False,
                        container=False,
                        elem_id="conversation-list",
                    )
                    delete_conversation_button = gr.Button(
                        "Delete selected conversation",
                        elem_id="delete-conversation",
                        elem_classes=["danger-action"],
                    )

                with gr.Column(elem_classes=["sidebar-section"]):
                    gr.HTML(
                        '<div class="section-title">Document library</div>'
                        '<div class="section-copy">Upload files, see their status, and choose exactly what this chat can use.</div>'
                    )
                    upload_files = gr.File(
                        label="Drop files or browse",
                        show_label=False,
                        container=False,
                        file_count="multiple",
                        file_types=SUPPORTED_FILE_TYPES,
                        type="filepath",
                        height=88,
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
                        "Refresh processing status",
                        elem_id="refresh-documents",
                    )

                    gr.HTML(
                        '<div class="section-title" style="margin-top:13px !important;">Use in this chat</div>'
                        '<div class="section-copy">Tick files here or type @ in the message box. No selection means all ready files.</div>'
                    )
                    selected_documents = gr.CheckboxGroup(
                        choices=[],
                        value=[],
                        label="",
                        show_label=False,
                        container=False,
                        elem_id="selected-documents",
                    )

                    with gr.Accordion(
                        "Document actions",
                        open=False,
                        elem_id="document-actions",
                    ):
                        manage_document = gr.Dropdown(
                            choices=[],
                            value=None,
                            label="Choose a document",
                            show_label=False,
                            container=False,
                            elem_id="manage-document",
                        )
                        with gr.Row(elem_classes=["sidebar-actions"]):
                            reprocess_document_button = gr.Button("Reprocess")
                            delete_document_button = gr.Button(
                                "Delete document",
                                elem_id="delete-document",
                                elem_classes=["danger-action"],
                            )

            with gr.Column(scale=0, elem_id="account-area"):
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
                    "Messages, sources, document mentions, and voice input stay in one fixed workspace"
                )

            with gr.Column(scale=1, min_width=0, elem_id="chat-stage"):
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
                    height="100%",
                    min_height=0,
                    placeholder="",
                    buttons=["copy", "copy_all"],
                    autoscroll=True,
                    layout="bubble",
                    feedback_options=None,
                    group_consecutive_messages=False,
                    elem_id="chatbot",
                )

                with gr.Accordion(
                    "Sources used for the latest answer",
                    open=False,
                    visible=False,
                    elem_id="sources-panel",
                ) as sources_panel:
                    sources_html = gr.HTML("")

            with gr.Column(scale=0, elem_id="composer-shell"):
                mention_menu = gr.Radio(
                    choices=[],
                    value=None,
                    label="Choose a ready document",
                    show_label=True,
                    container=True,
                    visible=False,
                    elem_id="mention-menu",
                )

                with gr.Column(visible=False, elem_id="voice-panel") as voice_panel:
                    gr.HTML(
                        '<div class="voice-panel-head">'
                        '<div class="voice-panel-title">Voice prompt</div>'
                        '<div class="voice-panel-copy">Record your question and press stop. Sending is locked while you are speaking or while the transcript is being prepared.</div>'
                        "</div>"
                    )
                    voice_recorder = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        format="wav",
                        label="",
                        show_label=False,
                        container=False,
                        interactive=True,
                        buttons=[],
                        elem_id="voice-recorder",
                    )
                    voice_status = gr.HTML(
                        render_voice_status(),
                        elem_id="voice-status",
                    )

                selection_chips = gr.HTML(
                    render_selected_chips([], {}),
                    elem_id="selection-chips",
                )

                with gr.Row(elem_id="composer"):
                    mention_button = gr.Button(
                        "@",
                        variant="secondary",
                        scale=0,
                        min_width=54,
                        elem_id="mention-button",
                    )
                    mic_button = gr.Button(
                        "🎙",
                        variant="secondary",
                        scale=0,
                        min_width=54,
                        elem_id="mic-button",
                    )
                    question_input = gr.Textbox(
                        label="",
                        show_label=False,
                        container=False,
                        placeholder="Ask about your documents…  Type @ to choose a file",
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
                        min_width=54,
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

    mention_button.click(
        open_mention_menu,
        inputs=[document_catalog],
        outputs=[mention_menu, toast_box],
        show_progress="hidden",
        queue=False,
    )

    question_input.input(
        mention_suggestions,
        inputs=[question_input, document_catalog],
        outputs=[mention_menu],
        show_progress="hidden",
        trigger_mode="always_last",
        queue=False,
    )

    mention_menu.change(
        apply_document_mention,
        inputs=[question_input, selected_documents, mention_menu, document_catalog],
        outputs=[question_input, selected_documents, selection_chips, mention_menu],
        show_progress="hidden",
        queue=False,
    )

    mic_button.click(
        toggle_voice_panel,
        inputs=[voice_panel_state],
        outputs=[voice_panel_state, voice_panel],
        show_progress="hidden",
    )

    voice_recorder.start_recording(
        voice_recording_started,
        outputs=[
            voice_busy_state,
            question_input,
            send_button,
            mic_button,
            voice_status,
            mention_menu,
            toast_box,
        ],
        show_progress="hidden",
    )

    voice_recorder.stop_recording(
        transcribe_voice,
        inputs=[voice_recorder, question_input],
        outputs=[
            voice_busy_state,
            question_input,
            send_button,
            mic_button,
            voice_status,
            toast_box,
            voice_recorder,
        ],
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
        inputs=[
            auth_state,
            question_input,
            selected_documents,
            chatbot,
            voice_busy_state,
        ],
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
        inputs=[
            auth_state,
            question_input,
            selected_documents,
            chatbot,
            voice_busy_state,
        ],
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
