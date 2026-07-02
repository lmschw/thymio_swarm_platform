import asyncio
from swarm_platform.daemon.server import SwarmDaemon


def main():
    print("MAIN ENTRYPOINT REACHED")
    daemon = SwarmDaemon()
    asyncio.run(daemon.run())


print("SCRIPT LOADED")


if __name__ == "__main__":
    main()