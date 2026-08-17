ALTER TABLE disease_system_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY apr_mdc_code VARCHAR(30) NULL,
    MODIFY apr_mdc_description VARCHAR(500) NULL;

CREATE INDEX idx_disease_system_area
    ON disease_system_summary (hospital_service_area, apr_mdc_code);
CREATE INDEX idx_disease_system_county
    ON disease_system_summary (hospital_county, apr_mdc_code);
CREATE INDEX idx_disease_system_facility
    ON disease_system_summary (facility_name, apr_mdc_code);

ALTER TABLE diagnosis_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY ccsr_diagnosis_code VARCHAR(30) NULL,
    MODIFY ccsr_diagnosis_description VARCHAR(500) NULL;

CREATE INDEX idx_diagnosis_area
    ON diagnosis_summary (hospital_service_area, discharge_count);
CREATE INDEX idx_diagnosis_county
    ON diagnosis_summary (hospital_county, discharge_count);
CREATE INDEX idx_diagnosis_facility
    ON diagnosis_summary (facility_name, discharge_count);

ALTER TABLE patient_risk_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY apr_severity_description VARCHAR(50) NULL;

CREATE INDEX idx_risk_area
    ON patient_risk_summary (hospital_service_area, apr_severity_code, apr_risk_of_mortality);
CREATE INDEX idx_risk_county
    ON patient_risk_summary (hospital_county, apr_severity_code, apr_risk_of_mortality);
CREATE INDEX idx_risk_facility
    ON patient_risk_summary (facility_name, apr_severity_code, apr_risk_of_mortality);

ALTER TABLE disease_drilldown_summary
    MODIFY hospital_service_area VARCHAR(100) NULL,
    MODIFY hospital_county VARCHAR(100) NULL,
    MODIFY facility_name VARCHAR(255) NULL,
    MODIFY apr_mdc_code VARCHAR(30) NULL,
    MODIFY apr_mdc_description VARCHAR(500) NULL,
    MODIFY apr_drg_code VARCHAR(30) NULL,
    MODIFY apr_drg_description VARCHAR(500) NULL,
    MODIFY ccsr_diagnosis_code VARCHAR(30) NULL,
    MODIFY ccsr_diagnosis_description VARCHAR(500) NULL;

CREATE INDEX idx_drilldown_area
    ON disease_drilldown_summary (hospital_service_area, apr_mdc_code, apr_drg_code);
CREATE INDEX idx_drilldown_county
    ON disease_drilldown_summary (hospital_county, apr_mdc_code, apr_drg_code);
CREATE INDEX idx_drilldown_facility
    ON disease_drilldown_summary (facility_name, apr_mdc_code, apr_drg_code);
