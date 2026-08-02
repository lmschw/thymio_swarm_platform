"""
Contains methods to retrieve robots in a normalised form
"""
def normalize_robots(robots):
    """
    Normalises the robots into the general dictionary format.

    Params:
        - robots [list or dict]: the robots to be normalised

    Supports both:
    - dict: {id: robot}
    - list: [{robot_id, ip, port}]

    Returns a dictionary with the robot's hostname as its key and the robot data as the value.
    """
    if isinstance(robots, dict):
        return robots

    return {
        r["robot_id"]: r
        for r in robots
    }

async def get_robots(client):
    """
    Retrieves the available robots from the client.

    Params:
        - client [SwarmClient]: the swarm client instance that connects to the coordinator

    Returns a dictionary with the robot's hostname as its key and the robot data as the value.
    """
    robots_raw = await client.list_robots()
    return normalize_robots(robots_raw)

def print_robots(robots):
    """
    Prints a summary of all robots with its hostname as well as its IP and port.

    Params:
        - robots [dict[string, dict]]: A dictionary of the robots with their hostname as the keys.

    Returns nothing.
    """
    print(f"\nFound {len(robots)} robots\n")

    for robot_id, robot in robots.items():
        print(f"  {robot_id}: {robot['ip']}:{robot.get('port', 9000)}")