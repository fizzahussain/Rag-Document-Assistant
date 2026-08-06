from pydantic import BaseModel, Field


class AudioTranscriptionResponse(BaseModel):
    """Return transcribed text and detected audio information"""

    text: str = Field(
        min_length=1,
        description="Text transcribed from the uploaded audio",
    )
    language: str | None = Field(
        default=None,
        description="Detected or configured language code",
    )
    language_probability: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Confidence in the detected language",
    )
    duration_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Duration of the uploaded audio",
    )
    execution_time_seconds: float = Field(
        ge=0,
        description="Time spent transcribing the audio",
    )
