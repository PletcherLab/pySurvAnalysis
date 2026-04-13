"""Load and prepare individual-level survival data from experiment Excel files.

Input format
------------
The Excel workbook must contain:

* **RawData** sheet — one row per chamber per census time, with columns:
    AgeH, Chamber, IntDeaths, Censored  (at minimum)

* **Design** sheet — one row per chamber, with columns:
    Chamber, SampleSize, StartTime, <factor1>, <factor2>, ...
    All columns after *StartTime* are treatment factors.

Output
------
A pandas DataFrame with one row per *individual*, containing:

    time        — age at death or censoring (hours)
    event       — 1 = observed death, 0 = right-censored
    chamber     — source chamber id
    treatment   — combined treatment label (factor levels joined with "/")
    <factor1>, <factor2>, ...  — individual factor columns
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd


def read_assume_censored(path: Union[str, Path]) -> bool:
    """Read the AssumeCensored flag from the PrivateData sheet.

    Returns True if AssumeCensored == 1, False otherwise.
    Falls back to True if the sheet or column is missing.
    """
    try:
        priv = pd.read_excel(path, sheet_name="PrivateData")
        if "AssumeCensored" in priv.columns and len(priv) > 0:
            return int(priv["AssumeCensored"].iloc[0]) == 1
    except (ValueError, KeyError):
        pass
    return True


def load_design(path: Union[str, Path]) -> tuple[pd.DataFrame, list[str]]:
    """Read the Design sheet and return (design_df, factor_names).

    Factor columns are everything after the *StartTime* column.
    """
    design = pd.read_excel(path, sheet_name="Design")
    cols = list(design.columns)
    start_idx = cols.index("StartTime")
    factors = cols[start_idx + 1 :]
    if not factors:
        raise ValueError("No treatment factor columns found after StartTime in Design sheet")
    return design, factors


def load_raw_data(path: Union[str, Path]) -> pd.DataFrame:
    """Read the RawData sheet."""
    raw = pd.read_excel(path, sheet_name="RawData")
    required = {"AgeH", "Chamber", "IntDeaths", "Censored"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"RawData sheet missing columns: {missing}")
    return raw


def build_individual_data(
    raw: pd.DataFrame,
    design: pd.DataFrame,
    factors: list[str],
    assume_censored: bool = True,
) -> pd.DataFrame:
    """Expand census-level counts into one row per individual.

    For each chamber at each census time:
    * IntDeaths > 0 → that many death rows (event=1)
    * Censored > 0  → that many censored rows (event=0)

    Parameters
    ----------
    assume_censored : bool
        If True (default), the initial cohort size is taken from the Design
        sheet's SampleSize column.  Individuals not accounted for by observed
        deaths or explicit censoring are assumed right-censored at the last
        census time and added to the dataset.

        If False, the initial cohort size for each chamber is calculated as
        the sum of all IntDeaths and Censored observations for that chamber.
        No additional right-censored individuals are added.
    """
    rows: list[dict] = []

    # Pre-compute chamber → design info lookup
    design_lookup = design.set_index("Chamber")

    for chamber_id, grp in raw.groupby("Chamber"):
        grp = grp.sort_values("AgeH")

        if chamber_id not in design_lookup.index:
            continue

        chamber_design = design_lookup.loc[chamber_id]
        factor_vals = {f: chamber_design[f] for f in factors}

        accounted = 0  # total deaths + censored seen so far

        for _, row in grp.iterrows():
            age = row["AgeH"]
            n_deaths = int(row["IntDeaths"])
            n_censored = int(row["Censored"])

            for _ in range(n_deaths):
                rec = {"time": age, "event": 1, "chamber": chamber_id}
                rec.update(factor_vals)
                rows.append(rec)

            for _ in range(n_censored):
                rec = {"time": age, "event": 0, "chamber": chamber_id}
                rec.update(factor_vals)
                rows.append(rec)

            accounted += n_deaths + n_censored

        if assume_censored:
            # Remaining individuals are right-censored at the last census time
            n0 = int(chamber_design["SampleSize"])
            last_time = grp["AgeH"].max()
            remaining = n0 - accounted
            for _ in range(remaining):
                rec = {"time": last_time, "event": 0, "chamber": chamber_id}
                rec.update(factor_vals)
                rows.append(rec)

    df = pd.DataFrame(rows)

    # Build treatment label from factor columns
    df["treatment"] = df[factors].astype(str).agg("/".join, axis=1)

    # Order columns nicely
    col_order = ["time", "event", "chamber", "treatment"] + factors
    df = df[col_order].sort_values(["treatment", "time"]).reset_index(drop=True)

    return df


def load_experiment(
    path: Union[str, Path],
    assume_censored: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """High-level loader: returns (individual_data, factor_names).

    Parameters
    ----------
    assume_censored : bool
        If True, unaccounted individuals (SampleSize minus observed deaths
        and censored) are added as right-censored at the last census time.
        If False, cohort size is just the sum of deaths + censored.
    """
    path = Path(path)
    design, factors = load_design(path)
    raw = load_raw_data(path)
    individual = build_individual_data(raw, design, factors, assume_censored=assume_censored)
    return individual, factors
