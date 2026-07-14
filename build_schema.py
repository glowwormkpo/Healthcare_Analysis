import pandas as pd
import sqlite3
import numpy as np

src = "/sessions/intelligent-compassionate-gates/mnt/uploads/Health Care_Patient_survey_source.csv"
df = pd.read_csv(src, dtype=str)

def to_num(s):
    return pd.to_numeric(s, errors='coerce')

df['Answer Percent_n'] = to_num(df['Answer Percent'])
df['Linear Mean Value_n'] = to_num(df['Linear Mean Value'])
df['Number of Completed Surveys_n'] = to_num(df['Number of Completed Surveys'])
df['Survey Response Rate Percent_n'] = to_num(df['Survey Response Rate Percent'])
df['Patient Survey Star Rating_n'] = to_num(df['Patient Survey Star Rating'])

df['County Name'] = df['County Name'].fillna('UNKNOWN')

# ---- Dim_Country_Details (County/State/City/Zip grain, per report requirements re: counties) ----
county_dim = df[['County Name','State','City','ZIP Code']].drop_duplicates().reset_index(drop=True)
county_dim.insert(0, 'Country_Id', range(1, len(county_dim)+1))
county_dim.columns = ['Country_Id','Country_Name','State','City','Zipcode']
# Country_Name here holds the County Name (source data is county-grain, not nation-grain; see notes)

df = df.merge(county_dim, left_on=['County Name','State','City','ZIP Code'],
              right_on=['Country_Name','State','City','Zipcode'], how='left')

# ---- Dim_Hospital_Details ----
hosp_dim = df[['Provider ID','Hospital Name','City','Country_Id','Location']].drop_duplicates(subset=['Provider ID']).reset_index(drop=True)
hosp_dim = hosp_dim.rename(columns={'Provider ID':'Hospital_Id','Hospital Name':'Hospital_Name','City':'City','Location':'Location'})
hosp_dim = hosp_dim[['Hospital_Id','Hospital_Name','Country_Id','City','Location']]

# ---- Dim_Measure_Details ----
measure_dim = df[['Measure ID','Measure Start Date','Measure End Date']].drop_duplicates(subset=['Measure ID']).reset_index(drop=True)
measure_dim.insert(0, 'Measure_Id', range(1, len(measure_dim)+1))
measure_dim = measure_dim.rename(columns={'Measure ID':'Measure_Code','Measure Start Date':'Measure_Start_Date','Measure End Date':'Measure_End_Date'})
measure_dim = measure_dim[['Measure_Id','Measure_Code','Measure_Start_Date','Measure_End_Date']]

df = df.merge(measure_dim[['Measure_Id','Measure_Code']], left_on='Measure ID', right_on='Measure_Code', how='left')

# ---- Dim_Survey_Details ----
survey_dim = df[['Measure_Id','Question','Answer Description']].drop_duplicates(subset=['Measure_Id']).reset_index(drop=True)
survey_dim.insert(0, 'Survey_Id', range(1, len(survey_dim)+1))
survey_dim = survey_dim.rename(columns={'Question':'Survey_Question','Answer Description':'Survey_Answer'})
survey_dim = survey_dim[['Survey_Id','Measure_Id','Survey_Question','Survey_Answer']]

df = df.merge(survey_dim[['Survey_Id','Measure_Id']], on='Measure_Id', how='left')

# ---- Fact_Patient_Survey ----
fact = df[['Country_Id','Hospital_Id' if False else 'Provider ID','Measure_Id','Survey_Id',
           'Number of Completed Surveys_n','Number of Completed Surveys Footnote',
           'Survey Response Rate Percent_n','Survey Response Rate Percent Footnote',
           'Linear Mean Value_n','Answer Percent_n','Answer Percent Footnote',
           'Patient Survey Star Rating_n','Patient Survey Star Rating Footnote']].copy()
fact = fact.rename(columns={
    'Provider ID':'Hospital_Id',
    'Number of Completed Surveys_n':'No_Completed_Surveys',
    'Number of Completed Surveys Footnote':'No_Completed_Surveys_Footnote',
    'Survey Response Rate Percent_n':'Survey_Response_Rate_Percent',
    'Survey Response Rate Percent Footnote':'Survey_Response_Rate_Percent_Footnote',
    'Linear Mean Value_n':'Linear_Mean_Value',
    'Answer Percent_n':'Answer_Percent',
    'Answer Percent Footnote':'Answer_Percent_Footnote',
    'Patient Survey Star Rating_n':'Patient_Survey_Star_Rating',
    'Patient Survey Star Rating Footnote':'Patient_Survey_Star_Rating_Footnote',
})
fact.insert(0, 'Fact_Id', range(1, len(fact)+1))

print("county_dim", county_dim.shape)
print("hosp_dim", hosp_dim.shape)
print("measure_dim", measure_dim.shape)
print("survey_dim", survey_dim.shape)
print("fact", fact.shape)

# ---- Write to SQLite ----
db_path = "/tmp/healthcare_bi.db"
conn = sqlite3.connect(db_path)
county_dim.to_sql('Dim_Country_Details', conn, if_exists='replace', index=False)
hosp_dim.to_sql('Dim_Hospital_Details', conn, if_exists='replace', index=False)
measure_dim.to_sql('Dim_Measure_Details', conn, if_exists='replace', index=False)
survey_dim.to_sql('Dim_Survey_Details', conn, if_exists='replace', index=False)
fact.to_sql('Fact_Patient_Survey', conn, if_exists='replace', index=False)
conn.commit()
conn.close()
print("done", db_path)
