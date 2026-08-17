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
