import asyncio
from swarm_platform.daemon.server import SwarmDaemon


def main() -> None:
    """Create a SwarmDaemon and run it until completion.

    Entry point for running the swarm daemon process on a robot.
    """
    print("MAIN ENTRYPOINT REACHED")
    daemon = SwarmDaemon()
    asyncio.run(daemon.run())


print("SCRIPT LOADED")


if __name__ == "__main__":
    main()