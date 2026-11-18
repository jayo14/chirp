from fastapi import Request, status
from fastapi.responses import JSONResponse


class ChirpException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AssignmentNotFoundException(ChirpException):
    def __init__(self, identifier: str):
        super().__init__(
            message=f"Assignment with identifier '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedAdminException(ChirpException):
    def __init__(self, jid: str):
        super().__init__(
            message=f"WhatsApp JID '{jid}' is not authorized to perform administrative actions.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


async def chirp_exception_handler(request: Request, exc: ChirpException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_type": exc.__class__.__name__,
            "message": exc.message,
            "path": request.url.path,
        },
    )
