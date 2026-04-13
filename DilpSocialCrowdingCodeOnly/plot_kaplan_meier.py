"""
Plot Kaplan–Meier survival curves by treatment on one figure.

Treatments with fewer than 5 observed deaths (event_type == 1) are omitted.
Reads survival_data.csv (run prepare_survival_data.py first).
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from lifelines import KaplanMeierFitter

MIN_DEATHS = 5
DATA_FILE = Path(__file__).resolve().parent / "survival_data.csv"
OUTPUT_FILE = Path(__file__).resolve().parent / "kaplan_meier.png"


def main() -> None:
    df = pd.read_csv(DATA_FILE)
    death_counts = df.groupby("treatment", sort=False)["event_type"].sum()
    eligible = death_counts[death_counts >= MIN_DEATHS].index.tolist()
    skipped = death_counts[death_counts < MIN_DEATHS]

    if skipped.size:
        print(
            "Skipping treatments with fewer than "
            f"{MIN_DEATHS} observed deaths:\n{skipped.to_string()}\n"
        )

    if not eligible:
        print("No treatments meet the minimum death count; nothing to plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    for treatment in sorted(eligible):
        sub = df[df["treatment"] == treatment]
        kmf = KaplanMeierFitter()
        kmf.fit(sub["age"], sub["event_type"], label=treatment)
        kmf.plot_survival_function(ax=ax)

    ax.set_xlabel("Age (hours)")
    ax.set_ylabel("Survival probability")
    ax.set_ylim(0, 1.0)
    ax.set_title("Kaplan–Meier survival by treatment")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUTPUT_FILE, dpi=150)
    print(f"Saved {OUTPUT_FILE}")
    if matplotlib.get_backend().lower() != "agg":
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
