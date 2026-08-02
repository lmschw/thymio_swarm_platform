import csv
import time
from pathlib import Path
from typing import IO, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from swarm_platform.protocol.command import RobotCommand
    from swarm_platform.robot.state import RobotState


class CSVLogger:
    """Writes robot state/command rows to a CSV file, one row per logged tick.

    The CSV header (based on the number of proximity sensors) is written on
    the first call to `log`.
    """

    def __init__(self, path: str) -> None:
        """Store the target path; the file itself is opened by `start`.

        Args:
            path: Filesystem path of the CSV file to write to.
        """
        self.path = Path(path)
        self.file: Optional[IO[str]] = None
        self.writer: Optional["csv._writer"] = None

    def start(self) -> None:
        """Create the parent directory if needed and open the CSV file for writing.

        Resets the writer so the header is (re)written on the next `log` call.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "w", newline="")
        self.writer = None

    def log(self, state: "RobotState", command: "RobotCommand") -> None:
        """Write one row of sensor state and motor command to the CSV file.

        On the first call, writes a header row sized to the number of
        proximity sensors in `state`.

        Args:
            state: The robot's current sensor state (uses `proximity` and
                `temperature`).
            command: The motor command issued for this tick (uses
                `left_motor` and `right_motor`).
        """
        if self.writer is None:
            headers = (
                ["time"]
                + [f"prox_{i}" for i in range(len(state.proximity))]
                + ["temp", "left", "right"]
            )
            self.writer = csv.writer(self.file)
            self.writer.writerow(headers)

        row = (
            [time.time()]
            + list(state.proximity)
            + [state.temperature]
            + [command.left_motor, command.right_motor]
        )

        self.writer.writerow(row)

    def stop(self) -> None:
        """Close the underlying file, if it was opened."""
        if self.file:
            self.file.close()