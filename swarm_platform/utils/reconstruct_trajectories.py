from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def load_trajectories(
    csv_file: str | Path,
    hostnames: list[str] | None = None,
):
    """
    Load trajectories from an aggregated OptiTrack CSV.

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
    trajectories,
    output_file: str | Path | None = None,
    title="Robot trajectories",
):
    """
    Plot reconstructed robot trajectories.

    Parameters
    ----------
    trajectories:
        Dictionary returned by load_trajectories.

    output_file:
        If provided, save figure here.

    title:
        Plot title.
    """

    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    for hostname, trajectory in trajectories.items():

        x = trajectory["pose.x"]
        z = trajectory["pose.z"]

        ax.plot(
            x,
            z,
            linewidth=2,
            label=hostname,
        )

        # start marker
        ax.scatter(
            x.iloc[0],
            z.iloc[0],
            marker="o",
            s=80,
        )

        # end marker
        ax.scatter(
            x.iloc[-1],
            z.iloc[-1],
            marker="X",
            s=100,
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
        )

        # label end position
        ax.annotate(
            hostname,
            (
                x.iloc[-1],
                z.iloc[-1],
            ),
            xytext=(5, 5),
            textcoords="offset points",
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