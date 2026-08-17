import type { ApiResponse, DashboardFilters, DrilldownResponse, AgeGenderItem, PaymentItem, DispositionItem, AdmissionItem, KpiData, HospitalItem, HospitalPage, DiseaseItem, SeverityItem } from "@/lib/types";

// Requests go through the Next.js rewrite so the browser only calls its own origin.
// This avoids cross-origin and private-network restrictions on localhost deployments.
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

function query(filters: DashboardFilters, extra: Record<string, string | number | undefined> = {}) {
  const params = new URLSearchParams();
  Object.entries({ ...filters, ...extra }).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  });
  const text = params.toString();
  return text ? `?${text}` : "";
}

async function request<T>(path: string, filters: DashboardFilters = {}, extra: Record<string, string | number | undefined> = {}, signal?: AbortSignal): Promise<ApiResponse<T>> {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort(), 15_000);
  const combinedSignal = signal
    ? AbortSignal.any([signal, timeoutController.signal])
    : timeoutController.signal;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}${query(filters, extra)}`, { signal: combinedSignal, cache: "no-store" });
  } catch (error) {
    if (timeoutController.signal.aborted && !signal?.aborted) {
      throw new Error("接口请求超时");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
  const payload = (await response.json()) as ApiResponse<T>;
  if (!response.ok || payload.code !== 0) throw new Error(payload.message || "数据请求失败");
  return payload;
}

export const dashboardApi = {
  areas: (signal?: AbortSignal) => request<{ hospital_service_area: string }[]>("/filters/areas", {}, {}, signal),
  counties: (area?: string, signal?: AbortSignal) => request<{ hospital_county: string }[]>("/filters/counties", { hospital_service_area: area }, {}, signal),
  facilities: (filters: DashboardFilters, signal?: AbortSignal) => request<{ facility_name: string }[]>("/filters/facilities", filters, {}, signal),
  ageGender: (filters: DashboardFilters, signal?: AbortSignal) => request<AgeGenderItem[]>("/dashboard/patient/age-gender", filters, {}, signal),
  payment: (filters: DashboardFilters, signal?: AbortSignal) => request<PaymentItem[]>("/dashboard/patient/payment", filters, {}, signal),
  disposition: (filters: DashboardFilters, signal?: AbortSignal) => request<DispositionItem[]>("/dashboard/patient/disposition", filters, { limit: 10 }, signal),
  admission: (filters: DashboardFilters, signal?: AbortSignal) => request<AdmissionItem[]>("/dashboard/patient/admission-emergency", filters, {}, signal),
  kpi: (filters: DashboardFilters, signal?: AbortSignal) => request<KpiData>("/dashboard/kpi", filters, {}, signal),
  resources: (filters: DashboardFilters, signal?: AbortSignal) => request<HospitalItem[]>("/dashboard/hospital/resources", filters, {}, signal),
  ranking: (filters: DashboardFilters, sortBy = "discharge_count", signal?: AbortSignal) => request<HospitalItem[]>("/dashboard/hospital/ranking", filters, { sort_by: sortBy, order: "desc", limit: 10 }, signal),
  comparison: (filters: DashboardFilters, page = 1, signal?: AbortSignal) => request<HospitalPage>("/dashboard/hospital/comparison", filters, { page, page_size: 8, sort_by: "discharge_count", order: "desc" }, signal),
  systems: (filters: DashboardFilters, signal?: AbortSignal) => request<DiseaseItem[]>("/dashboard/disease/systems", filters, {}, signal),
  diagnoses: (filters: DashboardFilters, signal?: AbortSignal) => request<DiseaseItem[]>("/dashboard/disease/top-diagnoses", filters, { limit: 10 }, signal),
  severity: (filters: DashboardFilters, signal?: AbortSignal) => request<SeverityItem[]>("/dashboard/disease/risk", filters, {}, signal),
  drilldown: (filters: DashboardFilters, level: "mdc" | "drg" | "ccsr", mdc?: string, drg?: string, signal?: AbortSignal) => request<DrilldownResponse["data"]>("/dashboard/disease/drilldown", filters, { level, apr_mdc_code: mdc, apr_drg_code: drg }, signal) as Promise<DrilldownResponse>,
};
