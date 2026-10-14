# Census Education and Employment Dashboard

An interactive Tableau analysis of how education and employment changed across England and Wales between the 2011 and 2021 censuses, backed by a reproducible Python data-preparation pipeline.

**Question:** how closely is a region's level of qualification related to the kind of work its residents do, and how did that relationship shift over a decade?

## Highlights

- Five dashboards covering qualifications, economic activity and industry of employment at Local Authority level.
- A Python pipeline that harmonises two census years (changed area codes, renamed categories, missing values) into one analysis-ready workbook.
- Dimensionality reduction (PCA on industry employment, t-SNE on qualifications) to cluster regions with similar profiles.
- A written report covering task definition, design justification, a small user evaluation and limitations.

## Findings

- The share of residents with **Level 4 qualifications and above rose markedly**, while the share with no qualifications fell.
- **Full-time employment grew and unemployment fell** over the decade.
- Professional, education, technology and healthcare employment expanded, most visibly in regions with higher qualification levels. Manufacturing declined.
- A **north-south gap** is visible in qualification growth, and regions with slower educational progress stayed tied to lower-growth industries.

The full discussion is in [`report/report.pdf`](report/report.pdf).

## Dashboards

| Dashboard | Purpose | Key insight |
| --- | --- | --- |
| Qualifications Comparison and Trends | Compare education levels, 2011 vs 2021 | Level 4+ increased significantly |
| Qualification Rate by Region | Regional differences in education change | North-south gap in qualification growth |
| Economic Activity Change | Employment type trends over time | Unemployment fell; full-time work rose |
| Industry Employment Change and PCA | Industry shifts and regional clustering | Tech and healthcare expanded in high-education regions |
| Dominant Industry and Employment Trends | Regional economic specialisation | Professional sectors dominate where education is higher |

Chart choices (grouped and stacked bars, choropleth maps, trend lines, PCA and t-SNE scatter plots) are justified against Munzner's task taxonomy in the report.

## Repository layout

```
.
├── dashboard/
│   └── england-wales-census-dashboard.twbx   Tableau packaged workbook
├── data/
│   ├── raw/                                  ONS census extracts (2011, 2021) and area-code lookup
│   └── processed/combined_sheets.xlsx        Pipeline output used by Tableau
├── report/report.pdf                         Full written report
├── src/prepare_data.py                       Data preparation pipeline
├── requirements.txt
└── LICENSE
```

## Open the dashboard

Open `dashboard/england-wales-census-dashboard.twbx` in [Tableau Public](https://public.tableau.com/app/discover) or Tableau Desktop. The workbook is packaged with its data, so no extra setup is needed.

## Reproduce the data

Requires Python 3.10 or newer.

```bash
git clone https://github.com/Mounish16/census-education-employment-dashboard.git
cd census-education-employment-dashboard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/prepare_data.py
```

This writes `data/processed/combined_sheets.xlsx` with five sheets:

| Sheet | Contents |
| --- | --- |
| Economic Activity | Long format: region, area code, year, activity, count |
| Highest Qualification | Long format: region, area code, year, qualification, count |
| industry_employment | Long format: region, area code, year, industry, count |
| industry employment pca | Wide industry counts plus `PCA1`, `PCA2` |
| Highest qualification tsne | Wide qualification counts plus `TSNE1`, `TSNE2` |

On Windows, activate the environment with `.venv\Scripts\activate`.

## Method

1. **Read** each Nomis export, skipping the seven metadata rows and the trailing footnotes.
2. **Harmonise area codes** from 2011 to 2021 Local Authority codes using the ONS lookup table.
3. **Align categories**: rename 2021 columns to the 2011 naming, drop unmatched columns, add a `Year` column and concatenate the two years.
4. **Impute missing values.** The 2011 qualification data has gaps in `Apprenticeship` and `Other qualifications`. A Bayesian Ridge regression, trained on rows with complete data and using the other numeric columns as features, predicts them. Predictions are clipped at zero because the values are counts.
5. **Reshape** to long format for Tableau.
6. **Embed**: standardise, then PCA (2 components) on industry employment and t-SNE (perplexity 30, `random_state=42`) on qualifications.

## Data

Population counts by Local Authority from the Office for National Statistics, Census 2011 and Census 2021 (England and Wales), contains public sector information licensed under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Source: [ONS Census 2021](https://www.ons.gov.uk/census/2021census).

## Limitations

- Built in Tableau Public, which has limited in-tool data preparation, so cleaning happens in Python beforehand.
- Mapping boundaries use 2011 definitions. Some 2021 area codes no longer match and appear as "unknown" on the 2021 maps.
- The 2011 imputation is a statistical estimate, not observed data.
- The evaluation was small (five participants) and informal.
- The t-SNE layout depends on the library version, so regenerated coordinates can differ slightly from those packaged in the workbook.

## Tools

Python (pandas, scikit-learn, openpyxl), Tableau Public.

## License

Code is released under the [MIT License](LICENSE). Census data is subject to the Open Government Licence noted above.
