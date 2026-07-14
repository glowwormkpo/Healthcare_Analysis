-- BI Mini Project: Healthcare Patient Survey Star Schema
-- NOTE: The original spec's "Dim_Country_Details" is populated at COUNTY grain
-- (Country_Name = County Name), since the source data (Health Care_Patient_survey_source.csv)
-- is US county-level and report requirements #3/#5 explicitly ask about "Counties".

CREATE TABLE Dim_Country_Details (
    Country_Id   INTEGER PRIMARY KEY,   -- surrogate key
    Country_Name TEXT NOT NULL,         -- County Name from source
    State        TEXT,
    City         TEXT,
    Zipcode      TEXT
);

CREATE TABLE Dim_Hospital_Details (
    Hospital_Id   INTEGER PRIMARY KEY,  -- Provider ID from source (natural key)
    Hospital_Name TEXT NOT NULL,
    Country_Id    INTEGER REFERENCES Dim_Country_Details(Country_Id),
    City          TEXT,
    Location      TEXT                 -- full address + lat/long, as provided
);

CREATE TABLE Dim_Measure_Details (
    Measure_Id         INTEGER PRIMARY KEY,  -- surrogate key
    Measure_Code        TEXT NOT NULL,        -- e.g. H_CLEAN_HSP_A_P (natural key)
    Measure_Start_Date  TEXT,
    Measure_End_Date    TEXT
);

CREATE TABLE Dim_Survey_Details (
    Survey_Id       INTEGER PRIMARY KEY,      -- surrogate key
    Measure_Id      INTEGER REFERENCES Dim_Measure_Details(Measure_Id),
    Survey_Question TEXT,
    Survey_Answer   TEXT
);

CREATE TABLE Fact_Patient_Survey (
    Fact_Id                                INTEGER PRIMARY KEY,
    Country_Id                             INTEGER REFERENCES Dim_Country_Details(Country_Id),
    Hospital_Id                            INTEGER REFERENCES Dim_Hospital_Details(Hospital_Id),
    Measure_Id                             INTEGER REFERENCES Dim_Measure_Details(Measure_Id),
    Survey_Id                              INTEGER REFERENCES Dim_Survey_Details(Survey_Id),
    No_Completed_Surveys                   REAL,
    No_Completed_Surveys_Footnote          TEXT,
    Survey_Response_Rate_Percent           REAL,
    Survey_Response_Rate_Percent_Footnote  TEXT,
    Linear_Mean_Value                      REAL,
    Answer_Percent                         REAL,
    Answer_Percent_Footnote                TEXT,
    Patient_Survey_Star_Rating             REAL,
    Patient_Survey_Star_Rating_Footnote    TEXT
);

CREATE INDEX idx_fact_hospital ON Fact_Patient_Survey(Hospital_Id);
CREATE INDEX idx_fact_measure  ON Fact_Patient_Survey(Measure_Id);
CREATE INDEX idx_fact_survey   ON Fact_Patient_Survey(Survey_Id);
CREATE INDEX idx_fact_country  ON Fact_Patient_Survey(Country_Id);
CREATE INDEX idx_hospital_country ON Dim_Hospital_Details(Country_Id);
