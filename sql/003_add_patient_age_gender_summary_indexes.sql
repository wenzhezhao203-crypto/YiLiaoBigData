ALTER TABLE patient_age_gender_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY age_group VARCHAR(30) NULL,
    MODIFY gender VARCHAR(30) NULL;

CREATE INDEX idx_age_gender_area
    ON patient_age_gender_summary (hospital_service_area, age_group_sort, gender);

CREATE INDEX idx_age_gender_county
    ON patient_age_gender_summary (hospital_county, age_group_sort, gender);

CREATE INDEX idx_age_gender_facility
    ON patient_age_gender_summary (facility_name, age_group_sort, gender);
