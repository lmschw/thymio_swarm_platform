from itertools import cycle
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import matplotlib.pyplot as plt

# Cycled per robot so trajectories stay distinguishable in grayscale prints.
TRAJECTORY_COLORS = ["black", "dimgray", "lightgray"]


def load_trajectories(
    csv_file: str | Path,
    hostnames: Optional[List[str]] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Load trajectories from an aggregated OptiTrack CSV.

    Reads the CSV, optionally filters it down to the requested
    hostnames, and splits it into one dataframe per hostname containing
    the pose and motor columns.

    Parameters
    ----------
    csv_file:
        Aggregated CSV containing pose.x, pose.y and hostname.

    hostnames:
        Optional list of robot hostnames to include.

    Returns
    -------
    dict[str, pd.DataFrame]
        Dictionary mapping hostname -> trajectory dataframe.
    """

    df = pd.read_csv(csv_file)

    if hostnames is not None:
        df = df[
            df["hostname"].isin(hostnames)
        ]

    trajectories = {}

    for hostname, robot_df in df.groupby("hostname"):

        trajectories[hostname] = robot_df[
            [
                "pose.x",
                "pose.y",
                "pose.z",
                "pose.o0",
                "pose.o1",
                "pose.o2",
                "pose.o3",
                "left_motor",
                "right_motor",
            ]
        ].reset_index(drop=True)

    return trajectories


def plot_trajectories(
    trajectories: Dict[str, pd.DataFrame],
    output_file: Optional[str | Path] = None,
    title: str = "Robot trajectories",
    labels: Optional[List[str]] = None,
) -> None:
    """
    Plot reconstructed robot trajectories.

    For each robot, plots its x/z path with start (circle) and end
    (X) markers, periodic direction arrows, and an end-position label.
    Saves the figure to ``output_file`` if provided, otherwise shows it
    interactively.

    Parameters
    ----------
    trajectories:
        Dictionary returned by load_trajectories.

    output_file:
        If provided, save figure here.

    title:
        Plot title.

    labels:
        Optional display labels, matched positionally to
        ``trajectories``' iteration order. Falls back to the hostname
        for any trajectory beyond the end of this list.
    """

    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    colors = cycle(TRAJECTORY_COLORS)

    for index, (hostname, trajectory) in enumerate(trajectories.items()):

        color = next(colors)

        label = (
            labels[index]
            if labels is not None and index < len(labels)
            else hostname
        )

        x = trajectory["pose.x"]
        z = trajectory["pose.z"]

        ax.plot(
            x,
            z,
            linewidth=2,
            color=color,
            label=label,
        )

        # start marker
        ax.scatter(
            x.iloc[0],
            z.iloc[0],
            marker="o",
            s=80,
            color=color,
        )

        # end marker
        ax.scatter(
            x.iloc[-1],
            z.iloc[-1],
            marker="X",
            s=100,
            color=color,
        )

        # direction arrows
        step = max(
            len(x) // 10,
            1,
        )

        ax.quiver(
            x.iloc[::step],
            z.iloc[::step],
            x.diff().iloc[::step],
            z.diff().iloc[::step],
            angles="xy",
            scale_units="xy",
            scale=1,
            width=0.003,
            color=color,
        )

        # label end position
        ax.annotate(
            label,
            (
                x.iloc[-1],
                z.iloc[-1],
            ),
            xytext=(5, 5),
            textcoords="offset points",
            color=color,
        )

    ax.set_title(title)

    ax.set_xlabel(
        "x position (m)"
    )

    ax.set_ylabel(
        "y position (m)"
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    ax.grid(True)
    ax.legend()

    plt.tight_layout()

    if output_file:
        plt.savefig(
            output_file,
            dpi=300,
            bbox_inches="tight",
        )
        plt.close(fig)
    else:
        plt.show()