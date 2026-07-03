
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