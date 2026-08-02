"""Manual task script: connect to the coordinator and save known robots' hostnames/IPs to a CSV file."""

import asyncio
import csv

from swarm_platform.controller.client import SwarmClient
from swarm_platform.utils.utils import save_robot_info_to_csv


async def main() -> None:
    """Connect to the coordinator and write the known robots' hostname/IP to a CSV file."""

    client = SwarmClient("10.15.2.63")
    await save_robot_info_to_csv(client)

asyncio.run(main())