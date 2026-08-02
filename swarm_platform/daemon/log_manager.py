from pathlib import Path
from typing import List, Optional, Union


class LogManager:
    """Manages the on-disk directory layout for per-session, per-robot log files."""

    def __init__(self, root: Union[str, Path] = "logs") -> None:
        """Initialize the manager and ensure the root log directory exists.

        Args:
            root: Path to the root directory under which session directories
                are created.
        """
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        """Get (creating if necessary) the directory for a given session.

        Args:
            session_id: Identifier of the session.

        Returns:
            The path to the session's log directory.
        """
        path = self.root / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def robot_log(self, session_id: str, robot_id: str) -> Path:
        """Get the path of a robot's CSV log file within a session.

        Args:
            session_id: Identifier of the session.
            robot_id: Identifier of the robot.

        Returns:
            The path to the robot's CSV log file (which may not yet exist).
        """
        return self.session_dir(session_id) / f"{robot_id}.csv"

    def read(self, session_id: str, robot_id: str) -> Optional[str]:
        """Read the full contents of a robot's log file for a session.

        Args:
            session_id: Identifier of the session.
            robot_id: Identifier of the robot.

        Returns:
            The text content of the log file, or None if it does not exist.
        """
        path = self.robot_log(session_id, robot_id)

        if not path.exists():
            return None

        return path.read_text()

    def delete(self, session_id: str) -> None:
        """Delete all log files and the directory for a session, if it exists.

        Args:
            session_id: Identifier of the session whose logs should be deleted.
        """

        directory = self.root / session_id

        if not directory.exists():
            return

        for file in directory.iterdir():
            file.unlink()

        directory.rmdir()

    def list_sessions(self) -> List[str]:
        """List the identifiers of all sessions with a log directory.

        Returns:
            The session directory names, sorted alphabetically.
        """
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir()
        )