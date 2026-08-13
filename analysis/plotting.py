import pandas as pd
import matplotlib.pyplot as plt


def plot_opinion_distribution(csv_path):
    df = pd.read_csv(csv_path)

    # Ignore robots that haven't selected an opinion yet.
    df = df[df["opinion"] >= 0].copy()

    # Number of robots with each opinion at each tick.
    counts = (
        df.groupby(["tick", "opinion"])
        .size()
        .unstack(fill_value=0)
    )

    # Convert counts to percentages of robots that have an opinion.
    percentages = counts.div(counts.sum(axis=1), axis=0) * 100

    # Make sure all possible opinion options appear.
    num_options = int(df["opinion"].max()) + 1
    percentages = percentages.reindex(
        columns=range(num_options),
        fill_value=0
    )

    # Plot.
    ax = percentages.plot(
        figsize=(10, 6),
        linewidth=2,
        color=["black", "dimgray", "lightgray"]
    )

    ax.set_xlabel("Tick")
    ax.set_ylabel("Thymios choosing option (%)")
    ax.set_title("Opinion Distribution Over Time")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    ax.legend(
        title="Opinion",
        labels=["black", "grey", "white"]
    )

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    plot_opinion_distribution(
        "results/weighted_voter_quality_switch-run/processed/aggregated.csv"
    )