from typing import Optional


class RobotConnectionError(Exception):
    """Raised when a connection to a robot cannot be established or is lost."""

    def __init__(self, message: str, cause: Optional[BaseException] = None) -> None:
        """Initialize the error.

        Args:
            message: Human-readable description of the connection failure.
            cause: The underlying exception that triggered this error, if any.
        """
        super().__init__(message)
        self.cause = cause


class CameraError(Exception):
    """Raised when a camera operation is attempted but no camera is available."""