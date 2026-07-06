from swarm_platform.controller.session import SwarmSession


class Project:

    def __init__(self, client, repository: str):
        self.client = client
        self.repository = repository

        name = repository.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]

        self.name = name

    async def install(self):
        """
        Clone the repository onto every robot and activate it.
        """

        print(f"Installing project '{self.name}'")

        await self.client.broadcast({
            "type": "clone_project",
            "repository": self.repository,
        })

        await self.activate()

    async def update(self):
        """
        Pull the latest version, install dependencies and activate it.
        """

        print(f"Updating project '{self.name}'")

        await self.client.broadcast({
            "type": "update_project",
            "project": self.name,
        })

        await self.activate()

    async def activate(self):

        responses = await self.client.broadcast({
            "type": "activate_project",
            "project": self.name,
        })

        failures = {
            robot: response["error"]
            for robot, response in responses.items()
            if response.get("type") == "error"
        }

        if failures:
            message = "\n".join(
                f"  {robot}: {error}"
                for robot, error in failures.items()
            )

            raise RuntimeError(
                f"Could not activate project '{self.name}':\n{message}"
            )

        return responses

    def session(self, name=None):
        return SwarmSession(
            self.client,
            project=self,
            name=name,
        )