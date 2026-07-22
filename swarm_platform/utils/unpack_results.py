from pathlib import Path
import zipfile

import pandas as pd


def extract_robot_logs(zip_dir, output_dir):
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


def aggregate_csvs(root_dir, output_file=None):
    """
    Aggregate CSV files from robot directories.

    Hostname is inferred from the CSV filename.
    Empty CSV files are skipped.
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


def unpack_and_aggregate(zip_dir, output_dir):
    """
    Extract robot logs and create aggregated CSV.
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