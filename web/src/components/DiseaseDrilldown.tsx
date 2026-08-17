"use client";

import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";
import { dashboardApi } from "@/lib/api";
import { number } from "@/lib/format";
import type { DashboardFilters, DrilldownResponse } from "@/lib/types";
import { Panel, State } from "@/components/Panel";

export function DiseaseDrilldown({ filters }: { filters: DashboardFilters }) {
  const [level, setLevel] = useState<"mdc" | "drg" | "ccsr">("mdc");
  const [mdc, setMdc] = useState<string>();
  const [drg, setDrg] = useState<string>();
  const [result, setResult] = useState<DrilldownResponse>();
  const [loading, setLoading] = useState(true);

  useEffect(() => { setLevel("mdc"); setMdc(undefined); setDrg(undefined); }, [filters.hospital_service_area, filters.hospital_county, filters.facility_name]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    dashboardApi.drilldown(filters, level, mdc, drg, controller.signal)
      .then(setResult)
      .catch((error) => { if (error.name !== "AbortError") setResult(undefined); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [filters, level, mdc, drg]);

  const navigate = (item: { code: string }) => {
    if (level === "mdc") { setMdc(item.code); setLevel("drg"); }
    else if (level === "drg") { setDrg(item.code); setLevel("ccsr"); }
  };

  return <Panel title="疾病分层下钻">
    <div className="crumbs"><button onClick={() => { setLevel("mdc"); setMdc(undefined); setDrg(undefined); }}>全部疾病系统</button>{result?.breadcrumb.map((item, index) => <span key={item.code}><ChevronRight size={13}/><button onClick={() => index === 0 ? (setLevel("drg"), setDrg(undefined)) : setLevel("ccsr")}>{item.description}</button></span>)}</div>
    <div className="drill-list">
      {loading ? <State>正在加载疾病路径...</State> : result?.data.map((item) => <button className="drill-node" key={item.code} onClick={() => navigate(item)} disabled={level === "ccsr"}>
        <span><b>{item.code}</b><em>{item.description}</em></span><strong>{number(item.discharge_count)}</strong>{level !== "ccsr" && <ChevronRight size={17}/>}</button>)}
      {!loading && !result?.data.length && <State>当前范围暂无疾病数据</State>}
    </div>
  </Panel>;
}
