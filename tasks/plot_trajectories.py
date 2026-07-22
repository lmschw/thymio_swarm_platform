import asyncio
import sys
from pathlib import Path

from swarm_platform.utils.reconstruct_trajectories import (
    load_trajectories,
    plot_trajectories,
)


async def main():

    if len(sys.argv) < 3:
        print("Usage:")
        print(
            "    uv run ./tasks/plot_trajectories.py "
            "./results/session/aggregated.csv "
            "./results/session/trajectories.png "
            "[hostname1 hostname2 ...]"
        )
        return

    csv_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    hostnames = None

    if len(sys.argv) > 3:
        hostnames = sys.argv[3:]
        
    trajectories = load_trajectories(
        csv_path,
        hostnames,
    )

    print(
        "Loaded trajectories:",
        list(trajectories.keys()),
    )

    if not trajectories:
        raise RuntimeError(
            "No trajectories found"
        )

    print(
        "Saving to:",
        output_path.resolve(),
    )

    plot_trajectories(
        trajectories,
        output_file=output_path,
        title=csv_path.parent.name,
    )

    print(
        "Exists after save:",
        output_path.exists(),
    )

if __name__ == "__main__":
    asyncio.run(main())