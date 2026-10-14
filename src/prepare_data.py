"""Prepare the 2011 and 2021 England & Wales census extracts for Tableau.

Pipeline
    1. Harmonise Local Authority codes (2011 -> 2021) with the ONS lookup table.
    2. Clean and align the three datasets (economic activity, highest
       qualification, industry of employment) across the two census years.
    3. Impute missing 2011 'Apprenticeship' / 'Other qualifications' counts
       with Bayesian Ridge regression.
    4. Reshape to long format, add PCA (industry) and t-SNE (qualification)
       coordinates, and write one workbook for Tableau.

Usage
    python src/prepare_data.py
    python src/prepare_data.py --raw data/raw --out data/processed
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import BayesianRidge
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

ID_COLS = ["Region", "Area Code", "Year"]
RANDOM_STATE = 42

ECONOMIC_ACTIVITY_MAP = {
    "Economically active (excluding full-time students):In employment": "Economically active: In employment",
    "Economically active (excluding full-time students): In employment: Employee: Part-time": "Economically active: Employee: Part-time",
    "Economically active (excluding full-time students): In employment: Employee: Full-time": "Economically active: Employee: Full-time",
    "Economically active (excluding full-time students): Unemployed": "Economically active: Unemployed",
    "Economically inactive: Retired": "Economically inactive: Retired",
    "Economically inactive: Other": "Economically inactive: Other",
    "Economically active and a full-time student:In employment": "Economically active: Full-time student",
    "Economically inactive: Student": "Economically inactive: Student (including full-time students)",
}

QUALIFICATION_MAP = {
    "Level 1 and entry level qualifications": "Level 1 qualifications",
    "Level 4 qualifications or above": "Level 4 qualifications and above",
}

INDUSTRY_MAP = {
    "A: Agriculture, Forestry and fishing": "A Agriculture, forestry and fishing",
    "B: Mining and quarrying": "B Mining and quarrying",
    "C: Manufacturing": "C Manufacturing",
    "D: Electricity, gas, steam and air conditioning supply": "D Electricity, gas, steam and air conditioning supply",
    "E:  Water supply; Sewerage, Waste management and Remediation activities": "E Water supply; sewerage, waste management and remediation activities",
    "F: Construction": "F Construction",
    "G: Wholesale and retail trade; repair of motor vehicles and motorcycles": "G Wholesale and retail trade; repair of motor vehicles and motor cycles",
    "H: Transport and storage": "H Transport and storage",
    "I: Accommodation and food service activities": "I Accommodation and food service activities",
    "J: Information and communication": "J Information and communication",
    "K: Financial and insurance activities": "K Financial and insurance activities",
    "L: Real estate activities": "L Real estate activities",
    "M: Professional, scientific and technical activities": "M Professional, scientific and technical activities",
    "N: Administrative and support service activities": "N Administrative and support service activities",
    "O: Public administration and defence; compulsory social security": "O Public administration and defence; compulsory social security",
    "P: Education": "P Education",
    "Q: Human health and social work activities": "Q Human health and social work activities",
}


def read_ons(path: Path, trailing_rows: int, sheet: str = "Data") -> pd.DataFrame:
    """Read an ONS Nomis export: skip 7 metadata rows, drop footnotes."""
    df = pd.read_excel(path, sheet_name=sheet, skiprows=7)
    if trailing_rows:
        df = df.iloc[:-trailing_rows]
    df = df.rename(columns={df.columns[0]: "Region", df.columns[1]: "Area Code"})
    # Keep England and Wales only (codes starting E or W); drops stray rows.
    return df[df["Area Code"].astype(str).str.match(r"^[EW]\d")]


def load_lookup(path: Path) -> pd.DataFrame:
    lookup = pd.read_csv(path).rename(columns={"LAD11CD": "Old_Code", "LAD21CD": "New_Code"})
    return lookup[["Old_Code", "New_Code"]]


def map_area_codes(df: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    """Replace 2011 Local Authority codes with their 2021 equivalent."""
    df = df.merge(lookup, how="left", left_on="Area Code", right_on="Old_Code")
    df["Area Code"] = df["New_Code"].combine_first(df["Area Code"])
    return df.drop(columns=["Old_Code", "New_Code"])


def prepare_economic_activity(raw: Path, lookup: pd.DataFrame) -> pd.DataFrame:
    d11 = read_ons(raw / "2011" / "economic_activity.xlsx", trailing_rows=59)
    d21 = read_ons(raw / "2021" / "economic_activity.xlsx", trailing_rows=2)
    d11 = map_area_codes(d11.drop(columns="All usual residents aged 16 to 74"), lookup)
    d21 = d21.rename(columns=ECONOMIC_ACTIVITY_MAP)[d11.columns].copy()
    d11["Year"], d21["Year"] = 2011, 2021
    return pd.concat([d11, d21], ignore_index=True)


def impute_qualifications_2011(raw: Path) -> pd.DataFrame:
    """Fill any missing 2011 'Apprenticeship' / 'Other qualifications' counts.

    In the supplied extract the only gaps belong to Aberdeen City, which is
    outside England and Wales and removed by `read_ons`. The imputation is kept
    as a safeguard so the pipeline also handles extracts that do have gaps.
    """
    df = read_ons(raw / "2011" / "highest_qualification.xlsx", trailing_rows=60)
    df = df.replace("-", pd.NA)
    targets = ["Apprenticeship", "Other qualifications"]
    features = df.drop(columns=targets + ["Region"], errors="ignore")
    features = features.drop(columns="Area Code").apply(pd.to_numeric, errors="coerce")
    scaled = StandardScaler().fit_transform(
        SimpleImputer(strategy="mean").fit_transform(features)
    )
    for col in targets:
        y = pd.to_numeric(df[col], errors="coerce")
        known = y.notna()
        if known.all():
            continue
        model = BayesianRidge().fit(scaled[known], y[known])
        df.loc[~known, col] = model.predict(scaled[~known]).clip(min=0)
    return df


def prepare_qualifications(raw: Path, lookup: pd.DataFrame) -> pd.DataFrame:
    d11 = map_area_codes(impute_qualifications_2011(raw), lookup)
    d21 = read_ons(raw / "2021" / "highest_qualification.xlsx", trailing_rows=2)
    d21 = d21.rename(columns=QUALIFICATION_MAP)[d11.columns].copy()
    d11["Year"], d21["Year"] = 2011, 2021
    return pd.concat([d11, d21], ignore_index=True)


def prepare_industry(raw: Path, lookup: pd.DataFrame) -> pd.DataFrame:
    d11 = map_area_codes(read_ons(raw / "2011" / "industry_of_employment.xlsx", 59), lookup)
    d21 = read_ons(raw / "2021" / "industry_of_employment.xlsx", 2)
    d21 = d21.rename(columns=INDUSTRY_MAP)
    d11 = d11[d21.columns]
    d11["Year"], d21["Year"] = 2011, 2021
    return pd.concat([d11, d21], ignore_index=True)


def to_long(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    value_cols = [c for c in df.columns if c not in ID_COLS]
    return df.melt(id_vars=ID_COLS, value_vars=value_cols, var_name=dimension, value_name="Counts")


def embed(df: pd.DataFrame, reducer, names: tuple[str, str]) -> pd.DataFrame:
    """Append a 2-D embedding of the standardised numeric columns."""
    scaled = StandardScaler().fit_transform(df.select_dtypes(include="number"))
    coords = reducer.fit_transform(scaled)
    out = df.copy()
    out[names[0]], out[names[1]] = coords[:, 0], coords[:, 1]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/processed"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    lookup = load_lookup(args.raw / "lad_lookup_2011_to_2021.csv")

    economic = prepare_economic_activity(args.raw, lookup)
    qualifications = prepare_qualifications(args.raw, lookup)
    industry = prepare_industry(args.raw, lookup)

    pca = embed(industry, PCA(n_components=2), ("PCA1", "PCA2"))
    tsne = embed(
        qualifications,
        TSNE(n_components=2, perplexity=30, max_iter=1000, random_state=RANDOM_STATE),
        ("TSNE1", "TSNE2"),
    )

    sheets = {
        "Economic Activity": to_long(economic, "Economic Activity"),
        "Highest Qualification": to_long(qualifications, "Qualifications"),
        "industry_employment": to_long(industry, "Industry"),
        "industry employment pca": pca,
        "Highest qualification tsne": tsne,
    }
    target = args.out / "combined_sheets.xlsx"
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    for name, frame in sheets.items():
        print(f"{name:<28}{frame.shape[0]:>7} rows x {frame.shape[1]} cols")
    print(f"Saved {target}")


if __name__ == "__main__":
    main()
