import pandas as pd
import matplotlib.pyplot as plt


def plot_opinion_distribution_ticks(
    csv_path,
    switch_at=None,
    plot_unselected=False,
):
    df = pd.read_csv(csv_path)

    # Check whether any robot returns to -1 after having an opinion.
    for hostname, robot_df in df.groupby("hostname"):
        robot_df = robot_df.sort_values("tick")

        had_opinion = False

        for _, row in robot_df.iterrows():
            if row["opinion"] >= 0:
                had_opinion = True
            elif row["opinion"] == -1 and had_opinion:
                print(
                    f"WARNING: {hostname} went back to -1 "
                    f"at tick {row['tick']}"
                )
                break

    # ---------------------------------------------------------
    # One state per robot per tick.
    # ---------------------------------------------------------
    robot_states = (
        df.sort_values("timestamp")
        .drop_duplicates(
            subset=["tick", "hostname"],
            keep="last",
        )
    )

    # ---------------------------------------------------------
    # Total number of robots at each tick.
    # ---------------------------------------------------------
    total_robots = (
        robot_states
        .groupby("tick")["hostname"]
        .nunique()
    )

    # ---------------------------------------------------------
    # Calculate percentage for each opinion.
    # All percentages use ALL robots as the denominator.
    # ---------------------------------------------------------
    percentages = pd.DataFrame(index=total_robots.index)

    for opinion, label in [
        (0, "black"),
        (1, "grey"),
        (2, "white"),
        (-1, "No opinion"),
    ]:
        counts = (
            robot_states[robot_states["opinion"] == opinion]
            .groupby("tick")["hostname"]
            .nunique()
        )

        percentages[label] = (
            counts
            .reindex(total_robots.index, fill_value=0)
            .div(total_robots)
            * 100
        )

    # ---------------------------------------------------------
    # Only plot -1 when requested.
    # ---------------------------------------------------------
    plot_percentages = percentages.copy()

    if not plot_unselected:
        plot_percentages = plot_percentages.drop(
            columns=["No opinion"]
        )

    # ---------------------------------------------------------
    # Plot against TICK directly.
    # ---------------------------------------------------------
    ax = plot_percentages.plot(
        figsize=(10, 6),
        linewidth=2,
        color={
            "black": "black",
            "grey": "darkgrey",
            "white": "lightgray",
            "No opinion": "blue",
        },
    )

    if switch_at is not None:
        ax.axvline(
            x=switch_at,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Switch at {switch_at}",
        )

    ax.set_xlabel("Tick")
    ax.set_ylabel("Thymios choosing option (%)")
    ax.set_title("Opinion Distribution Over Time")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    ax.legend(title="Opinion")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_opinion_distribution_ticks(
        "results/active_inference_quality_switch-run/processed/aggregated.csv",
        switch_at=400,
        plot_unselected=True,
    )