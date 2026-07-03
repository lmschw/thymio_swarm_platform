from typing import Protocol


class ProjectProvider(Protocol):

    def experiment(self, name: str) -> type:
        pass

    def list_experiments(self) -> list[str]:
        pass

    def reload(self) -> None:
        pass