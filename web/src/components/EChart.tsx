"use client";

import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

export function EChart({ option, className = "chart", onClick }: { option: EChartsOption; className?: string; onClick?: (params: unknown) => void }) {
  const elementRef = useRef<HTMLDivElement>(null);
  const clickHandlerRef = useRef(onClick);

  useEffect(() => { clickHandlerRef.current = onClick; }, [onClick]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    const chart = echarts.init(element, undefined, { renderer: "canvas" });
    chart.setOption(option, true);
    const handleClick = (params: unknown) => clickHandlerRef.current?.(params);
    chart.on("click", handleClick);
    let disposed = false;
    const observer = new ResizeObserver(() => {
      if (!disposed && !chart.isDisposed()) chart.resize();
    });
    observer.observe(element);
    return () => {
      disposed = true;
      observer.disconnect();
      chart.off("click", handleClick);
      if (!chart.isDisposed()) chart.dispose();
    };
  }, [option]);
  return <div ref={elementRef} className={className} />;
}
