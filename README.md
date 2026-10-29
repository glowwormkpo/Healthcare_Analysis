# Hospital Patient Experience BI (CMS HCAHPS)

A star-schema data model and BI reporting layer built on CMS HCAHPS patient survey data:
34,999 survey records across 700 hospitals, modeled into four dimensions and one fact table,
with a Jupyter report notebook and an interactive HTML dashboard (State → County → Hospital drill-down).

## Key findings

- **Medication communication was the weakest care category**, scoring 78.6 versus 90+ for most other categories.
- **Survey response rate correlated with star rating** (r = 0.56). This is a correlation, not evidence of causation.

## Data model

| Table | Grain | Rows |
| --- | --- | --- |
| `Fact_Patient_Survey` | hospital × survey measure × answer | 34,999 |
| `Dim_Hospital_Details` | hospital (CMS Provider ID) | 700 |
| `Dim_Country_Details` | county / city / ZIP | 629 |
| `Dim_Measure_Details` | survey measure | 50 |
| `Dim_Survey_Details` | survey question and answer | 50 |

`Dim_Country_Details` keeps the name from the original project spec, but it is populated at
**county** grain, because the source data is US county-level and the reports ask about counties.
See the note at the top of `sql/schema.sql`.

## Repository layout

```
sql/schema.sql                     star-schema DDL (SQLite)
scripts/build_schema.py            reads the source CSV and builds healthcare_bi.db
scripts/cells.py                   report notebook cells (source)
scripts/run_notebook.py            executes cells.py and writes the .ipynb with outputs
notebooks/healthcare_bi_reports.ipynb
dashboard/healthcare_dashboard.html
healthcare_bi.db                   built SQLite database
```

## Snowflake version

`sql/snowflake_schema.sql` contains the equivalent Snowflake DDL, file format, stage and `COPY INTO`
statements, plus a row-count sanity check. It has not yet been run against a Snowflake account,
and the CSV exports it loads are not included in this repository.
