-- Execute after the Spark job has written patient_medical_surgical_summary,
-- or execute first to provision the table and its query indexes.
CREATE TABLE IF NOT EXISTS patient_medical_surgical_summary (
    hospital_service_area VARCHAR(100) NULL,
    hospital_county VARCHAR(100) NULL,
    facility_name VARCHAR(255) NULL,
    apr_medical_surgical_description VARCHAR(50) NULL,
    discharge_count BIGINT NOT NULL,
    length_of_stay_sum DECIMAL(20,2) NULL,
    total_charges_sum DECIMAL(20,2) NULL,
    total_costs_sum DECIMAL(20,2) NULL,
    updated_at TIMESTAMP NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_medical_surgical_area
    ON patient_medical_surgical_summary (
        hospital_service_area,
        apr_medical_surgical_description
    );

CREATE INDEX idx_medical_surgical_county
    ON patient_medical_surgical_summary (
        hospital_county,
        apr_medical_surgical_description
    );

CREATE INDEX idx_medical_surgical_facility
    ON patient_medical_surgical_summary (
        facility_name,
        apr_medical_surgical_description
    );
