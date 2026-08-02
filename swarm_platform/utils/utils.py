import csv
import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swarm_platform.controller.client import SwarmClient


async def save_robot_info_to_csv(client: "SwarmClient") -> None:
    """Fetch known robots from the coordinator and save their hostname/IP to a CSV file.

    The output file is named `thymio_ips_<date>_<time>.csv`, with the date and
    time taken from the moment the file is written.

    Args:
        client: The swarm client used to list the currently known robots.
    """
    robots = await client.list_robots()
    data = [{"hostname": hostname, "ip": robots[hostname]["ip"]} for hostname in robots.keys()]

    now = datetime.datetime.now()
    time = str(now.time()).replace(":", "")

    with open(f"thymio_ips_{now.date()}_{time}.csv", "w", newline="") as csv_file:
        fieldnames = ["hostname", "ip"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

