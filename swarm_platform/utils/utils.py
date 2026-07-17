import csv
import datetime
from pathlib import Path
import pandas as pd

async def save_robot_info_to_csv(client):
    robots = await client.list_robots()
    data = [{"hostname": hostname, "ip": robots[hostname]["ip"]} for hostname in robots.keys()]

    now = datetime.datetime.now()
    time = str(now.time()).replace(":", "")

    with open(f"thymio_ips_{now.date()}_{time}.csv", "w", newline="") as csv_file:
        fieldnames = ["hostname", "ip"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def aggregate_csvs(root_dir, output_file=None):
    """
    Aggregate all CSV files found in hostname subdirectories.

    Parameters
    ----------
    root_dir : str or Path
        Root experiments directory.
    output_file : str or Path, optional
        If provided, write the aggregated CSV to this path.

    Returns
    -------
    pandas.DataFrame
        Aggregated dataframe with an added 'hostname' column.
    """
    root = Path(root_dir)
    dfs = []

    # Iterate over hostname directories
    for host_dir in root.iterdir():
        if not host_dir.is_dir():
            continue

        hostname = host_dir.name

        # Read every CSV in this hostname directory (recursively)
        for csv_file in host_dir.rglob("*.csv"):
            df = pd.read_csv(csv_file)
            df["hostname"] = hostname
            dfs.append(df)

    if not dfs:
        raise ValueError(f"No CSV files found under {root}")

    combined = pd.concat(dfs, ignore_index=True)

    if output_file is not None:
        combined.to_csv(output_file, index=False)

    return combined