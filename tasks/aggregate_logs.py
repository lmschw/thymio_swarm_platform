import asyncio
import sys

from swarm_platform.utils.utils import aggregate_csvs

async def main():

    if len(sys.argv) != 3:
        print("Usage:")
        print("    uv run ./tasks/aggregate_logs.py ./results/baseline-run ./results/baseline-run/aggregated_csvs.csv")
        return

    aggregate_csvs(root_dir=sys.argv[1], output_file=sys.argv[2])

asyncio.run(main())