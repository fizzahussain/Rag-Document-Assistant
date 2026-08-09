import asyncio
import base64
import html
import json
import mimetypes
import os
import re
import sys
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
    f"{BACKEND_URL}/audio/transcribe",
).rstrip("/")
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
PROCESSING_STATUSES = {
    "processing",
    "pending",
    "queued",
    "uploading",
    "extracting",
    "chunking",
    "embedding",
    "indexing",
}

EMPTY_STATE: dict[str, Any] = {
    "access_token": "",
    "user": None,
    "conversation_id": None,
}

THEME = gr.themes.Soft(
    primary_hue="rose",
    secondary_hue="amber",
    neutral_hue="stone",
    radius_size="lg",
    text_size="md",
)

CSS = r"""
:root {
    color-scheme: light !important;
    --quick-silver: #a09e9f;
    --desert-sand: #dfd3b5;
    --coyote-brown: #826632;
    --blast-off-bronze: #a67765;
    --dark-chestnut: #956460;
    --paper: #dfd3b5;
    --paper-deep: #d3c19f;
    --surface: #f7efe2;
    --surface-raised: #fffaf4;
    --surface-soft: #c9b6a8;
    --surface-hover: #b98b79;
    --text: #3b2a24;
    --text-soft: #5d443c;
    --muted: #7b6961;
    --line: rgba(130, 102, 50, .26);
    --line-strong: rgba(130, 102, 50, .46);
    --accent: #956460;
    --accent-hover: #7d4e4a;
    --accent-soft: rgba(149, 100, 96, .20);
    --success: #667a55;
    --warning: #826632;
    --danger: #934d4b;
    --shadow: 0 20px 55px rgba(67, 44, 35, .18);
}

html,
body {
    width: 100%;
    height: 100%;
    margin: 0;
    overflow: hidden;
    background: var(--paper) !important;
}

body,
.gradio-container {
    color: var(--text) !important;
    background: var(--paper) !important;
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

button,
input,
textarea,
select {
    font: inherit !important;
}

/* Authentication */
#auth-shell {
    width: 100vw !important;
    min-height: 100vh !important;
    padding: 28px !important;
    align-items: center !important;
    justify-content: center !important;
    background:
        radial-gradient(circle at 12% 16%, rgba(166, 119, 101, .24), transparent 30%),
        radial-gradient(circle at 86% 82%, rgba(130, 102, 50, .17), transparent 28%),
        linear-gradient(145deg, var(--paper), var(--paper-deep)) !important;
}

#auth-card {
    width: min(460px, calc(100vw - 36px)) !important;
    padding: 34px !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 24px !important;
    background: rgba(247, 239, 226, .98) !important;
    box-shadow: var(--shadow) !important;
}

#auth-card h1,
#auth-card h2,
#auth-card h3,
#auth-card p,
#auth-card label,
#auth-card span {
    color: var(--text) !important;
}

#auth-card input,
#auth-card textarea {
    border-color: var(--line-strong) !important;
    background: var(--surface-raised) !important;
    color: var(--text) !important;
}

#auth-card button.primary {
    border-color: transparent !important;
    background: var(--accent) !important;
    color: #fffaf1 !important;
}

.auth-copy {
    margin-bottom: 18px !important;
    color: var(--muted) !important;
    line-height: 1.55 !important;
}

.auth-error {
    min-height: 22px !important;
    color: var(--danger) !important;
}

#auth-shell::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background:
        radial-gradient(circle at 16% 18%, rgba(166, 119, 101, .42), transparent 30%),
        radial-gradient(circle at 84% 78%, rgba(149, 100, 96, .34), transparent 30%),
        linear-gradient(135deg, #dfd3b5 0%, #c8b28c 48%, #a67765 100%);
}

#auth-card {
    position: relative !important;
    z-index: 1 !important;
    overflow: hidden !important;
    border: 1px solid rgba(149, 100, 96, .40) !important;
    background: rgba(255, 250, 244, .92) !important;
    box-shadow: 0 28px 80px rgba(83, 51, 43, .25) !important;
    backdrop-filter: blur(18px);
}

#auth-card::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 8px;
    background: linear-gradient(90deg, #956460, #a67765, #826632);
}

#auth-card h1 {
    margin-bottom: 6px !important;
    color: #3b2a24 !important;
    font-size: 2rem !important;
    letter-spacing: -.04em !important;
}

#auth-card input {
    min-height: 48px !important;
    border: 1px solid rgba(130, 102, 50, .34) !important;
    border-radius: 13px !important;
    background: #fffaf4 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.7) !important;
}

#auth-card input:focus {
    border-color: #956460 !important;
    box-shadow: 0 0 0 3px rgba(149, 100, 96, .18) !important;
}

#auth-card button.primary {
    min-height: 48px !important;
    border-radius: 13px !important;
    background: linear-gradient(135deg, #956460, #a67765) !important;
    box-shadow: 0 12px 26px rgba(149, 100, 96, .24) !important;
}

#auth-card button.primary:hover {
    background: linear-gradient(135deg, #7d4e4a, #956460) !important;
}

#auth-card [role="radiogroup"] {
    padding: 5px !important;
    border: 1px solid rgba(130, 102, 50, .24) !important;
    border-radius: 13px !important;
    background: rgba(223, 211, 181, .48) !important;
}

/* Application shell */
#workspace {
    display: flex !important;
    width: 100vw !important;
    height: 100vh !important;
    min-height: 100vh !important;
    max-height: 100vh !important;
    gap: 0 !important;
    overflow: hidden !important;
    background: var(--paper) !important;
}

#sidebar {
    display: flex !important;
    flex: 0 0 320px !important;
    flex-direction: column !important;
    width: 320px !important;
    min-width: 320px !important;
    max-width: 320px !important;
    height: 100vh !important;
    min-height: 0 !important;
    padding: 16px 14px 13px !important;
    overflow: hidden !important;
    border-right: 1px solid var(--line) !important;
    background: linear-gradient(180deg, #dfd3b5 0%, #cdbb99 100%) !important;
}

.brand {
    flex: 0 0 auto !important;
    padding: 5px 7px 11px !important;
}

.brand h2 {
    margin: 0 !important;
    color: var(--text) !important;
    font-size: 1.15rem !important;
}

.brand p {
    margin: 4px 0 0 !important;
    color: var(--muted) !important;
    font-size: .8rem !important;
}

#new-chat {
    flex: 0 0 43px !important;
    width: 100% !important;
    margin: 0 0 10px !important;
}

#new-chat button,
#upload-button button {
    width: 100% !important;
    border: 1px solid transparent !important;
    border-radius: 12px !important;
    background: var(--accent) !important;
    color: #fffaf1 !important;
    font-weight: 720 !important;
}

#new-chat button:hover,
#upload-button button:hover {
    background: var(--accent-hover) !important;
}

#sidebar-scroll {
    display: block !important;
    flex: 1 1 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    margin-top: 4px !important;
    padding-right: 4px !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
}

#sidebar-scroll::-webkit-scrollbar,
#conversation-list::-webkit-scrollbar,
#document-cards::-webkit-scrollbar,
#selected-documents::-webkit-scrollbar,
#chatbot .messages::-webkit-scrollbar,
#sources-panel::-webkit-scrollbar {
    width: 6px;
}

#sidebar-scroll::-webkit-scrollbar-thumb,
#conversation-list::-webkit-scrollbar-thumb,
#document-cards::-webkit-scrollbar-thumb,
#selected-documents::-webkit-scrollbar-thumb,
#chatbot .messages::-webkit-scrollbar-thumb,
#sources-panel::-webkit-scrollbar-thumb {
    border-radius: 99px;
    background: rgba(130, 102, 50, .25);
}

.sidebar-section {
    margin-bottom: 11px !important;
    padding: 12px !important;
    border: 1px solid var(--line) !important;
    border-radius: 15px !important;
    background: rgba(255, 250, 244, .82) !important;
    box-shadow: 0 8px 24px rgba(70, 53, 35, .06) !important;
}

.section-title {
    margin: 0 0 4px !important;
    color: var(--text) !important;
    font-size: .82rem !important;
    font-weight: 780 !important;
}

.section-copy {
    margin: 0 0 9px !important;
    color: var(--muted) !important;
    font-size: .71rem !important;
    line-height: 1.42 !important;
}

#conversation-list {
    min-height: 44px !important;
    max-height: 190px !important;
    overflow-y: auto !important;
}

#conversation-list label,
#selected-documents label {
    margin: 0 0 6px !important;
    padding: 8px 9px !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    background: rgba(130, 102, 50, .06) !important;
    color: var(--text-soft) !important;
    font-size: .75rem !important;
}

#conversation-list label:hover,
#selected-documents label:hover {
    border-color: var(--line) !important;
    background: rgba(130, 102, 50, .10) !important;
}

#conversation-list label:has(input:checked),
#selected-documents label:has(input:checked) {
    border-color: rgba(149, 100, 96, .35) !important;
    background: var(--accent-soft) !important;
    color: var(--text) !important;
}

#document-upload {
    height: 84px !important;
    min-height: 84px !important;
    overflow: hidden !important;
    border: 1px dashed var(--line-strong) !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, .42) !important;
}

#document-upload * {
    color: var(--text-soft) !important;
}

#document-cards {
    max-height: 170px !important;
    margin-top: 8px !important;
    overflow-y: auto !important;
}

.document-card-info {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr) auto;
    gap: 8px;
    margin-bottom: 6px;
    padding: 8px;
    align-items: center;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: rgba(255, 250, 241, .68);
}

.document-icon {
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    border-radius: 8px;
    background: rgba(130, 102, 50, .13);
    color: var(--coyote-brown);
    font-size: .61rem;
    font-weight: 820;
}

.document-info {
    min-width: 0;
}

.document-name,
.document-meta {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.document-name {
    color: var(--text);
    font-size: .74rem;
    font-weight: 700;
}

.document-meta {
    margin-top: 2px;
    color: var(--muted);
    font-size: .63rem;
}

.status-badge {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    padding: 4px 7px;
    border-radius: 999px;
    font-size: .6rem;
    font-weight: 760;
    white-space: nowrap;
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
}

.status-ready { color: var(--success); background: rgba(102, 122, 85, .10); }
.status-processing,
.status-pending { color: var(--warning); background: rgba(130, 102, 50, .10); }
.status-failed { color: var(--danger); background: rgba(147, 77, 75, .10); }

.document-empty {
    padding: 11px 9px;
    border: 1px dashed var(--line);
    border-radius: 10px;
    color: var(--muted);
    font-size: .7rem;
    text-align: center;
}

#selected-documents {
    min-height: 40px !important;
    max-height: 150px !important;
    overflow-y: auto !important;
}

#refresh-documents button,
#delete-conversation button,
#logout button {
    border: 1px solid var(--line) !important;
    border-radius: 10px !important;
    background: rgba(255, 250, 241, .70) !important;
    color: var(--text-soft) !important;
}

.danger-action button {
    border-color: rgba(147, 77, 75, .22) !important;
    color: var(--danger) !important;
}

#account-area {
    flex: 0 0 auto !important;
    padding-top: 9px !important;
    border-top: 1px solid var(--line) !important;
}

#account-card {
    margin: 0 !important;
    padding: 9px 11px !important;
    border: 1px solid var(--line) !important;
    border-radius: 11px !important;
    background: rgba(255, 250, 241, .66) !important;
}

#account-card h3,
#account-card p {
    margin: 0 !important;
    color: var(--text) !important;
}

/* Main workspace */
#main-panel {
    position: relative !important;
    display: flex !important;
    flex: 1 1 0 !important;
    flex-direction: column !important;
    width: 0 !important;
    min-width: 0 !important;
    height: 100vh !important;
    min-height: 0 !important;
    overflow: hidden !important;
    background:
        radial-gradient(circle at 75% 18%, rgba(166, 119, 101, .24), transparent 34%),
        radial-gradient(circle at 35% 80%, rgba(149, 100, 96, .14), transparent 35%),
        #eadfc8 !important;
}

#chat-header {
    flex: 0 0 72px !important;
    min-height: 72px !important;
    padding: 0 28px !important;
    align-items: center !important;
    border-bottom: 1px solid var(--line) !important;
    background: rgba(247, 239, 226, .96) !important;
}

#chat-header h3 {
    margin: 0 !important;
    color: var(--text) !important;
    font-size: 1.04rem !important;
}

#chat-header p {
    margin: 3px 0 0 !important;
    color: var(--muted) !important;
    font-size: .79rem !important;
}

#chat-stage {
    position: relative !important;
    display: flex !important;
    flex: 1 1 0 !important;
    flex-direction: column !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

#empty-state-panel {
    position: absolute !important;
    inset: 0 !important;
    z-index: 3 !important;
    display: grid !important;
    place-items: center !important;
    padding: 28px !important;
    pointer-events: none !important;
}

.empty-state-card {
    width: min(680px, 92%);
    padding: 28px;
    border: 1px solid var(--line);
    border-radius: 20px;
    background: rgba(255, 250, 241, .88);
    box-shadow: var(--shadow);
    text-align: center;
}

.empty-eyebrow,
.selection-label {
    color: var(--coyote-brown);
    font-size: .69rem;
    font-weight: 820;
    letter-spacing: .10em;
    text-transform: uppercase;
}

.empty-state-card h2 {
    margin: 8px 0 7px;
    color: var(--text);
}

.empty-state-card p {
    margin: 0 auto;
    color: var(--text-soft);
    line-height: 1.55;
}

.prompt-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 17px;
}

.prompt-pill,
.document-chip {
    padding: 6px 10px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgba(130, 102, 50, .09);
    color: var(--text-soft);
    font-size: .74rem;
}

#empty-state-panel .prompt-pill {
    pointer-events: auto !important;
    cursor: pointer !important;
    user-select: none;
}

#chatbot {
    flex: 1 1 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: none !important;
    border: 0 !important;
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
    background: transparent !important;
}

#chatbot .messages,
#chatbot .scroll-hide {
    overflow-y: auto !important;
    padding: 18px 4.5vw 22px !important;
}

#chatbot .message {
    max-width: 860px !important;
    border-radius: 17px !important;
    line-height: 1.6 !important;
    box-shadow: 0 8px 25px rgba(70, 53, 35, .08) !important;
}

#chatbot .message.user,
#chatbot [data-testid="user"] .message,
#chatbot .user .message {
    border: 1px solid rgba(149, 100, 96, .18) !important;
    background: var(--dark-chestnut) !important;
    color: #fffaf1 !important;
}

#chatbot .message.user * {
    color: #fffaf1 !important;
}

#chatbot .message.bot,
#chatbot .message.assistant,
#chatbot [data-testid="bot"] .message,
#chatbot [data-testid="assistant"] .message,
#chatbot .bot .message,
#chatbot .assistant .message {
    border: 1px solid var(--line) !important;
    background: var(--surface) !important;
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

#chatbot code,
#chatbot pre {
    border: 1px solid var(--line) !important;
    background: var(--paper-deep) !important;
    color: var(--text) !important;
}

#sources-panel {
    flex: 0 0 auto !important;
    max-height: 132px !important;
    margin: 0 22px 10px !important;
    overflow-y: auto !important;
    border: 1px solid var(--line) !important;
    border-radius: 13px !important;
    background: var(--surface) !important;
}

.source-card {
    margin-bottom: 8px;
    padding: 11px;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: var(--surface-raised);
}

.source-head {
    display: flex;
    gap: 10px;
    justify-content: space-between;
}

.source-name { color: var(--text); font-weight: 700; }
.source-score,
.source-location { color: var(--muted); font-size: .78rem; }
.source-excerpt { margin: 7px 0 0; color: var(--text-soft); line-height: 1.48; }

/* Composer and voice */
#composer-shell {
    position: relative !important;
    flex: 0 0 auto !important;
    min-height: 92px !important;
    max-height: 220px !important;
    overflow: visible !important;
    border-top: 1px solid var(--line) !important;
    background: rgba(247, 239, 226, .98) !important;
    box-shadow: 0 -12px 30px rgba(70, 53, 35, .07) !important;
}

#voice-panel {
    position: absolute !important;
    right: 4.5vw !important;
    bottom: 90px !important;
    left: 4.5vw !important;
    z-index: 50 !important;
    margin: 0 !important;
    padding: 12px !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 15px !important;
    background: rgba(247, 239, 226, .99) !important;
    box-shadow: var(--shadow) !important;
}

.voice-panel-title {
    color: var(--text);
    font-size: .81rem;
    font-weight: 760;
}

.voice-panel-copy {
    margin-top: 2px;
    color: var(--muted);
    font-size: .69rem;
}

#voice-recorder {
    min-height: 64px !important;
    margin-top: 8px !important;
    border: 1px solid var(--line) !important;
    border-radius: 11px !important;
    background: var(--paper-deep) !important;
}

#voice-recorder * {
    color: var(--text-soft) !important;
}

#voice-status {
    min-height: 20px !important;
    margin-top: 5px !important;
    background: transparent !important;
}

.voice-status {
    display: inline-flex;
    gap: 7px;
    align-items: center;
    color: var(--muted);
    font-size: .71rem;
}

.voice-status.recording { color: var(--danger); }
.voice-status.transcribing { color: var(--warning); }
.voice-status.ready { color: var(--success); }

.voice-pulse {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: currentColor;
}

#mention-menu {
    position: absolute !important;
    right: calc(4.5vw + 180px) !important;
    bottom: 88px !important;
    left: 4.5vw !important;
    z-index: 45 !important;
    max-height: 230px !important;
    padding: 9px !important;
    overflow-y: auto !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 13px !important;
    background: var(--surface-raised) !important;
    box-shadow: var(--shadow) !important;
}

#mention-menu label {
    margin: 0 0 5px !important;
    padding: 7px 9px !important;
    border: 1px solid var(--line) !important;
    border-radius: 9px !important;
    background: var(--surface) !important;
    color: var(--text-soft) !important;
}

#selection-chips {
    min-height: 32px !important;
    padding: 6px 4.5vw 1px !important;
    background: transparent !important;
}

.selection-row {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    align-items: center;
}

.selection-empty {
    color: var(--muted);
    font-size: .73rem;
}

#composer {
    min-height: 78px !important;
    padding: 8px 4.5vw 13px !important;
    align-items: end !important;
    gap: 8px !important;
}

#question-input,
#question-input > div,
#question-input .wrap,
#question-input .form {
    background: transparent !important;
}

#question-input textarea {
    min-height: 52px !important;
    max-height: 112px !important;
    padding: 13px 16px !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 15px !important;
    background: var(--surface-raised) !important;
    color: var(--text) !important;
    box-shadow: 0 7px 20px rgba(70, 53, 35, .07) !important;
}

#question-input textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-soft) !important;
}

#mention-button,
#mic-button,
#send-button {
    flex: 0 0 52px !important;
    width: 52px !important;
    min-width: 52px !important;
    max-width: 52px !important;
}

#mention-button button,
#mic-button button,
#send-button button {
    width: 52px !important;
    min-width: 52px !important;
    max-width: 52px !important;
    height: 52px !important;
    min-height: 52px !important;
    max-height: 52px !important;
    border-radius: 15px !important;
    box-shadow: 0 7px 20px rgba(70, 53, 35, .08) !important;
}

#mention-button button,
#mic-button button {
    border: 1px solid var(--line-strong) !important;
    background: var(--paper-deep) !important;
    color: var(--text) !important;
}

#send-button button {
    border: 1px solid transparent !important;
    background: var(--accent) !important;
    color: #fffaf1 !important;
}

#mention-button button:hover,
#mic-button button:hover { background: var(--surface-hover) !important; }
#send-button button:hover { background: var(--accent-hover) !important; }

#mention-button button:disabled,
#mic-button button:disabled,
#send-button button:disabled {
    opacity: .48 !important;
}

/* Toasts */
.toast-anchor {
    position: fixed !important;
    top: 16px !important;
    right: 18px !important;
    width: min(390px, calc(100vw - 36px)) !important;
    z-index: 9999 !important;
    pointer-events: none !important;
}

.toast {
    display: flex;
    gap: 11px;
    align-items: flex-start;
    padding: 14px 16px;
    border: 1px solid var(--line-strong);
    border-radius: 14px;
    background: var(--surface-raised);
    color: var(--text);
    box-shadow: var(--shadow);
}

.toast.error { border-left: 4px solid var(--danger); }
.toast.success { border-left: 4px solid var(--success); }
.toast.info { border-left: 4px solid var(--accent); }
.toast.working { border-left: 4px solid var(--warning); }
.toast strong { display: block; margin-bottom: 2px; color: var(--text); }
.toast span { color: var(--text-soft); font-size: .88rem; line-height: 1.42; }
.toast-icon { width: 22px; display: grid; place-items: center; font-weight: 800; }

.spinner {
    width: 17px;
    height: 17px;
    border: 2px solid rgba(130, 102, 50, .18);
    border-top-color: var(--warning);
    border-radius: 50%;
    animation: spin .8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1040px) {
    #sidebar {
        flex-basis: 292px !important;
        width: 292px !important;
        min-width: 292px !important;
        max-width: 292px !important;
    }

    #chatbot .messages,
    #selection-chips,
    #composer {
        padding-left: 22px !important;
        padding-right: 22px !important;
    }

    #voice-panel {
        right: 22px !important;
        left: 22px !important;
    }
}

/* Blush glass redesign and viewport fit */
:root {
    --vanilla-cream: #fff7e6;
    --blush-petal: #f7c8d3;
    --rosewood: #b46a72;
    --sage-leaf: #a8b58a;
    --misty-sky: #a9b7c6;
    --midnight-lagoon: #2d3a47;
    --paper: #fff7e6;
    --paper-deep: #f5e6df;
    --surface: rgba(255, 247, 230, .82);
    --surface-raised: rgba(255, 255, 255, .72);
    --surface-soft: rgba(247, 200, 211, .34);
    --surface-hover: rgba(180, 106, 114, .16);
    --text: #2d3a47;
    --text-soft: #4d5965;
    --muted: #76818b;
    --line: rgba(180, 106, 114, .18);
    --line-strong: rgba(180, 106, 114, .34);
    --accent: #b46a72;
    --accent-hover: #9d5861;
    --accent-soft: rgba(247, 200, 211, .48);
    --success: #74845e;
    --warning: #9a784c;
    --danger: #a94f5d;
    --shadow: 0 22px 60px rgba(45, 58, 71, .14);
}

html,
body,
.gradio-container,
#workspace,
#sidebar,
#main-panel {
    height: 100dvh !important;
    min-height: 100dvh !important;
    max-height: 100dvh !important;
}

body,
.gradio-container {
    background: var(--vanilla-cream) !important;
}

/* Glass login and signup */
#auth-shell {
    position: relative !important;
    isolation: isolate !important;
    overflow: hidden !important;
    padding: 24px !important;
    background:
        radial-gradient(circle at 18% 16%, rgba(247, 200, 211, .98) 0 12%, transparent 35%),
        radial-gradient(circle at 79% 21%, rgba(169, 183, 198, .82) 0 12%, transparent 34%),
        radial-gradient(circle at 76% 78%, rgba(168, 181, 138, .72) 0 13%, transparent 35%),
        linear-gradient(155deg, #fff7e6 0%, #f8dce3 39%, #cbd8e3 72%, #8ba9b5 100%) !important;
}

#auth-shell::before,
#auth-shell::after {
    content: "";
    position: fixed;
    z-index: -1;
    border-radius: 999px;
    filter: blur(3px);
    pointer-events: none;
}

#auth-shell::before {
    width: 280px;
    height: 280px;
    left: 8%;
    top: 8%;
    background: linear-gradient(145deg, rgba(180, 106, 114, .92), rgba(247, 200, 211, .66));
    box-shadow: 520px 350px 0 rgba(168, 181, 138, .64);
}

#auth-shell::after {
    width: 230px;
    height: 230px;
    right: 9%;
    bottom: 11%;
    background: linear-gradient(145deg, rgba(169, 183, 198, .84), rgba(45, 58, 71, .30));
}

#auth-card {
    width: min(470px, calc(100vw - 32px)) !important;
    padding: 34px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, .72) !important;
    border-radius: 28px !important;
    background: linear-gradient(145deg, rgba(255, 255, 255, .40), rgba(255, 247, 230, .24)) !important;
    box-shadow:
        0 30px 80px rgba(45, 58, 71, .22),
        inset 0 1px 0 rgba(255, 255, 255, .72) !important;
    backdrop-filter: blur(24px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(140%) !important;
}

#auth-card::before {
    height: 1px !important;
    background: rgba(255, 255, 255, .72) !important;
}

#auth-card h1 {
    color: var(--midnight-lagoon) !important;
    font-size: 2.15rem !important;
}

#auth-card .auth-copy,
#auth-card label,
#auth-card span,
#auth-card p {
    color: #4f5b66 !important;
}

#auth-card input,
#auth-card textarea {
    min-height: 49px !important;
    border: 1px solid rgba(255, 255, 255, .70) !important;
    background: rgba(255, 255, 255, .42) !important;
    color: var(--midnight-lagoon) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .76) !important;
    backdrop-filter: blur(12px) !important;
}

#auth-card input:focus {
    border-color: var(--rosewood) !important;
    box-shadow: 0 0 0 4px rgba(247, 200, 211, .42) !important;
}

#auth-card [role="radiogroup"] {
    border: 1px solid rgba(255, 255, 255, .56) !important;
    background: rgba(255, 255, 255, .26) !important;
}

#auth-card button.primary {
    background: linear-gradient(135deg, var(--rosewood), #cb8290) !important;
    color: white !important;
    box-shadow: 0 14px 30px rgba(180, 106, 114, .28) !important;
}

/* Compact app shell so every control stays on-screen */
#workspace {
    background: linear-gradient(135deg, #fff7e6, #f8e3e7 58%, #edf1f3) !important;
}

#sidebar {
    flex-basis: 292px !important;
    width: 292px !important;
    min-width: 292px !important;
    max-width: 292px !important;
    padding: 13px 12px 11px !important;
    border-right: 1px solid rgba(180, 106, 114, .22) !important;
    background:
        linear-gradient(180deg, rgba(247, 200, 211, .72), rgba(255, 247, 230, .94) 38%, rgba(247, 200, 211, .38)) !important;
}

.brand {
    padding: 3px 6px 8px !important;
}

.brand h2,
#chat-header h3,
.section-title,
#account-card h3 {
    color: var(--midnight-lagoon) !important;
}

#new-chat {
    flex-basis: 40px !important;
    margin-bottom: 8px !important;
}

#new-chat button,
#upload-button button,
#send-button button {
    background: linear-gradient(135deg, var(--rosewood), #c97f8c) !important;
    color: white !important;
    box-shadow: 0 10px 24px rgba(180, 106, 114, .20) !important;
}

#sidebar-scroll {
    margin-top: 2px !important;
    padding-right: 3px !important;
}

.sidebar-section {
    margin-bottom: 8px !important;
    padding: 10px !important;
    border-color: rgba(180, 106, 114, .16) !important;
    border-radius: 14px !important;
    background: rgba(255, 255, 255, .50) !important;
    box-shadow: 0 8px 24px rgba(45, 58, 71, .06) !important;
    backdrop-filter: blur(10px) !important;
}

.section-copy {
    margin-bottom: 7px !important;
}

#conversation-list {
    max-height: 152px !important;
}

#document-upload {
    height: 72px !important;
    min-height: 72px !important;
    background: rgba(255, 255, 255, .48) !important;
}

#document-cards {
    max-height: 132px !important;
}

#selected-documents {
    max-height: 112px !important;
}

#conversation-list label,
#selected-documents label,
.document-card-info {
    background: rgba(255, 255, 255, .46) !important;
}

#conversation-list label:has(input:checked),
#selected-documents label:has(input:checked) {
    border-color: rgba(180, 106, 114, .44) !important;
    background: rgba(247, 200, 211, .58) !important;
}

#account-area {
    padding-top: 7px !important;
}

#account-card {
    padding: 8px 10px !important;
    background: rgba(255, 255, 255, .48) !important;
}

#logout button,
#refresh-documents button,
#delete-conversation button {
    background: rgba(45, 58, 71, .86) !important;
    color: white !important;
}

#main-panel {
    background:
        radial-gradient(circle at 77% 18%, rgba(247, 200, 211, .60), transparent 34%),
        radial-gradient(circle at 34% 76%, rgba(169, 183, 198, .32), transparent 35%),
        linear-gradient(135deg, #fff7e6 0%, #f9e8ec 55%, #edf2f4 100%) !important;
}

#chat-header {
    flex-basis: 64px !important;
    min-height: 64px !important;
    padding: 0 24px !important;
    background: rgba(255, 247, 230, .74) !important;
    backdrop-filter: blur(16px) !important;
}

#chat-stage {
    min-height: 0 !important;
}

#chatbot .messages,
#chatbot .scroll-hide {
    padding: 16px clamp(18px, 3vw, 42px) 18px !important;
}

#chatbot .message {
    max-width: 780px !important;
}

#chatbot .message.user,
#chatbot [data-testid="user"] .message,
#chatbot .user .message {
    background: linear-gradient(135deg, var(--rosewood), #c9828e) !important;
}

#chatbot .message.bot,
#chatbot .message.assistant,
#chatbot [data-testid="bot"] .message,
#chatbot [data-testid="assistant"] .message,
#chatbot .bot .message,
#chatbot .assistant .message {
    background: rgba(255, 255, 255, .62) !important;
    border-color: rgba(180, 106, 114, .18) !important;
    backdrop-filter: blur(12px) !important;
}

#composer-shell {
    flex: 0 0 auto !important;
    min-height: 82px !important;
    max-height: 180px !important;
    overflow: visible !important;
    background: rgba(255, 247, 230, .80) !important;
    backdrop-filter: blur(18px) !important;
}

#selection-chips {
    min-height: 26px !important;
    padding: 4px clamp(18px, 3vw, 42px) 0 !important;
}

#composer {
    min-height: 68px !important;
    padding: 6px clamp(18px, 3vw, 42px) 10px !important;
    gap: 7px !important;
}

#question-input textarea {
    min-height: 48px !important;
    max-height: 88px !important;
    padding: 11px 14px !important;
    border-color: rgba(180, 106, 114, .28) !important;
    background: rgba(255, 255, 255, .70) !important;
}

#mention-button,
#mic-button,
#send-button {
    flex-basis: 48px !important;
    width: 48px !important;
    min-width: 48px !important;
    max-width: 48px !important;
}

#mention-button button,
#mic-button button,
#send-button button {
    width: 48px !important;
    min-width: 48px !important;
    max-width: 48px !important;
    height: 48px !important;
    min-height: 48px !important;
    max-height: 48px !important;
    border-radius: 14px !important;
}

#mention-button button,
#mic-button button {
    border-color: rgba(180, 106, 114, .26) !important;
    background: rgba(247, 200, 211, .64) !important;
    color: var(--midnight-lagoon) !important;
}

#voice-panel {
    right: clamp(18px, 3vw, 42px) !important;
    bottom: 76px !important;
    left: clamp(18px, 3vw, 42px) !important;
    max-height: min(300px, calc(100dvh - 170px)) !important;
    overflow-y: auto !important;
    border-color: rgba(180, 106, 114, .26) !important;
    background: rgba(255, 247, 230, .90) !important;
    backdrop-filter: blur(18px) !important;
}

#voice-recorder {
    background: rgba(247, 200, 211, .34) !important;
}

#mention-menu {
    right: 170px !important;
    bottom: 74px !important;
    left: clamp(18px, 3vw, 42px) !important;
    max-height: min(220px, calc(100dvh - 170px)) !important;
    background: rgba(255, 247, 230, .94) !important;
    backdrop-filter: blur(18px) !important;
}

.toast {
    background: rgba(255, 247, 230, .90) !important;
    backdrop-filter: blur(16px) !important;
}

@media (max-height: 780px) {
    #sidebar {
        padding-top: 9px !important;
        padding-bottom: 8px !important;
    }

    .brand p,
    .section-copy {
        line-height: 1.3 !important;
    }

    #conversation-list { max-height: 118px !important; }
    #document-cards { max-height: 104px !important; }
    #selected-documents { max-height: 86px !important; }
    #chat-header { flex-basis: 58px !important; min-height: 58px !important; }
}

@media (max-width: 980px) {
    #sidebar {
        flex-basis: 258px !important;
        width: 258px !important;
        min-width: 258px !important;
        max-width: 258px !important;
    }

    #chat-header {
        padding: 0 18px !important;
    }
}

@media (max-width: 760px) {
    #sidebar {
        flex-basis: 230px !important;
        width: 230px !important;
        min-width: 230px !important;
        max-width: 230px !important;
    }

    #chat-header p,
    .brand p {
        display: none !important;
    }

    #chatbot .messages,
    #chatbot .scroll-hide,
    #selection-chips,
    #composer {
        padding-left: 12px !important;
        padding-right: 12px !important;
    }
}

/* Refined authentication screen */
#auth-shell {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 28px !important;
    background:
        linear-gradient(125deg, rgba(255, 247, 230, .98), rgba(247, 200, 211, .82) 38%, rgba(169, 183, 198, .68) 72%, rgba(168, 181, 138, .50)) !important;
}

#auth-shell::before {
    width: 420px !important;
    height: 420px !important;
    left: -90px !important;
    top: -130px !important;
    background:
        radial-gradient(circle at 38% 38%, rgba(255, 255, 255, .72), transparent 36%),
        linear-gradient(145deg, rgba(247, 200, 211, .90), rgba(180, 106, 114, .54)) !important;
    filter: blur(18px) !important;
    box-shadow: none !important;
    opacity: .88 !important;
}

#auth-shell::after {
    width: 520px !important;
    height: 520px !important;
    right: -170px !important;
    bottom: -210px !important;
    background:
        radial-gradient(circle at 42% 38%, rgba(255, 255, 255, .42), transparent 34%),
        linear-gradient(145deg, rgba(169, 183, 198, .72), rgba(168, 181, 138, .58)) !important;
    filter: blur(24px) !important;
    opacity: .82 !important;
}

#auth-card {
    width: min(430px, calc(100vw - 34px)) !important;
    padding: 30px 30px 26px !important;
    border: 1px solid rgba(255, 255, 255, .78) !important;
    border-radius: 26px !important;
    background:
        linear-gradient(145deg, rgba(255, 255, 255, .52), rgba(255, 247, 230, .28)) !important;
    box-shadow:
        0 28px 70px rgba(45, 58, 71, .18),
        inset 0 1px 0 rgba(255, 255, 255, .88) !important;
    backdrop-filter: blur(28px) saturate(135%) !important;
    -webkit-backdrop-filter: blur(28px) saturate(135%) !important;
}

#auth-card h1 {
    margin-bottom: 8px !important;
    font-size: 2rem !important;
    letter-spacing: -.035em !important;
}

#auth-card .auth-copy {
    margin-bottom: 20px !important;
    color: rgba(45, 58, 71, .72) !important;
    line-height: 1.55 !important;
}

#auth-card .form,
#auth-card .block,
#auth-card .wrap,
#auth-card .container,
#auth-card .panel {
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

#auth-card [role="radiogroup"] {
    display: inline-flex !important;
    width: fit-content !important;
    min-width: 0 !important;
    gap: 4px !important;
    margin: 0 0 16px !important;
    padding: 4px !important;
    border: 1px solid rgba(180, 106, 114, .18) !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, .30) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .65) !important;
}

#auth-card [role="radiogroup"] label {
    position: relative !important;
    min-height: 34px !important;
    margin: 0 !important;
    padding: 7px 13px !important;
    border: 0 !important;
    border-radius: 9px !important;
    background: transparent !important;
    color: rgba(45, 58, 71, .72) !important;
    font-size: .86rem !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    cursor: pointer !important;
}

#auth-card [role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(135deg, var(--rosewood), #ca8793) !important;
    color: #fff !important;
    box-shadow: 0 7px 16px rgba(180, 106, 114, .20) !important;
}

#auth-card [role="radiogroup"] input {
    position: absolute !important;
    width: 1px !important;
    height: 1px !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

#auth-card [role="radiogroup"] label span {
    color: inherit !important;
}

#auth-card label {
    color: var(--midnight-lagoon) !important;
    font-size: .84rem !important;
    font-weight: 700 !important;
}

#auth-card input,
#auth-card textarea {
    min-height: 48px !important;
    border: 1px solid rgba(180, 106, 114, .22) !important;
    border-radius: 12px !important;
    background: rgba(255, 255, 255, .62) !important;
    color: var(--midnight-lagoon) !important;
    box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, .88),
        0 7px 18px rgba(45, 58, 71, .06) !important;
}

#auth-card input::placeholder {
    color: rgba(45, 58, 71, .44) !important;
}

#auth-card button.primary {
    min-height: 46px !important;
    margin-top: 6px !important;
    border: 1px solid rgba(180, 106, 114, .20) !important;
    border-radius: 12px !important;
    background: linear-gradient(135deg, var(--rosewood), #cf8796) !important;
    color: #fff !important;
    font-weight: 760 !important;
    box-shadow: 0 13px 28px rgba(180, 106, 114, .25) !important;
}

#auth-card button.primary:hover {
    transform: translateY(-1px) !important;
    background: linear-gradient(135deg, #a95f69, #d7929f) !important;
}

@media (max-width: 620px) {
    #auth-shell {
        padding: 16px !important;
    }

    #auth-card {
        width: 100% !important;
        padding: 25px 22px 22px !important;
        border-radius: 22px !important;
    }

    #auth-shell::before {
        width: 300px !important;
        height: 300px !important;
    }

    #auth-shell::after {
        width: 360px !important;
        height: 360px !important;
    }
}



#attach-button {
    flex: 0 0 46px !important;
    width: 46px !important;
    min-width: 46px !important;
}

#attach-button button {
    width: 46px !important;
    min-width: 46px !important;
    height: 46px !important;
    min-height: 46px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(180, 106, 114, .28) !important;
    background: rgba(247, 200, 211, .45) !important;
    color: #2d3a47 !important;
    font-size: 1.35rem !important;
}

.document-failure {
    margin-top: 4px;
    color: #9b4f5b;
    font-size: .62rem;
    line-height: 1.3;
}

#document-open-file {
    display: none !important;
}

.document-inline-card {
    gap: 2px !important;
    margin-bottom: 7px !important;
    padding: 8px 9px 7px !important;
    border: 1px solid rgba(180, 106, 114, .17) !important;
    border-radius: 11px !important;
    background: rgba(255, 255, 255, .48) !important;
}

.document-inline-card .document-card-info {
    display: grid !important;
    grid-template-columns: 32px minmax(0, 1fr) auto !important;
    gap: 8px !important;
    align-items: center !important;
    padding: 0 !important;
    border: 0 !important;
    background: transparent !important;
}

.document-inline-actions {
    min-height: 25px !important;
    margin: -1px 0 0 40px !important;
    gap: 9px !important;
    align-items: center !important;
}

.document-inline-actions button {
    min-height: 21px !important;
    height: 21px !important;
    padding: 0 !important;
    box-shadow: none !important;
}

.document-text-action button {
    width: auto !important;
    min-width: 0 !important;
    border: 0 !important;
    background: transparent !important;
    color: #7c5960 !important;
    font-size: .58rem !important;
    font-weight: 650 !important;
    text-decoration: underline !important;
    text-underline-offset: 2px !important;
}

.document-text-action button:hover {
    color: #b46a72 !important;
}

.document-delete-action button {
    color: #9b4f5b !important;
}

.document-retry-action button {
    width: 24px !important;
    min-width: 24px !important;
    height: 24px !important;
    min-height: 24px !important;
    border: 1px solid rgba(180, 106, 114, .30) !important;
    border-radius: 999px !important;
    background: rgba(247, 200, 211, .38) !important;
    color: #9b4f5b !important;
    font-size: .9rem !important;
    line-height: 1 !important;
}

.document-retry-action button:hover {
    background: rgba(247, 200, 211, .72) !important;
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


def friendly_document_failure(document: dict[str, Any]) -> str:
    message = safe_text(document.get("failure_message"))
    code = safe_text(document.get("failure_code")).lower()
    blocked = (
        "sqlalchemy",
        "asyncpg",
        "integrityerror",
        "uniqueviolation",
        "traceback",
        "insert into",
        "parameters:",
    )

    if code == "ocr_required" and message:
        return message
    if message and not any(item in message.lower() for item in blocked):
        return message
    if code == "delete_failed":
        return "The document could not be deleted. Please try again."
    return "Processing failed. Retry the document."


def render_document_card_info(document: dict[str, Any]) -> str:
    """Render document metadata used by the dynamic document list"""

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
    failure_message = friendly_document_failure(document)
    failure_html = (
        f'<div class="document-failure">{html.escape(failure_message)}</div>'
        if status_key in {"failed", "error"} and failure_message
        else ""
    )

    return (
        '<div class="document-card-info">'
        f'<div class="document-icon">{html.escape(document_icon(filename))}</div>'
        '<div class="document-info">'
        f'<div class="document-name" title="{html.escape(filename)}">{html.escape(filename)}</div>'
        f'<div class="document-meta">{html.escape(meta)}</div>'
        f"{failure_html}"
        "</div>"
        f'<span class="status-badge status-{status_class}">'
        '<span class="status-dot"></span>'
        f"{html.escape(status_label)}</span>"
        "</div>"
    )


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
        '<button type="button" class="prompt-pill" data-prompt="Summarize the key findings">Summarize the key findings</button>'
        '<button type="button" class="prompt-pill" data-prompt="Compare the uploaded reports">Compare the uploaded reports</button>'
        '<button type="button" class="prompt-pill" data-prompt="List decisions and action items">List decisions and action items</button>'
        '<button type="button" class="prompt-pill" data-prompt="Find evidence for a claim">Find evidence for a claim</button>'
        "</div></div>"
    )


def document_updates(
    documents: list[dict[str, Any]],
    selected_ids: list[str] | None = None,
):
    catalog: dict[str, str] = {}
    ready_choices: list[tuple[str, str]] = []

    for document in documents:
        filename = safe_text(document.get("filename")) or "Untitled document"
        document_id = safe_text(document.get("id"))
        if not document_id:
            continue
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
        None,
        documents,
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
    if current.get("__cancel_delete"):
        current = {key: value for key, value in current.items() if key != "__cancel_delete"}
        outputs = load_documents(current, selected_ids)
        return (*outputs, "")

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


def prepare_document_open(
    state: dict[str, Any] | None,
    document_id: str | None,
):
    """Fetch an owned document and prepare browser-inline preview data"""

    current = state or empty_state()
    clean_id = safe_text(document_id)
    if not clean_id:
        return "", toast("info", "Document unavailable", "No document was selected.")

    try:
        response = httpx.get(
            f"{BACKEND_URL}/documents/{clean_id}/content",
            headers=auth_headers(current),
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError:
        return "", toast("error", "Open failed", backend_unavailable())

    if response.status_code != 200:
        return "", toast("error", "Open failed", friendly_api_error(response))

    disposition = response.headers.get("content-disposition", "")
    filename_match = re.search(r'filename="?([^";]+)', disposition, flags=re.IGNORECASE)
    filename = filename_match.group(1).strip() if filename_match else f"document-{clean_id}"
    filename = Path(filename).name or f"document-{clean_id}"
    media_type = response.headers.get("content-type") or ""
    media_type = media_type.split(";", 1)[0].strip().lower()
    guessed_type = mimetypes.guess_type(filename)[0]
    if not media_type or media_type == "application/octet-stream":
        media_type = guessed_type or "application/octet-stream"
    payload = {
        "name": filename,
        "mime": media_type or "application/octet-stream",
        "data": base64.b64encode(response.content).decode("ascii"),
    }
    return json.dumps(payload), toast("success", "Opening document", filename)


def upload_chat_attachments(
    state: dict[str, Any] | None,
    files: list[Any] | Any | None,
    selected_ids: list[str] | None,
):
    current = state or empty_state()
    selected = [safe_text(item) for item in (selected_ids or []) if safe_text(item)]
    paths = normalize_files(files)

    if not current.get("access_token"):
        outputs = load_documents(current, selected)
        return (*outputs, toast("error", "Session expired", "Please log in again."))

    if not paths:
        outputs = load_documents(current, selected)
        return (*outputs, toast("info", "No attachment", "Choose a document to attach."))

    attached_ids: list[str] = []
    failures: list[str] = []
    for path in paths:
        try:
            with path.open("rb") as handle:
                response = httpx.post(
                    f"{BACKEND_URL}/documents/upload",
                    headers=auth_headers(current),
                    files={"file": (path.name, handle, "application/octet-stream")},
                    timeout=REQUEST_TIMEOUT,
                )
        except (OSError, httpx.HTTPError):
            failures.append(path.name)
            continue

        if response.status_code in {200, 201}:
            document_id = safe_text(response.json().get("id"))
            if document_id:
                attached_ids.append(document_id)
        else:
            failures.append(f"{path.name}: {friendly_api_error(response)}")

    updated_selected = list(dict.fromkeys([*selected, *attached_ids]))
    outputs = load_documents(current, updated_selected)
    if failures:
        return (
            *outputs,
            toast("info", "Attachment upload completed", "; ".join(failures[:3])),
        )
    return (
        *outputs,
        toast(
            "success",
            "Attached to chat",
            f"{len(attached_ids)} document(s) are ready for this chat.",
        ),
    )


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


def transcribe_voice(
    audio_path: str | None,
    question: str | None,
    state: dict[str, Any] | None,
):
    current = state or empty_state()
    current_question = safe_text(question)

    yield (
        True,
        gr.update(value=current_question, interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        render_voice_status("transcribing"),
        toast(
            "working",
            "Transcribing",
            "Converting your recording into text.",
        ),
        gr.update(),
    )

    path = Path(audio_path) if audio_path else None

    if not path or not path.exists():
        yield (
            False,
            gr.update(value=current_question, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            render_voice_status(
                "error",
                "No recording was received. Try recording again.",
            ),
            toast(
                "error",
                "No recording",
                "Record a voice prompt, then press stop.",
            ),
            gr.update(value=None, interactive=True),
        )
        return

    mime_type = mimetypes.guess_type(path.name)[0] or "audio/wav"

    try:
        with path.open("rb") as audio_file:
            response = httpx.post(
                STT_API_URL,
                headers=(auth_headers(current) if current.get("access_token") else {}),
                files={
                    "file": (
                        path.name,
                        audio_file,
                        mime_type,
                    )
                },
                timeout=STT_TIMEOUT,
            )
    except (OSError, httpx.HTTPError):
        yield (
            False,
            gr.update(value=current_question, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            render_voice_status(
                "error",
                "The transcription service could not be reached.",
            ),
            toast(
                "error",
                "Transcription failed",
                "Make sure FastAPI is running and try again.",
            ),
            gr.update(value=None, interactive=True),
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
            toast(
                "error",
                "Transcription failed",
                message,
            ),
            gr.update(value=None, interactive=True),
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
            render_voice_status(
                "error",
                "The service returned an empty transcript.",
            ),
            toast(
                "error",
                "Nothing was transcribed",
                "Try speaking more clearly or recording again.",
            ),
            gr.update(value=None, interactive=True),
        )
        return

    merged = f"{current_question} {transcript}".strip() if current_question else transcript

    yield (
        False,
        gr.update(value=merged, interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        render_voice_status("ready"),
        toast(
            "success",
            "Voice prompt ready",
            "The transcript was added to the message box.",
        ),
        gr.update(value=None, interactive=True),
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
                    documents_state = gr.State([])
                    manage_document = gr.State(None)
                    document_list_container = gr.Column(elem_id="document-cards")
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
                    attach_button = gr.UploadButton(
                        "+",
                        file_count="multiple",
                        file_types=SUPPORTED_FILE_TYPES,
                        variant="secondary",
                        scale=0,
                        min_width=54,
                        elem_id="attach-button",
                    )
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

    document_open_file = gr.Textbox(visible=False, elem_id="document-open-file")

    with document_list_container:

        @gr.render(inputs=[documents_state])
        def render_document_library(documents: list[dict[str, Any]] | None):
            current_documents = documents or []
            if not current_documents:
                gr.HTML(
                    '<div class="document-empty">No documents yet.<br>'
                    "Upload a PDF, DOCX, TXT, MD, or JSON file.</div>"
                )
                return

            for document in current_documents:
                document_id = safe_text(document.get("id"))
                if not document_id:
                    continue
                status_key = document_status(document)
                retryable = bool(document.get("retryable"))

                with gr.Column(
                    key=f"document-{document_id}",
                    elem_classes=["document-inline-card"],
                ):
                    gr.HTML(render_document_card_info(document))
                    with gr.Row(elem_classes=["document-inline-actions"]):
                        view_button = gr.Button(
                            "View",
                            size="sm",
                            scale=0,
                            min_width=42,
                            key=f"view-{document_id}",
                            elem_classes=["document-text-action"],
                        )
                        if status_key in {"failed", "error"} and retryable:
                            retry_button = gr.Button(
                                "↻",
                                size="sm",
                                scale=0,
                                min_width=28,
                                key=f"retry-{document_id}",
                                elem_classes=["document-retry-action"],
                            )
                        else:
                            retry_button = None
                        delete_button = gr.Button(
                            "Delete",
                            size="sm",
                            scale=0,
                            min_width=46,
                            key=f"delete-{document_id}",
                            elem_classes=["document-text-action", "document-delete-action"],
                        )

                def open_inline(state, doc_id=document_id):
                    return prepare_document_open(state, doc_id)

                open_event = view_button.click(
                    open_inline,
                    inputs=[auth_state],
                    outputs=[document_open_file, toast_box],
                    show_progress="minimal",
                )
                open_event.then(
                    fn=None,
                    inputs=[document_open_file],
                    outputs=[],
                    js="""(raw) => {
                        if (!raw) return;
                        const file = JSON.parse(raw);
                        const bytes = Uint8Array.from(atob(file.data), c => c.charCodeAt(0));
                        const lowerName = (file.name || '').toLowerCase();
                        let mime = file.mime || 'application/octet-stream';
                        if (lowerName.endsWith('.pdf')) mime = 'application/pdf';
                        else if (lowerName.endsWith('.txt') || lowerName.endsWith('.md')) mime = 'text/plain';
                        else if (lowerName.endsWith('.json')) mime = 'application/json';
                        const blob = new Blob([bytes], {type: mime});
                        const url = URL.createObjectURL(blob);
                        const opened = window.open(url, '_blank', 'noopener,noreferrer');
                        if (!opened) window.location.href = url;
                        setTimeout(() => URL.revokeObjectURL(url), 60000);
                    }""",
                )

                if retry_button is not None:

                    def retry_inline(state, selected, doc_id=document_id):
                        yield from reprocess_document(state, doc_id, selected)

                    retry_button.click(
                        retry_inline,
                        inputs=[auth_state, selected_documents],
                        outputs=[
                            selected_documents,
                            manage_document,
                            documents_state,
                            document_catalog,
                            empty_panel,
                            selection_chips,
                            toast_box,
                        ],
                        show_progress="hidden",
                    )

                def delete_inline(state, selected, doc_id=document_id):
                    return delete_document(state, doc_id, selected)

                confirm_text = json.dumps(
                    f"Delete {safe_text(document.get('filename')) or 'this document'}? "
                    "This cannot be undone."
                )
                delete_button.click(
                    delete_inline,
                    inputs=[auth_state, selected_documents],
                    outputs=[
                        selected_documents,
                        manage_document,
                        documents_state,
                        document_catalog,
                        empty_panel,
                        selection_chips,
                        toast_box,
                    ],
                    js=f"""(state, selected) => {{
                        if (!window.confirm({confirm_text})) {{
                            return [{{...(state || {{}}), __cancel_delete: true}}, selected];
                        }}
                        return [state, selected];
                    }}""",
                    show_progress="minimal",
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
            documents_state,
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
            documents_state,
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
            documents_state,
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
            documents_state,
            document_catalog,
            empty_panel,
            selection_chips,
            toast_box,
        ],
        show_progress="hidden",
    )

    attach_button.upload(
        upload_chat_attachments,
        inputs=[auth_state, attach_button, selected_documents],
        outputs=[
            selected_documents,
            manage_document,
            documents_state,
            document_catalog,
            empty_panel,
            selection_chips,
            toast_box,
        ],
        show_progress="minimal",
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
        inputs=[
            voice_recorder,
            question_input,
            auth_state,
        ],
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


    # Keep the original prompt-pill UI and make those pills fill the existing composer
    demo.load(
        fn=None,
        inputs=[],
        outputs=[],
        js="""() => {
            if (window.__ragPromptPillsBound) return;
            window.__ragPromptPillsBound = true;
            document.addEventListener('click', (event) => {
                const pill = event.target.closest('.prompt-pill[data-prompt]');
                if (!pill) return;
                const textarea = document.querySelector('#question-input textarea');
                if (!textarea) return;
                const value = pill.dataset.prompt || pill.textContent || '';
                const setter = Object.getOwnPropertyDescriptor(
                    HTMLTextAreaElement.prototype,
                    'value'
                ).set;
                setter.call(textarea, value.trim());
                textarea.dispatchEvent(new Event('input', {bubbles: true}));
                textarea.dispatchEvent(new Event('change', {bubbles: true}));
                textarea.focus();
            });
        }""",
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    demo.queue(default_concurrency_limit=8).launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=False,
        inbrowser=False,
        theme=THEME,
        css=CSS,
    )
