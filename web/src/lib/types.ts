export type DashboardFilters = {
  hospital_service_area?: string;
  hospital_county?: string;
  facility_name?: string;
};

export type ApiResponse<T> = {
  code: number;
  message: string;
  data: T;
  filters?: DashboardFilters;
  updated_at?: string | null;
};

export type AgeGenderItem = { age_group: string; age_group_sort: number | null; gender: string; discharge_count: number; discharge_ratio: number | null };
export type PaymentItem = { payment_typology_1: string; discharge_count: number; discharge_ratio: number | null; total_charges: number | null; total_costs: number | null; average_charge: number | null; average_cost: number | null };
export type DispositionItem = { patient_disposition: string; discharge_count: number; discharge_ratio: number | null; average_length_of_stay: number | null; total_charges: number | null; total_costs: number | null; average_charge: number | null; average_cost: number | null };
export type AdmissionItem = { type_of_admission: string; emergency_department_indicator: string | null; discharge_count: number; discharge_ratio: number | null; average_length_of_stay: number | null };
export type MedicalSurgicalItem = { apr_medical_surgical_description: string; discharge_count: number; discharge_ratio: number | null; average_length_of_stay: number | null; total_charges: number | null; total_costs: number | null; average_charge: number | null; average_cost: number | null };
export type KpiData = { hospital_count: number; discharge_count: number; average_length_of_stay: number | null; total_charges: number | null; total_costs: number | null; average_charge: number | null; average_cost: number | null; emergency_ratio: number | null; emergency_charges: number | null; non_emergency_charges: number | null; emergency_costs: number | null; non_emergency_costs: number | null };
export type HospitalItem = { rank?: number; facility_name: string; hospital_county: string; hospital_service_area: string; discharge_count: number; total_charges: number | null; total_costs: number | null; average_length_of_stay: number | null; average_cost: number | null; emergency_ratio: number | null };
export type HospitalPage = { items: HospitalItem[]; page: number; page_size: number; total: number };
export type DiseaseItem = { apr_mdc_code?: string; apr_mdc_description?: string; ccsr_diagnosis_code?: string; ccsr_diagnosis_description?: string; discharge_count: number; discharge_ratio: number | null; average_length_of_stay: number | null; total_charges: number | null; total_costs: number | null };
export type SeverityItem = { apr_severity_code: number; apr_severity_description: string; discharge_count: number; discharge_ratio: number | null; average_length_of_stay: number | null; total_charges: number | null; total_costs: number | null };
export type DrilldownItem = { code: string; description: string; discharge_count: number; total_charges: number | null; total_costs: number | null; average_length_of_stay: number | null };
export type DrilldownResponse = ApiResponse<DrilldownItem[]> & { breadcrumb: { level: string; code: string; description: string | null }[] };
