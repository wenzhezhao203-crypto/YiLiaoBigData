ALTER TABLE patient_payment_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY payment_typology_1 VARCHAR(100) NULL;

CREATE INDEX idx_payment_area
    ON patient_payment_summary (hospital_service_area, payment_typology_1);
CREATE INDEX idx_payment_county
    ON patient_payment_summary (hospital_county, payment_typology_1);
CREATE INDEX idx_payment_facility
    ON patient_payment_summary (facility_name, payment_typology_1);

ALTER TABLE patient_disposition_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY patient_disposition VARCHAR(100) NULL;

CREATE INDEX idx_disposition_area
    ON patient_disposition_summary (hospital_service_area, patient_disposition);
CREATE INDEX idx_disposition_county
    ON patient_disposition_summary (hospital_county, patient_disposition);
CREATE INDEX idx_disposition_facility
    ON patient_disposition_summary (facility_name, patient_disposition);

ALTER TABLE patient_admission_emergency_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY type_of_admission VARCHAR(50) NULL,
    MODIFY emergency_department_indicator CHAR(1) NULL;

CREATE INDEX idx_admission_area
    ON patient_admission_emergency_summary (
        hospital_service_area,
        type_of_admission,
        emergency_department_indicator
    );
CREATE INDEX idx_admission_county
    ON patient_admission_emergency_summary (
        hospital_county,
        type_of_admission,
        emergency_department_indicator
    );
CREATE INDEX idx_admission_facility
    ON patient_admission_emergency_summary (
        facility_name,
        type_of_admission,
        emergency_department_indicator
    );
