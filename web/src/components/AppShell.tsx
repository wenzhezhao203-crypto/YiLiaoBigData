"use client";

import { BarChart3, Hospital, MessageSquareText } from "lucide-react";
import { useState } from "react";
import { AgentWorkspace } from "@/components/AgentSidebar";
import { Dashboard } from "@/components/Dashboard";

type View = "dashboard" | "agent";

export function AppShell() {
  const [view, setView] = useState<View>("dashboard");

  return <main className="app-shell">
    <header className="app-topbar">
      <div className="app-brand"><Hospital size={27}/><div><small>MEDICAL INTELLIGENCE</small><h1>智慧医疗住院数据分析平台</h1></div></div>
      <nav className="app-tabs" aria-label="主视图切换">
        <button className={view === "dashboard" ? "active" : ""} onClick={() => setView("dashboard")}><BarChart3 size={16}/>BI 大屏</button>
        <button className={view === "agent" ? "active" : ""} onClick={() => setView("agent")}><MessageSquareText size={16}/>AI 分析助手</button>
      </nav>
    </header>
    {view === "dashboard" ? <Dashboard /> : <AgentWorkspace />}
  </main>;
}
