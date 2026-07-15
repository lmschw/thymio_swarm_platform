import asyncio
import csv

from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.utils import save_robot_info_to_csv

async def main():

    client = SwarmClient("10.15.2.63")
    await save_robot_info_to_csv(client)

asyncio.run(main())