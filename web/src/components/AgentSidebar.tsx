"use client";

import { Bot, ChevronDown, LoaderCircle, Send, Sparkles, Wrench } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { streamAgentMessage, type AgentToolCall } from "@/lib/agent-api";

type Message = { id: number; role: "assistant" | "user"; content: string; toolCalls?: AgentToolCall[] };
type PipeTable = { intro: string; headers: string[]; rows: string[][]; conclusion: string };

const SUGGESTIONS = ["全量数据的急诊患者占比是多少？", "住院量最高的疾病系统是什么？", "哪家医院的出院量最高？"];

function renderInline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) => part.startsWith("**") && part.endsWith("**")
    ? <strong key={index}>{part.slice(2, -2)}</strong>
    : part);
}

function parseFlattenedPipeTable(line: string): PipeTable | null {
  if (!line.includes("|")) return null;
  const cells = line.split("|").map(cell => cell.trim()).filter(Boolean);
  const separatorIndex = cells.findIndex(cell => /^:?-{3,}:?$/.test(cell));
  if (separatorIndex < 0) return null;
  const headerStart = separatorIndex >= 3 ? separatorIndex - 3 : separatorIndex;
  let intro = cells.slice(0, headerStart).join(" ").replace(/[：:]$/, "");
  const headers = cells.slice(headerStart, separatorIndex);
  if (headers.length !== 3) headers.splice(0, headers.length, "支付方式", "出院人次", "占比");
  const titleSeparator = Math.max(headers[0].lastIndexOf("："), headers[0].lastIndexOf(":"));
  if (titleSeparator >= 0) { intro = [intro, headers[0].slice(0, titleSeparator)].filter(Boolean).join(" "); headers[0] = headers[0].slice(titleSeparator + 1).trim() || "支付方式"; }
  const dataStart = cells.findIndex((cell, index) => index >= separatorIndex && !/^:?-{3,}:?$/.test(cell));
  if (dataStart < 0) return null;
  const data = cells.slice(dataStart); const rows: string[][] = []; let position = 0;
  while (position + 2 < data.length && /^\d[\d,]*(?:\.\d+)?$/.test(data[position + 1]) && /^\d+(?:\.\d+)?%$/.test(data[position + 2])) { rows.push(data.slice(position, position + 3)); position += 3; }
  return rows.length ? { intro, headers, rows, conclusion: data.slice(position).join(" ") } : null;
}

function renderAssistantContent(content: string) {
  const lines = content.replace(/\r/g, "").split("\n"); const blocks: ReactNode[] = []; let index = 0;
  while (index < lines.length) {
    const line = lines[index].trim(); if (!line) { index += 1; continue; }
    const table = parseFlattenedPipeTable(line);
    if (table) { blocks.push(<section className="agent-data-table" key={index}>{table.intro && <p className="agent-table-intro">{renderInline(table.intro)}</p>}<div className="agent-table-row agent-table-heading">{table.headers.map((header, itemIndex) => <span key={itemIndex}>{header}</span>)}</div>{table.rows.map((row, rowIndex) => <div className="agent-table-row" key={rowIndex}>{row.map((cell, itemIndex) => <span key={itemIndex}>{cell}</span>)}</div>)}{table.conclusion && <p className="agent-table-conclusion">{renderInline(table.conclusion)}</p>}</section>); index += 1; continue; }
    if (/^#{1,3}\s+/.test(line)) { blocks.push(<h3 key={index}>{renderInline(line.replace(/^#{1,3}\s+/, ""))}</h3>); index += 1; continue; }
    if (/^(?:[-*]|\d+\.)\s+/.test(line)) { const items: string[] = []; while (index < lines.length && /^(?:[-*]|\d+\.)\s+/.test(lines[index].trim())) { items.push(lines[index].trim().replace(/^(?:[-*]|\d+\.)\s+/, "")); index += 1; } blocks.push(<ul key={`list-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item)}</li>)}</ul>); continue; }
    blocks.push(<p key={index}>{renderInline(line)}</p>); index += 1;
  }
  return blocks.length ? blocks : <span className="agent-cursor" aria-label="正在生成回答" />;
}

export function AgentWorkspace() {
  const [input, setInput] = useState(""); const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{ id: 0, role: "assistant", content: "你好，我可以基于当前住院数据回答医院运营、患者结构、急诊、疾病和费用相关问题。" }]);
  const nextId = useRef(1); const messageListRef = useRef<HTMLDivElement>(null);
  useEffect(() => { messageListRef.current?.scrollTo({ top: messageListRef.current.scrollHeight, behavior: "smooth" }); }, [messages, sending]);

  const submit = async (event?: FormEvent, prompt = input) => {
    event?.preventDefault(); const message = prompt.trim(); if (!message || sending) return;
    const assistantMessageId = nextId.current++;
    setMessages(current => [...current, { id: nextId.current++, role: "user", content: message }, { id: assistantMessageId, role: "assistant", content: "" }]);
    setInput(""); setSending(true);
    try {
      await streamAgentMessage(message, {
        onDelta: text => setMessages(current => current.map(item => item.id === assistantMessageId ? { ...item, content: item.content + text } : item)),
        onToolCalls: toolCalls => setMessages(current => current.map(item => item.id === assistantMessageId ? { ...item, toolCalls } : item)),
      });
    } catch (error) {
      const toolCalls = error instanceof Error && "toolCalls" in error ? error.toolCalls as AgentToolCall[] : [];
      setMessages(current => current.map(item => item.id === assistantMessageId ? { ...item, content: error instanceof Error ? error.message : "暂时无法连接 AI 分析服务，请稍后重试。", toolCalls } : item));
    } finally { setSending(false); }
  };

  return <section className="agent-workspace">
    <aside className="agent-conversation">
      <header className="agent-workspace-head"><div><Sparkles size={18}/><div><strong>AI 数据分析助手</strong><small>住院出院数据智能问答</small></div></div></header>
      <div className="agent-messages" ref={messageListRef} aria-live="polite">
        {messages.map(message => <article className={`agent-message ${message.role}`} key={message.id}>{message.role === "assistant" && <Bot size={15}/>}<div className="agent-bubble">{message.role === "assistant" ? renderAssistantContent(message.content) : <p>{message.content}</p>}{message.toolCalls?.map(tool => <span className={`agent-tool ${tool.status}`} key={`${message.id}-${tool.name}`}><Wrench size={11}/>{tool.name}</span>)}</div></article>)}
        {sending && <article className="agent-message assistant"><LoaderCircle className="agent-spin" size={15}/><div className="agent-status">正在分析数据...</div></article>}
      </div>
      <div className="agent-suggestions"><span>推荐提问</span>{SUGGESTIONS.map(suggestion => <button disabled={sending} key={suggestion} onClick={() => submit(undefined, suggestion)}>{suggestion}<ChevronDown size={12}/></button>)}</div>
      <form className="agent-input" onSubmit={event => submit(event)}><textarea value={input} onChange={event => setInput(event.target.value)} placeholder="请输入数据分析问题" maxLength={500} rows={2}/><button disabled={!input.trim() || sending} aria-label="发送问题" title="发送"><Send size={16}/></button></form>
    </aside>
    <section className="agent-chart-stage"><div className="agent-chart-empty"><Sparkles size={25}/><strong>分析图表</strong><span>等待 Agent 返回可视化指令</span></div></section>
  </section>;
}
