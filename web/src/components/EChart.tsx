"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

export function EChart({ option, className = "chart", onClick }: { option: EChartsOption; className?: string; onClick?: (params: unknown) => void }) {
  const elementRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    const chart = echarts.init(element, undefined, { renderer: "canvas" });
    chart.setOption(option, true);
    if (onClick) chart.on("click", onClick);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element);
    return () => { observer.disconnect(); if (onClick) chart.off("click", onClick); chart.dispose(); };
  }, [option, onClick]);
  return <div ref={elementRef} className={className} />;
}
