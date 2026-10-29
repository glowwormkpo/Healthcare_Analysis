-- ============================================================================
-- BI Mini Project: Healthcare Patient Survey -- Snowflake DDL
-- Run this in Snowsight (or SnowSQL) to create the database/schema/tables.
-- Mirrors schema.sql (SQLite) but with Snowflake-native types.
--
-- NOTE: Dim_Country_Details is populated at COUNTY grain (Country_Name = County
-- Name), since the source data is US county-level and report requirements
-- #3/#5 explicitly ask about counties.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS HEALTHCARE_BI;
CREATE SCHEMA IF NOT EXISTS HEALTHCARE_BI.PUBLIC;
USE DATABASE HEALTHCARE_BI;
USE SCHEMA PUBLIC;

CREATE OR REPLACE TABLE Dim_Country_Details (
    Country_Id   NUMBER(10)    PRIMARY KEY,   -- surrogate key
    Country_Name VARCHAR(100)  NOT NULL,      -- County Name from source
    State        VARCHAR(10),
    City         VARCHAR(100),
    Zipcode      VARCHAR(10)
);

CREATE OR REPLACE TABLE Dim_Hospital_Details (
    Hospital_Id   NUMBER(10)   PRIMARY KEY,   -- Provider ID from source (natural key)
    Hospital_Name VARCHAR(200) NOT NULL,
    Country_Id    NUMBER(10)   REFERENCES Dim_Country_Details(Country_Id),
    City          VARCHAR(100),
    Location      VARCHAR(500)                -- full address + lat/long
);

CREATE OR REPLACE TABLE Dim_Measure_Details (
    Measure_Id          NUMBER(10)  PRIMARY KEY,  -- surrogate key
    Measure_Code        VARCHAR(50) NOT NULL,     -- e.g. H_CLEAN_HSP_A_P
    Measure_Start_Date  DATE,
    Measure_End_Date    DATE
);

CREATE OR REPLACE TABLE Dim_Survey_Details (
    Survey_Id       NUMBER(10)  PRIMARY KEY,     -- surrogate key
    Measure_Id      NUMBER(10)  REFERENCES Dim_Measure_Details(Measure_Id),
    Survey_Question VARCHAR(500),
    Survey_Answer   VARCHAR(500)
);

CREATE OR REPLACE TABLE Fact_Patient_Survey (
    Fact_Id                                NUMBER(10) PRIMARY KEY,
    Country_Id                             NUMBER(10) REFERENCES Dim_Country_Details(Country_Id),
    Hospital_Id                            NUMBER(10) REFERENCES Dim_Hospital_Details(Hospital_Id),
    Measure_Id                             NUMBER(10) REFERENCES Dim_Measure_Details(Measure_Id),
    Survey_Id                              NUMBER(10) REFERENCES Dim_Survey_Details(Survey_Id),
    No_Completed_Surveys                   NUMBER(10,2),
    No_Completed_Surveys_Footnote          VARCHAR(20),
    Survey_Response_Rate_Percent           NUMBER(5,2),
    Survey_Response_Rate_Percent_Footnote  VARCHAR(20),
    Linear_Mean_Value                      NUMBER(6,2),
    Answer_Percent                         NUMBER(5,2),
    Answer_Percent_Footnote                VARCHAR(20),
    Patient_Survey_Star_Rating             NUMBER(2,1),
    Patient_Survey_Star_Rating_Footnote    VARCHAR(20)
);

-- ============================================================================
-- Staging: file format + internal stage for loading the exported CSVs
-- ============================================================================

CREATE OR REPLACE FILE FORMAT csv_format
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    NULL_IF = ('', 'None', 'NaN', 'null');

CREATE OR REPLACE STAGE healthcare_stage
    FILE_FORMAT = csv_format;

-- ============================================================================
-- Load order matters (parents before children, due to FKs):
--   Dim_Country_Details -> Dim_Hospital_Details -> Dim_Measure_Details
--   -> Dim_Survey_Details -> Fact_Patient_Survey
--
-- From SnowSQL, PUT each CSV to the stage (adjust local paths), then COPY INTO:
--
--   PUT file:///local/path/Dim_Country_Details.csv  @healthcare_stage AUTO_COMPRESS=TRUE;
--   PUT file:///local/path/Dim_Hospital_Details.csv  @healthcare_stage AUTO_COMPRESS=TRUE;
--   PUT file:///local/path/Dim_Measure_Details.csv   @healthcare_stage AUTO_COMPRESS=TRUE;
--   PUT file:///local/path/Dim_Survey_Details.csv    @healthcare_stage AUTO_COMPRESS=TRUE;
--   PUT file:///local/path/Fact_Patient_Survey.csv   @healthcare_stage AUTO_COMPRESS=TRUE;
--
-- (In Snowsight instead of SnowSQL: use the "+" > Load Data UI to upload each
-- CSV straight into its matching table -- skips the PUT/stage steps below.)
-- ============================================================================

COPY INTO Dim_Country_Details
    FROM @healthcare_stage/Dim_Country_Details.csv.gz
    FILE_FORMAT = (FORMAT_NAME = csv_format)
    ON_ERROR = 'ABORT_STATEMENT';

COPY INTO Dim_Hospital_Details
    FROM @healthcare_stage/Dim_Hospital_Details.csv.gz
    FILE_FORMAT = (FORMAT_NAME = csv_format)
    ON_ERROR = 'ABORT_STATEMENT';

COPY INTO Dim_Measure_Details
    FROM @healthcare_stage/Dim_Measure_Details.csv.gz
    FILE_FORMAT = (FORMAT_NAME = csv_format)
    ON_ERROR = 'ABORT_STATEMENT';

COPY INTO Dim_Survey_Details
    FROM @healthcare_stage/Dim_Survey_Details.csv.gz
    FILE_FORMAT = (FORMAT_NAME = csv_format)
    ON_ERROR = 'ABORT_STATEMENT';

COPY INTO Fact_Patient_Survey
    FROM @healthcare_stage/Fact_Patient_Survey.csv.gz
    FILE_FORMAT = (FORMAT_NAME = csv_format)
    ON_ERROR = 'ABORT_STATEMENT';

-- ============================================================================
-- Sanity check after loading
-- ============================================================================
SELECT 'Dim_Country_Details' AS table_name, COUNT(*) AS row_count FROM Dim_Country_Details
UNION ALL SELECT 'Dim_Hospital_Details', COUNT(*) FROM Dim_Hospital_Details
UNION ALL SELECT 'Dim_Measure_Details',  COUNT(*) FROM Dim_Measure_Details
UNION ALL SELECT 'Dim_Survey_Details',   COUNT(*) FROM Dim_Survey_Details
UNION ALL SELECT 'Fact_Patient_Survey',  COUNT(*) FROM Fact_Patient_Survey;
-- Expected: 629, 700, 50, 50, 34999
