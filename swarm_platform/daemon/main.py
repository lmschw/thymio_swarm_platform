import asyncio
from swarm_platform.daemon.server import SwarmDaemon


def main():
    daemon = SwarmDaemon()
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()