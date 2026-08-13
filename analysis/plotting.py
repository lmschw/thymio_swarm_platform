import pandas as pd
import matplotlib.pyplot as plt


def plot_opinion_distribution(
    csv_path,
    reference_hostname="thymio-03",
    switch_at=None,
    plot_unselected=False,
):
    df = pd.read_csv(csv_path)

    # Use one robot as the reference for tick -> elapsed time.
    reference = (
        df[df["hostname"] == reference_hostname]
        .sort_values("tick")
        [["tick", "timestamp"]]
        .drop_duplicates("tick")
        .copy()
    )

    # Elapsed time relative to the first timestamp.
    reference["elapsed_time"] = (
        reference["timestamp"] - reference["timestamp"].iloc[0]
    )

    # Create tick -> elapsed time mapping.
    tick_to_time = reference.set_index("tick")["elapsed_time"]

    # ---------------------------------------------------------
    # Calculate percentage of robots with no opinion (-1).
    # ---------------------------------------------------------
    if plot_unselected:
        total_counts = df.groupby("tick").size()

        unselected_counts = (
            df[df["opinion"] == -1]
            .groupby("tick")
            .size()
        )

        unselected_percentage = (
            unselected_counts
            .reindex(total_counts.index, fill_value=0)
            .div(total_counts)
            * 100
        )

        unselected_percentage = unselected_percentage.rename("white?")

    # ---------------------------------------------------------
    # Calculate distribution of selected opinions.
    # ---------------------------------------------------------

    # Ignore robots that haven't selected an opinion yet.
    opinion_df = df[df["opinion"] >= 0].copy()

    # Number of robots with each opinion at each tick.
    counts = (
        opinion_df
        .groupby(["tick", "opinion"])
        .size()
        .unstack(fill_value=0)
    )

    # Convert counts to percentages of robots that have an opinion.
    percentages = counts.div(counts.sum(axis=1), axis=0) * 100

    # Make sure all possible opinion options appear.
    num_options = int(opinion_df["opinion"].max()) + 1

    percentages = percentages.reindex(
        columns=range(num_options),
        fill_value=0
    )

    # Give the opinion columns meaningful names.
    opinion_labels = {
        0: "black",
        1: "grey",
        2: "white",
    }

    percentages = percentages.rename(columns=opinion_labels)

    # Match each tick to elapsed time.
    percentages["elapsed_time"] = percentages.index.map(tick_to_time)

    # Remove ticks that weren't present for the reference robot.
    percentages = percentages.dropna(subset=["elapsed_time"])

    # Use elapsed time as x-axis.
    percentages = percentages.set_index("elapsed_time")

    # ---------------------------------------------------------
    # Plot.
    # ---------------------------------------------------------
    ax = percentages.plot(
        figsize=(10, 6),
        linewidth=2,
        color=["black", "darkgrey", "lightgray"]
    )

    # Add the optional -1 line.
    if plot_unselected:
        unselected_percentage.index = (
            unselected_percentage.index.map(tick_to_time)
        )

        unselected_percentage = unselected_percentage.dropna()

        ax.plot(
            unselected_percentage.index,
            unselected_percentage.values,
            color="blue",
            linewidth=2,
            label="No opinion"
        )

    # Add optional switch line.
    if switch_at is not None:
        ax.axvline(
            x=switch_at,
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Switch at {switch_at} s",
        )

    ax.set_xlabel("Elapsed time (s)")
    ax.set_ylabel("Thymios choosing option (%)")
    ax.set_title("Opinion Distribution Over Time")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    ax.legend(title="Opinion")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_opinion_distribution(
        "results/majority_voting_quality_switch-run/processed/aggregated.csv",
        reference_hostname="thymio-03",
        switch_at=120,
        plot_unselected=True,
    )