from swarm_platform.controller.session import SwarmSession

class Project:

    def __init__(self, client, repository: str, hosts: list):
        self.client = client
        self.repository = repository
        self.hosts = hosts

        name = repository.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]

        self.name = name

    async def install(self):
        responses = await self.client.broadcast({
            "type": "clone_project",
            "repository": self.repository,
            "hosts": self.hosts,
        })
        self.client._check_results(
            "Project installation",
            responses,
        )
        await self.activate()

    async def update(self):
        responses = await self.client.broadcast({
            "type": "update_project",
            "hosts": self.hosts,
        })
        self.client._check_results(
            "Project update",
            responses,
        )
        await self.activate()

    async def activate(self):
        responses = await self.client.broadcast({
            "type": "activate_project",
            "hosts": self.hosts,
        })
        self.client._check_results(
            "Project activation",
            responses,
        )

    def session(self, name=None):
        return SwarmSession(
            self.client,
            project=self,
            name=name,
        )