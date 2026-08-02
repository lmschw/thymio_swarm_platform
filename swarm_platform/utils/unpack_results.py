from pathlib import Path
import zipfile

from typing import Optional, Union

import pandas as pd


def extract_robot_logs(zip_dir: Union[str, Path], output_dir: Union[str, Path]) -> None:
    """
    Extract all robot zip files into output_dir.

    Expected:
        zip_dir/
            thymio-18.zip
            thymio-19.zip
            ...

    Produces:
        output_dir/
            thymio-18/
                thymio-18.csv
            thymio-19/
                thymio-19.csv

    Args:
        zip_dir: Directory containing per-robot ``.zip`` log archives.
        output_dir: Directory to extract each robot's archive into
            (created if it does not already exist).
    """

    zip_dir = Path(zip_dir)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for robot_zip in zip_dir.glob("*.zip"):

        robot_name = robot_zip.stem

        robot_dir = output_dir / robot_name

        robot_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        with zipfile.ZipFile(robot_zip, "r") as z:
            z.extractall(robot_dir)


def aggregate_csvs(
    root_dir: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Aggregate CSV files from robot directories.

    Hostname is inferred from the CSV filename.
    Empty CSV files are skipped.

    Args:
        root_dir: Directory to search recursively for ``.csv`` files.
        output_file: If given, the combined DataFrame is written to this
            path as CSV, and this path is excluded from the search (so
            re-running aggregation does not re-ingest its own output).

    Returns:
        The concatenation of all non-empty CSV files found under
        ``root_dir``, each tagged with a ``hostname`` column derived from
        its filename.

    Raises:
        ValueError: If no valid (non-empty) CSV files are found under
            ``root_dir``.
    """

    root_dir = Path(root_dir)

    dfs = []
    skipped = []

    for csv_file in root_dir.rglob("*.csv"):

        if (
            output_file is not None
            and csv_file.resolve() == Path(output_file).resolve()
        ):
            continue

        try:
            df = pd.read_csv(csv_file)

        except pd.errors.EmptyDataError:
            skipped.append(csv_file)
            continue

        if df.empty:
            skipped.append(csv_file)
            continue

        df["hostname"] = csv_file.stem

        dfs.append(df)

    if skipped:
        print("Skipped empty CSV files:")
        for f in skipped:
            print(f"  {f}")

    if not dfs:
        raise ValueError(
            f"No valid CSV files found under {root_dir}"
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


def unpack_and_aggregate(
    zip_dir: Union[str, Path],
    output_dir: Union[str, Path],
) -> pd.DataFrame:
    """
    Extract robot logs and create aggregated CSV.

    Args:
        zip_dir: Directory containing per-robot ``.zip`` log archives.
        output_dir: Directory in which to place the extracted logs (under
            an ``extracted`` subdirectory) and the aggregated CSV
            (``aggregated.csv``).

    Returns:
        The aggregated DataFrame produced by :func:`aggregate_csvs`.
    """

    zip_dir = Path(zip_dir)
    output_dir = Path(output_dir)

    extract_dir = output_dir / "extracted"

    extract_robot_logs(
        zip_dir,
        extract_dir,
    )

    return aggregate_csvs(
        extract_dir,
        output_dir / "aggregated.csv",
    )