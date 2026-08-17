ALTER TABLE hospital_operation_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL;

CREATE INDEX idx_hospital_operation_area
    ON hospital_operation_summary (hospital_service_area, discharge_count);

CREATE INDEX idx_hospital_operation_county
    ON hospital_operation_summary (hospital_county, discharge_count);

CREATE INDEX idx_hospital_operation_facility
    ON hospital_operation_summary (facility_name);
