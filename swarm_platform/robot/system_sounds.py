from enum import IntEnum


class SystemSound(IntEnum):
    """Identifiers for the built-in Thymio system sounds that can be played by a robot."""

    TARGET_OK = 0
    TARGET_ERROR = 1
    BUTTON = 2
    STARTUP = 3
    SHUTDOWN = 4