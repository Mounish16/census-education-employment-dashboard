"""Draw static preview charts from the processed workbook.

These mirror the main views of the Tableau dashboards (the interactive
versions live in the .twbx) so the analysis can be seen without Tableau.

Usage
    python src/make_previews.py
"""

from __future__ import annotations

import argparse
import textwrap
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

C11, C21 = "#9AA5B1", "#1F6FEB"
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "figure.dpi": 110,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    }
)


ACTIVITY_LABELS = {
    "Economically active: In employment": "In employment",
    "Economically active: Employee: Full-time": "Employee,\nfull-time",
    "Economically active: Employee: Part-time": "Employee,\npart-time",
    "Economically active: Unemployed": "Unemployed",
    "Economically inactive: Retired": "Retired",
    "Economically inactive: Student (including full-time students)": "Student\n(inactive)",
    "Economically inactive: Other": "Other\n(inactive)",
}


def wrap(label: str, width: int = 16) -> str:
    return "\n".join(textwrap.wrap(label.replace(" qualifications", " quals."), width))


def shorten(label: str, width: int = 38) -> str:
    return label if len(label) <= width else label[: width - 1] + "…"


def grouped_bars(ax, table: pd.DataFrame, ylabel: str, fmt: str, labels: dict | None = None) -> None:
    labels = labels or {}
    x = range(len(table))
    w = 0.38
    b11 = ax.bar([i - w / 2 for i in x], table[2011], w, label="2011", color=C11)
    b21 = ax.bar([i + w / 2 for i in x], table[2021], w, label="2021", color=C21)
    for bars in (b11, b21):
        ax.bar_label(bars, fmt=fmt, fontsize=8, padding=2)
    ax.set_xticks(list(x), [labels.get(i, wrap(i)) for i in table.index])
    ax.set_ylabel(ylabel)
    ax.legend(frameon=False)


def qualifications(sheets, out: Path) -> None:
    df = sheets["Highest Qualification"]
    t = df.groupby(["Qualifications", "Year"]).Counts.sum().unstack()
    t = (t / t.sum() * 100).loc[
        [
            "No qualifications",
            "Level 1 qualifications",
            "Level 2 qualifications",
            "Apprenticeship",
            "Level 3 qualifications",
            "Level 4 qualifications and above",
            "Other qualifications",
        ]
    ]
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    grouped_bars(ax, t, "Share of residents aged 16+ (%)", "%.1f")
    ax.set_title("Highest level of qualification, England and Wales")
    fig.savefig(out / "01-qualifications.png")


def economic_activity(sheets, out: Path) -> None:
    df = sheets["Economic Activity"]
    t = df.groupby(["Economic Activity", "Year"]).Counts.sum().unstack() / 1e6
    keep = [
        "Economically active: In employment",
        "Economically active: Employee: Full-time",
        "Economically active: Employee: Part-time",
        "Economically active: Unemployed",
        "Economically inactive: Retired",
        "Economically inactive: Student (including full-time students)",
        "Economically inactive: Other",
    ]
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    grouped_bars(ax, t.loc[keep], "Residents aged 16 to 74 (millions)", "%.1f", ACTIVITY_LABELS)
    ax.set_title("Economic activity, England and Wales")
    fig.savefig(out / "02-economic-activity.png")


def industry(sheets, out: Path) -> None:
    df = sheets["industry_employment"]
    t = df.groupby(["Industry", "Year"]).Counts.sum().unstack()
    change = ((t / t.sum() * 100)[2021] - (t / t.sum() * 100)[2011]).sort_values()
    colors = [C21 if v >= 0 else "#D1495B" for v in change]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    bars = ax.barh([shorten(i, 60) for i in change.index], change, color=colors)
    ax.bar_label(bars, fmt="%+.2f", fontsize=8, padding=3)
    ax.axvline(0, color="#444", lw=0.8)
    ax.set_xlabel("Change in share of employment, 2011 to 2021 (percentage points)")
    ax.set_title("Industry employment: shifts in share")
    fig.savefig(out / "03-industry-change.png")


def scatter(sheet: pd.DataFrame, x: str, y: str, title: str, name: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5))
    for year, color in ((2011, C11), (2021, C21)):
        d = sheet[sheet.Year == year]
        ax.scatter(d[x], d[y], s=16, alpha=0.75, color=color, label=str(year), edgecolor="none")
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(title)
    ax.legend(frameon=False, title="Census year")
    fig.savefig(out / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("data/processed/combined_sheets.xlsx"))
    parser.add_argument("--out", type=Path, default=Path("docs/images"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    sheets = pd.read_excel(args.data, sheet_name=None)
    qualifications(sheets, args.out)
    economic_activity(sheets, args.out)
    industry(sheets, args.out)
    scatter(sheets["industry employment pca"], "PCA1", "PCA2",
            "Local authorities by industry mix (PCA)", "04-pca-industry.png", args.out)
    scatter(sheets["Highest qualification tsne"], "TSNE1", "TSNE2",
            "Local authorities by qualification mix (t-SNE)", "05-tsne-qualification.png", args.out)
    print(f"Saved previews to {args.out}")


if __name__ == "__main__":
    main()
