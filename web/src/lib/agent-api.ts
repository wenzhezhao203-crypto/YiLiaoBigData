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
