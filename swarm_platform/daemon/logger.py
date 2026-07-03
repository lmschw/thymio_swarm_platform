import json
import time
from pathlib import Path

class SessionLogger:
    def __init__(self, session_id: str, robot_id: str, base_dir="logs"):
        self.session_id = session_id
        self.robot_id = robot_id

        self.path = Path(base_dir)
        self.path.mkdir(parents=True, exist_ok=True)

        self.file = open(
            self.path / f"{session_id}-{robot_id}.jsonl",
            "a"
        )

    def log(self, state=None, command=None):
        entry = {
            "t": time.time(),
            "session": self.session_id,
            "robot": self.robot_id,
            "state": state,
            "command": command,
        }

        self.file.write(json.dumps(entry) + "\n")
        self.file.flush()

    def close(self):
        self.file.close()