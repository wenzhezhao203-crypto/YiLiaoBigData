"use client";

import type { EChartsOption } from "echarts";
import { ChevronRight, Expand, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { EChart } from "@/components/EChart";
import { Panel, State } from "@/components/Panel";
import { dashboardApi } from "@/lib/api";
import { days, money, number } from "@/lib/format";
import type { DashboardFilters, DrilldownItem, DrilldownResponse } from "@/lib/types";

type DrillLevel = "mdc" | "drg" | "ccsr";
type BubbleNode = { name: string; code: string; description: string; dischargeCount: number; totalCharges: number | null; totalCosts: number | null; averageLengthOfStay: number | null; symbolSize: number };

const LEVEL_LABELS: Record<DrillLevel, string> = { mdc: "疾病系统（MDC）", drg: "病例组（DRG）", ccsr: "具体诊断（CCSR）" };

function buildBubbleOption(items: DrilldownItem[], level: DrillLevel): EChartsOption {
  const largest = Math.max(...items.map(item => item.discharge_count), 1);
  const nodes: BubbleNode[] = items.map(item => ({
    name: item.code,
    code: item.code,
    description: item.description || "暂无描述",
    dischargeCount: item.discharge_count,
    totalCharges: item.total_charges,
    totalCosts: item.total_costs,
    averageLengthOfStay: item.average_length_of_stay,
    symbolSize: Math.round(16 + Math.sqrt(item.discharge_count / largest) * 66),
  }));
  const colors = level === "mdc" ? ["#287cff", "#21c7e8", "#51d39d"] : level === "drg" ? ["#36b6f0", "#50d1c1", "#86c76b"] : ["#5b9dff", "#35c8de", "#a4d05b"];

  return {
    tooltip: {
      trigger: "item", backgroundColor: "#061725", borderColor: "#2b95ca", borderWidth: 1, padding: 11, textStyle: { color: "#e8f5ff", fontSize: 12 },
      formatter: (params: unknown) => {
        const node = (params as { data?: BubbleNode }).data;
        if (!node) return "";
        return `<div style="font-weight:700;color:#74d7f4;margin-bottom:6px">${node.code}</div><div style="max-width:280px;margin-bottom:7px">${node.description}</div><div>出院量：<b>${number(node.dischargeCount)}</b></div><div>平均住院天数：<b>${days(node.averageLengthOfStay)}</b></div><div>总收费：<b>${money(node.totalCharges)}</b></div><div>总成本：<b>${money(node.totalCosts)}</b></div>`;
      },
    },
    animationDuration: 850, animationDurationUpdate: 900, animationEasingUpdate: "cubicInOut",
    series: [{
      type: "graph", layout: "force", data: nodes, links: [], roam: true, draggable: false, cursor: level === "ccsr" ? "default" : "pointer",
      label: { show: true, position: "inside", color: "#f8fdff", fontSize: 11, fontWeight: 700, formatter: "{b}", textBorderColor: "rgba(1, 24, 39, .65)", textBorderWidth: 2 }, itemStyle: { color: (params: { dataIndex: number }) => colors[params.dataIndex % colors.length], opacity: .88, borderColor: "rgba(223,248,255,.7)", borderWidth: 1 },
      emphasis: { scale: true, itemStyle: { borderColor: "#f2fbff", borderWidth: 2 } },
      force: { repulsion: 105, gravity: .32, edgeLength: 20, friction: .48, layoutAnimation: true },
    }],
  };
}

export function DiseaseDrilldown({ filters }: { filters: DashboardFilters }) {
  const [level, setLevel] = useState<DrillLevel>("mdc");
  const [mdc, setMdc] = useState<string>();
  const [drg, setDrg] = useState<string>();
  const [result, setResult] = useState<DrilldownResponse>();
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => { setLevel("mdc"); setMdc(undefined); setDrg(undefined); }, [filters.hospital_service_area, filters.hospital_county, filters.facility_name]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    dashboardApi.drilldown(filters, level, mdc, drg, controller.signal).then(setResult).catch(error => { if (error.name !== "AbortError") setResult(undefined); }).finally(() => setLoading(false));
    return () => controller.abort();
  }, [filters, level, mdc, drg]);

  const navigate = (item: { code: string }) => {
    if (level === "mdc") { setMdc(item.code); setDrg(undefined); setLevel("drg"); }
    else if (level === "drg") { setDrg(item.code); setLevel("ccsr"); }
  };
  const resetToMdc = () => { setLevel("mdc"); setMdc(undefined); setDrg(undefined); };
  const openModal = () => { resetToMdc(); setModalOpen(true); };
  const chartOption = useMemo(() => buildBubbleOption(result?.data ?? [], level), [result?.data, level]);
  const breadcrumb = result?.breadcrumb ?? [];
  const handleBubbleClick = (params: unknown) => { const node = (params as { data?: BubbleNode }).data; if (node && level !== "ccsr") navigate({ code: node.code }); };

  return <><Panel title="疾病分层下钻" action={<button className="drill-modal-trigger" onClick={openModal} title="打开疾病分层气泡图" aria-label="打开疾病分层气泡图"><Expand size={15}/></button>}>
    <div className="crumbs"><button onClick={resetToMdc}>全部疾病系统</button>{breadcrumb.map((item, index) => <span key={item.code}><ChevronRight size={13}/><button onClick={() => index === 0 ? (setLevel("drg"), setDrg(undefined)) : setLevel("ccsr")}>{item.description}</button></span>)}</div>
    <div className="drill-list">
      {loading ? <State>正在加载疾病路径...</State> : result?.data.map(item => <button className="drill-node" key={item.code} onClick={() => navigate(item)} disabled={level === "ccsr"}><span><b>{item.code}</b><em>{item.description}</em></span><strong>{number(item.discharge_count)}</strong>{level !== "ccsr" && <ChevronRight size={17}/>}</button>)}
      {!loading && !result?.data.length && <State>当前范围暂无疾病数据</State>}
    </div>
  </Panel>
  {modalOpen && <div className="drill-modal-backdrop" role="presentation" onMouseDown={() => setModalOpen(false)}><section className="drill-modal" role="dialog" aria-modal="true" aria-label="疾病分层气泡图" onMouseDown={event => event.stopPropagation()}>
    <header className="drill-modal-head"><div className="drill-modal-path"><span className="drill-level">{LEVEL_LABELS[level]}</span><div><button onClick={resetToMdc}>疾病系统</button>{breadcrumb.map((item, index) => <span key={item.code}><ChevronRight size={13}/><button onClick={() => index === 0 ? (setLevel("drg"), setDrg(undefined)) : setLevel("ccsr")}>{item.description}</button></span>)}</div></div><button className="drill-modal-close" onClick={() => setModalOpen(false)} title="关闭"><X size={19}/></button></header>
    <div className="drill-modal-body">{loading ? <State>正在加载疾病路径...</State> : result?.data.length ? <EChart className="drill-bubble-chart" option={chartOption} onClick={handleBubbleClick}/> : <State>当前范围暂无疾病数据</State>}</div>
    <footer className="drill-modal-foot">{level === "ccsr" ? "已到达具体诊断层" : "点击气泡进入下一层"}</footer>
  </section></div>}</>;
}
