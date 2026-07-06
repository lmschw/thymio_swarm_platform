from pathlib import Path


class LogManager:

    def __init__(self, root="logs"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def session_dir(self, session_id: str) -> Path:
        path = self.root / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def robot_log(self, session_id: str, robot_id: str) -> Path:
        return self.session_dir(session_id) / f"{robot_id}.csv"

    def read(self, session_id: str, robot_id: str) -> str | None:
        path = self.robot_log(session_id, robot_id)

        if not path.exists():
            return None

        return path.read_text()

    def delete(self, session_id: str):

        directory = self.root / session_id

        if not directory.exists():
            return

        for file in directory.iterdir():
            file.unlink()

        directory.rmdir()

    def list_sessions(self):
        return sorted(
            p.name
            for p in self.root.iterdir()
            if p.is_dir()
        )