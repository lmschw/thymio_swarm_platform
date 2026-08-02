"""
Contains methods to retrieve robots in a normalised form
"""
from typing import Any, Dict, List, Union

from swarm_platform.controller.client import SwarmClient


def normalize_robots(
    robots: Union[Dict[str, Dict[str, Any]], List[Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalises the robots into the general dictionary format.

    Args:
        robots: The robots to be normalised. Supports both:
            - dict: {id: robot}
            - list: [{robot_id, ip, port}]

    Returns:
        A dictionary with the robot's hostname as its key and the robot
        data as the value.
    """
    if isinstance(robots, dict):
        return robots

    return {
        r["robot_id"]: r
        for r in robots
    }

async def get_robots(client: SwarmClient) -> Dict[str, Dict[str, Any]]:
    """
    Retrieves the available robots from the client.

    Args:
        client: The swarm client instance that connects to the
            coordinator.

    Returns:
        A dictionary with the robot's hostname as its key and the robot
        data as the value.
    """
    robots_raw = await client.list_robots()
    return normalize_robots(robots_raw)

def print_robots(robots: Dict[str, Dict[str, Any]]) -> None:
    """
    Prints a summary of all robots with its hostname as well as its IP and port.

    Args:
        robots: A dictionary of the robots with their hostname as the
            keys.
    """
    print(f"\nFound {len(robots)} robots\n")

    for robot_id, robot in robots.items():
        print(f"  {robot_id}: {robot['ip']}:{robot.get('port', 9000)}")