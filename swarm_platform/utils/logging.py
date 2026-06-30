import csv
import time
from pathlib import Path

class CSVLogger:

    def __init__(self, path: str):
        self.path = Path(path)
        self.file = None
        self.writer = None

    def start(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "w", newline="")
        self.writer = None

    def log(self, state, command):
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

    def stop(self):
        if self.file:
            self.file.close()