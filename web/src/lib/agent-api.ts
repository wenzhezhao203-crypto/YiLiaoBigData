import type { DashboardFilters } from "@/lib/types";

export type AgentToolCall = { name: string; status: "success" | "failed" };

export type AgentChatData = {
  reply: string;
  tool_calls: AgentToolCall[];
};

type AgentResponse = {
  code: number;
  message: string;
  data: AgentChatData;
};

export type AgentReportType = "comprehensive" | "operations" | "patient" | "disease";
export type AgentReportData = {
  report_id: string;
  title: string;
  report_type: AgentReportType;
  download_path: string;
  scope: DashboardFilters;
  executive_summary: string;
  tool_calls: AgentToolCall[];
  generated_at: string;
};

const AGENT_BASE_URL = process.env.NEXT_PUBLIC_AGENT_API_BASE_URL ?? "/agent-api";

export async function sendAgentMessage(message: string, signal?: AbortSignal): Promise<AgentChatData> {
  const response = await fetch(`${AGENT_BASE_URL}/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });
  const payload = await response.json() as AgentResponse;
  if (!response.ok || payload.code !== 0) {
    const error = new Error(payload.data?.reply || payload.message || "Agent request failed");
    Object.assign(error, { toolCalls: payload.data?.tool_calls ?? [] });
    throw error;
  }
  return payload.data;
}

export async function createAndDownloadAgentReport(
  reportType: AgentReportType,
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<AgentReportData> {
  const response = await fetch(`${AGENT_BASE_URL}/ai/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report_type: reportType, filters }),
    signal,
  });
  const payload = await response.json() as { code: number; message: string; data?: AgentReportData | null };
  if (!response.ok || payload.code !== 0 || !payload.data) {
    throw new Error(payload.message || "报告生成失败，请稍后重试。");
  }
  const downloadResponse = await fetch(`${AGENT_BASE_URL}${payload.data.download_path}`, { signal });
  if (!downloadResponse.ok) throw new Error("报告已生成，但下载失败，请重试。");
  const blob = await downloadResponse.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "medical_analysis_report.docx";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  return payload.data;
}

type StreamHandlers = {
  onDelta: (text: string) => void;
  onToolCalls: (toolCalls: AgentToolCall[]) => void;
};

export async function streamAgentMessage(message: string, handlers: StreamHandlers, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`${AGENT_BASE_URL}/ai/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ message }),
    signal,
  });
  if (!response.ok || !response.body) throw new Error("AI 分析服务暂时不可用，请稍后重试。");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const event = frame.match(/^event: (.+)$/m)?.[1];
      const rawData = frame.match(/^data: (.+)$/m)?.[1];
      if (!event || !rawData) continue;
      const data = JSON.parse(rawData) as { text?: string; message?: string; tool_calls?: AgentToolCall[] };
      if (event === "delta" && data.text) handlers.onDelta(data.text);
      if (event === "tool_calls" || event === "done") handlers.onToolCalls(data.tool_calls ?? []);
      if (event === "error") throw new Error(data.message ?? "AI 分析服务暂时不可用，请稍后重试。");
    }
    if (done) break;
  }
}
