from pathlib import Path
import zipfile

import pandas as pd


def unpack_results(results_dir):
    """
    Extract every .zip file in a results directory.

    Parameters
    ----------
    results_dir : str | Path
        Session results directory.

    Returns
    -------
    Path
        Directory containing the extracted robot folders.
    """
    results_dir = Path(results_dir)

    for zip_path in results_dir.glob("*.zip"):
        extract_dir = results_dir / zip_path.stem
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

    return results_dir


def aggregate_csvs(root_dir, output_file=None):
    root = Path(root_dir)

    dfs = []

    for csv_file in root.rglob("*.csv"):
        if output_file is not None and csv_file == Path(output_file):
            continue
        df = pd.read_csv(csv_file)
        df["hostname"] = csv_file.stem
        dfs.append(df)

    if not dfs:
        raise ValueError(
            f"No CSV files found under {root}"
        )

    combined = pd.concat(
        dfs,
        ignore_index=True,
    )

    if output_file:
        combined.to_csv(
            output_file,
            index=False,
        )

    return combined


def unpack_and_aggregate(zip_path, output_dir):
    zip_path = Path(zip_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(output_dir)

    return aggregate_csvs(
        output_dir,
        output_dir / "aggregated.csv",
    )