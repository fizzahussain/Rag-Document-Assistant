import re
from enum import StrEnum


class ChatIntent(StrEnum):
    GREETING = "greeting"
    THANKS = "thanks"
    FAREWELL = "farewell"
    CALCULATION = "calculation"
    DOCUMENT = "document"


_GREETING_RE = re.compile(
    r"^(hi|hello|hey|hiya|good morning|good afternoon|good evening|howdy)[!.? ]*$",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(r"^(thanks|thank you|thx|ty)[!.? ]*$", re.IGNORECASE)
_FAREWELL_RE = re.compile(r"^(bye|goodbye|see you|see ya|take care)[!.? ]*$", re.IGNORECASE)
_CALCULATION_RE = re.compile(r"^[\d\s+\-*/().%^]+$")


def classify_intent(message: str) -> ChatIntent:
    """Classify lightweight intents that should bypass document retrieval"""

    text = " ".join(message.strip().split())
    if _GREETING_RE.fullmatch(text):
        return ChatIntent.GREETING
    if _THANKS_RE.fullmatch(text):
        return ChatIntent.THANKS
    if _FAREWELL_RE.fullmatch(text):
        return ChatIntent.FAREWELL
    if text and _CALCULATION_RE.fullmatch(text) and any(char.isdigit() for char in text):
        return ChatIntent.CALCULATION
    return ChatIntent.DOCUMENT


def direct_response(intent: ChatIntent) -> str | None:
    """Return a natural direct response for non-document intents"""

    if intent == ChatIntent.GREETING:
        return "Hi! What would you like to explore in your documents?"
    if intent == ChatIntent.THANKS:
        return "You're welcome! Ask another question whenever you're ready."
    if intent == ChatIntent.FAREWELL:
        return "Goodbye! Your documents and conversation history will be here when you return."
    if intent == ChatIntent.CALCULATION:
        return (
            "That looks like a calculation rather than a question grounded in your uploaded "
            "documents. I keep answers document-focused, so no document retrieval is needed for it."
        )
    return None
