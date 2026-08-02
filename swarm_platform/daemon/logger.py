import csv
from typing import Any, Dict, List, Optional


class SessionLogger:
    """Writes per-tick robot state/command rows to a CSV file for a session.

    The CSV header is inferred from the keys of the first logged row, so all
    subsequent rows are expected to share the same keys.
    """

    def __init__(self, path: str) -> None:
        """Open the log file for writing and prepare the CSV writer.

        Args:
            path: Filesystem path of the CSV file to create/overwrite.
        """
        self.file = open(path, "w", newline="")
        self.writer = csv.writer(self.file)
        self.header: Optional[List[str]] = None

    def log(self, state: Dict[str, Any], command: Dict[str, Any]) -> None:
        """Write one row combining a state and a command mapping to the CSV file.

        On the first call, the combined keys of `state` and `command` are used
        as the CSV header. The file is flushed after every write.

        Args:
            state: Mapping of state field names to values (e.g. robot sensor
                readings) to merge into the row.
            command: Mapping of command field names to values (e.g. motor
                speeds) to merge into the row.
        """
        row = {}

        row.update(state)
        row.update(command)

        if self.header is None:
            self.header = list(row.keys())
            self.writer.writerow(self.header)

        self.writer.writerow(
            [row[k] for k in self.header]
        )

        self.file.flush()

    def close(self) -> None:
        """Close the underlying log file."""
        self.file.close()