
def normalize_robots(robots):
    """
    Supports both:
    - dict: {id: robot}
    - list: [{robot_id, ip, port}]
    """
    if isinstance(robots, dict):
        return robots

    return {
        r["robot_id"]: r
        for r in robots
    }

async def get_robots(client):
    robots_raw = await client.list_robots()
    return normalize_robots(robots_raw)

def print_robots(robots):
    print(f"\nFound {len(robots)} robots\n")

    for robot_id, robot in robots.items():
        print(f"  {robot_id}: {robot['ip']}:{robot.get('port', 9000)}")