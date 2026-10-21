"""Domain errors. Each maps to one HTTP status and a {detail, code} body."""

from typing import Any


class RedCardError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, detail: str, extra: dict[str, Any] | None = None,
                 headers: dict[str, str] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra or {}
        self.headers = headers

    def body(self) -> dict[str, Any]:
        return {"detail": self.detail, "code": self.code, **self.extra}


class LanguageNotFoundError(RedCardError):
    status_code = 404
    code = "language_not_found"

    def __init__(self, code: str):
        super().__init__(f"Language not found: {code}")


class FontNotAvailableError(RedCardError):
    status_code = 400
    code = "font_not_available"

    def __init__(self, script: str, language: str):
        super().__init__(
            f"PDF rendering is not available for {language} ({script} script).",
            # error_type is kept for clients written against earlier versions.
            extra={"error_type": "font_not_available", "script": script, "language": language},
        )


class ServiceNotReadyError(RedCardError):
    status_code = 503
    code = "not_ready"

    def __init__(self):
        super().__init__("Service is starting up. Please try again in a moment.")


class RenderTimeoutError(RedCardError):
    status_code = 503
    code = "render_timeout"

    def __init__(self):
        super().__init__("PDF rendering took too long. Please try again.")


class RateLimitedError(RedCardError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, retry_after: int):
        super().__init__(
            "Too many PDF requests. Please wait a minute and try again.",
            headers={"Retry-After": str(retry_after)},
        )


class PDFRenderError(RedCardError):
    status_code = 500
    code = "render_failed"

    def __init__(self):
        # Never echo the underlying exception to clients; it is logged instead.
        super().__init__("PDF generation failed.")
