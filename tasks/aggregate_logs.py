import asyncio
import sys
from pathlib import Path

from swarm_platform.utils.unpack_results import (
    unpack_and_aggregate,
)


async def main():

    if len(sys.argv) != 3:
        print("Usage:")
        print(
            "    uv run ./tasks/aggregate_logs.py "
            "./results/session.zip "
            "./results/session"
        )
        return

    zip_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    df = unpack_and_aggregate(
        zip_path,
        output_dir,
    )

    print(
        f"Finished. Aggregated {len(df)} rows "
        f"into {output_dir / 'aggregated.csv'}"
    )


if __name__ == "__main__":
    asyncio.run(main())