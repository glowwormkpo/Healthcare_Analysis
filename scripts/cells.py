# Cell source strings for the Healthcare BI notebook.
# Each entry is (cell_type, source). Code cells are executed by the harness
# to produce real outputs before being written into the .ipynb file.

CELLS = [

("markdown", """\
# Healthcare Patient Survey BI Mini Project -- Reports

Runs the 8 sample reports from the BI Mini Project brief against the star schema in
`healthcare_bi.db` (`Dim_Country_Details`, `Dim_Hospital_Details`, `Dim_Measure_Details`,
`Dim_Survey_Details`, `Fact_Patient_Survey`), using only pandas + matplotlib.

> Note: `Dim_Country_Details` is populated at **county** grain (`Country_Name` holds the
> county name) rather than literal country, since the source data
> (`Health Care_Patient_survey_source.csv`) is US county-level and report requirements
> #3 and #5 explicitly ask about counties.
"""),

("code", """\
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 140)

conn = sqlite3.connect('healthcare_bi.db')

county   = pd.read_sql('select * from Dim_Country_Details', conn)
hospital = pd.read_sql('select * from Dim_Hospital_Details', conn)
measure  = pd.read_sql('select * from Dim_Measure_Details', conn)
survey   = pd.read_sql('select * from Dim_Survey_Details', conn)
fact     = pd.read_sql('select * from Fact_Patient_Survey', conn)

print(f"Dim_Country_Details:  {county.shape}")
print(f"Dim_Hospital_Details: {hospital.shape}")
print(f"Dim_Measure_Details:  {measure.shape}")
print(f"Dim_Survey_Details:   {survey.shape}")
print(f"Fact_Patient_Survey:  {fact.shape}")
"""),

("markdown", "## Build a hospital-level base table\n\nJoins hospital + county, and pulls out the two metrics (completed surveys, response rate) that are constant per hospital for the survey period, plus the hospital's overall star rating."),

("code", """\
h = hospital.drop(columns=['City']).merge(county, on='Country_Id').rename(columns={'Country_Name': 'County_Name'})

# Number of Completed Surveys & Survey Response Rate Percent are repeated identically
# across all 50 measure rows for a given hospital (they describe the survey period as
# a whole, not an individual question) -- so we take one value per hospital.
base = (
    fact.groupby('Hospital_Id')
        .agg(No_Completed_Surveys=('No_Completed_Surveys', 'max'),
             Survey_Response_Rate_Percent=('Survey_Response_Rate_Percent', 'max'))
        .reset_index()
        .merge(h, on='Hospital_Id')
)

overall_survey_id = survey.loc[survey.Survey_Question == 'Summary star rating', 'Survey_Id'].iloc[0]
overall_star = fact.loc[fact.Survey_Id == overall_survey_id, ['Hospital_Id', 'Patient_Survey_Star_Rating']]
base = base.merge(overall_star, on='Hospital_Id', how='left')

base.head()
"""),

("markdown", "## Report 1: Number of Surveys Completed by Different Hospitals"),

("code", """\
report1 = (
    base[['Hospital_Name', 'City', 'State', 'No_Completed_Surveys']]
    .sort_values('No_Completed_Surveys', ascending=False)
    .head(15)
)

fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(report1['Hospital_Name'][::-1], report1['No_Completed_Surveys'][::-1], color='#2563eb')
ax.set_xlabel('Completed Surveys')
ax.set_title('Report 1: Surveys Completed by Hospital (Top 15)')
plt.tight_layout()
plt.show()

report1
"""),

("markdown", "## Report 2: Survey Response Rate by Measure ID, per Hospital\n\nUsing the 10 `*_LINEAR_SCORE` measures as the measure-category axis. Response rate is one number per hospital for the whole survey, so each hospital's line is flat across categories -- the chart compares hospitals' overall engagement levels rather than per-question variation."),

("code", """\
lin = survey[survey.Survey_Question.str.contains('linear mean score')][['Survey_Id', 'Survey_Question']].copy()
lin['Category'] = lin['Survey_Question'].str.replace(' - linear mean score', '', regex=False)

r2 = (
    fact[fact.Survey_Id.isin(lin.Survey_Id)][['Hospital_Id', 'Survey_Id', 'Answer_Percent', 'Linear_Mean_Value']]
    .merge(lin, on='Survey_Id')
    .merge(base[['Hospital_Id', 'Hospital_Name', 'Survey_Response_Rate_Percent']], on='Hospital_Id')
)

top6_ids = base.sort_values('No_Completed_Surveys', ascending=False).head(6)['Hospital_Id']

fig, ax = plt.subplots(figsize=(10, 5))
for hid in top6_ids:
    sub = r2[r2.Hospital_Id == hid].set_index('Category').reindex(lin['Category'])
    ax.plot(sub.index, sub['Survey_Response_Rate_Percent'], marker='o', label=sub['Hospital_Name'].iloc[0])
ax.set_ylabel('Response Rate %')
ax.set_title('Report 2: Response Rate by Measure Category, per Hospital (Top 6 by Volume)')
ax.legend(fontsize=8, loc='upper left', bbox_to_anchor=(1, 1))
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
"""),

("markdown", "## Report 3: Top 3 Counties by Survey Response Rate"),

("code", """\
report3 = (
    base.groupby(['County_Name', 'State'])['Survey_Response_Rate_Percent']
        .mean()
        .reset_index()
        .sort_values('Survey_Response_Rate_Percent', ascending=False)
        .head(3)
)
report3
"""),

("markdown", "## Report 4: Top 10 Hospitals Based on Survey Response Rate"),

("code", """\
report4 = (
    base[['Hospital_Name', 'City', 'State', 'Survey_Response_Rate_Percent']]
    .sort_values('Survey_Response_Rate_Percent', ascending=False)
    .head(10)
)

fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(report4['Hospital_Name'][::-1], report4['Survey_Response_Rate_Percent'][::-1], color='#2ca02c')
ax.set_xlabel('Response Rate %')
ax.set_title('Report 4: Top 10 Hospitals by Survey Response Rate')
plt.tight_layout()
plt.show()

report4
"""),

("markdown", "## Report 5: County and City-wise Hospital Rating (Drill-down)"),

("code", """\
report5 = (
    base.dropna(subset=['Patient_Survey_Star_Rating'])
        .groupby(['State', 'County_Name', 'City'])['Patient_Survey_Star_Rating']
        .mean()
        .round(2)
        .reset_index()
        .sort_values(['State', 'County_Name', 'City'])
)

print(f"{len(report5)} State/County/City combinations have a rating")
report5.sort_values('Patient_Survey_Star_Rating', ascending=False).head(15)
"""),

("markdown", "## Report 6: Hospitals Which Are in the Same City"),

("code", """\
city_counts = base.groupby(['City', 'State'])['Hospital_Id'].count().reset_index(name='Num_Hospitals')
report6 = city_counts[city_counts.Num_Hospitals > 1].sort_values('Num_Hospitals', ascending=False)

print(f"{len(report6)} cities have more than one hospital in the dataset")
report6.head(15)
"""),

("code", """\
top_city, top_state = report6.iloc[0][['City', 'State']]
print(f"Hospitals in {top_city}, {top_state}:")
base.loc[(base.City == top_city) & (base.State == top_state), 'Hospital_Name'].tolist()
"""),

("markdown", "## Report 7: Total Survey Response Rate by All Hospitals"),

("code", """\
report7_summary = base['Survey_Response_Rate_Percent'].agg(['mean', 'median', 'min', 'max']).round(2)
print(report7_summary)

fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(base['Survey_Response_Rate_Percent'].dropna(), bins=range(0, 65, 5), color='#8172b3', edgecolor='white')
ax.set_xlabel('Response Rate %')
ax.set_ylabel('Number of Hospitals')
ax.set_title('Report 7: Distribution of Survey Response Rate Across Hospitals')
plt.tight_layout()
plt.show()
"""),

("markdown", "## Report 8: New Insight -- What Drives Patient Satisfaction?"),

("code", """\
cat_avg = r2.groupby('Category')['Linear_Mean_Value'].mean().sort_values()

fig, ax = plt.subplots(figsize=(8, 6))
colors = ['#c44e52' if v < 83 else '#2ca02c' for v in cat_avg.values]
ax.barh(cat_avg.index, cat_avg.values, color=colors)
ax.set_xlabel('Avg Linear Mean Score')
ax.set_title('Report 8a: Avg Score by HCAHPS Category (National)')
plt.tight_layout()
plt.show()

corr_df = base.dropna(subset=['Survey_Response_Rate_Percent', 'Patient_Survey_Star_Rating'])
corr = corr_df['Survey_Response_Rate_Percent'].corr(corr_df['Patient_Survey_Star_Rating'])

fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(corr_df['Survey_Response_Rate_Percent'], corr_df['Patient_Survey_Star_Rating'], alpha=0.4, color='#2563eb')
ax.set_xlabel('Response Rate %')
ax.set_ylabel('Overall Star Rating')
ax.set_title(f'Report 8b: Response Rate vs Overall Star Rating (r = {corr:.2f})')
plt.tight_layout()
plt.show()

print(f"Lowest-scoring category nationally:  {cat_avg.index[0]} (avg {cat_avg.iloc[0]:.1f})")
print(f"Highest-scoring category nationally: {cat_avg.index[-1]} (avg {cat_avg.iloc[-1]:.1f})")
print(f"Correlation between response rate and overall star rating: r = {corr:.3f}")
print()
print("Insight: hospitals that get more patients to complete the survey tend to be rated")
print("higher overall, and 'Communication about medicines' is consistently the weakest")
print("HCAHPS category nationally -- a clear improvement target across hospitals.")
"""),
]
