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
        print(f"Installing '{self.name}'")
        responses = await self.client.broadcast({
            "type": "clone_project",
            "repository": self.repository,
        })
        self.client._check_results("Project installation", responses)
        await self.activate()

    async def update(self):
        print(f"Updating '{self.name}'")
        responses = await self.client.broadcast({
            "type": "update_project",
            "project": self.name,
        })
        self.client._check_results("Project update", responses)
        await self.activate()

    async def activate(self):
        responses = await self.client.broadcast({
            "type": "activate_project",
            "project": self.name,
        })
        self.client._check_results("Project activation", responses)
        return responses

    def session(self, name=None):
        return SwarmSession(
            self.client,
            project=self,
            name=name,
        )