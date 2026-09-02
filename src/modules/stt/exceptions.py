"""STT module exceptions."""

from src.core.exceptions import AppException


class SttError(AppException):
    pass


class TranscriptionError(SttError):
    def __init__(self, detail: str = "Transcription failed"):
        super().__init__(status_code=500, detail=detail)
