"use client";

import { Bot, ChevronDown, LoaderCircle, Send, Sparkles, Wrench, X } from "lucide-react";
import { FormEvent, useRef, useState } from "react";
import { streamAgentMessage, type AgentToolCall } from "@/lib/agent-api";

type Message = {
  id: number;
  role: "assistant" | "user";
  content: string;
  toolCalls?: AgentToolCall[];
};

const SUGGESTIONS = ["全量数据的急诊患者占比是多少？", "住院量最高的疾病系统是什么？", "哪家医院的出院量最高？"];

export function AgentSidebar() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { id: 0, role: "assistant", content: "你好，我可以基于当前住院数据回答医院运营、患者结构、急诊、疾病和费用相关问题。" },
  ]);
  const nextId = useRef(1);

  const submit = async (event?: FormEvent, prompt = input) => {
    event?.preventDefault();
    const message = prompt.trim();
    if (!message || sending) return;

    const assistantMessageId = nextId.current++;
    setMessages(current => [
      ...current,
      { id: nextId.current++, role: "user", content: message },
      { id: assistantMessageId, role: "assistant", content: "" },
    ]);
    setInput("");
    setSending(true);
    try {
      await streamAgentMessage(message, {
        onDelta: text => setMessages(current => current.map(item => item.id === assistantMessageId
          ? { ...item, content: item.content + text }
          : item)),
        onToolCalls: toolCalls => setMessages(current => current.map(item => item.id === assistantMessageId
          ? { ...item, toolCalls }
          : item)),
      });
    } catch (error) {
      const toolCalls = error instanceof Error && "toolCalls" in error
        ? (error.toolCalls as AgentToolCall[])
        : [];
      setMessages(current => current.map(item => item.id === assistantMessageId
        ? { ...item, content: error instanceof Error ? error.message : "暂时无法连接 AI 分析服务，请稍后重试。", toolCalls }
        : item));
    } finally {
      setSending(false);
    }
  };

  return <>
    <button className="agent-trigger" onClick={() => setOpen(true)} aria-label="打开 AI 数据助手" title="AI 数据助手">
      <Bot size={21}/><span>AI 助手</span>
    </button>
    <aside className={`agent-sidebar ${open ? "is-open" : ""}`} aria-hidden={!open}>
      <header className="agent-head">
        <div><Sparkles size={17}/><div><strong>数据分析助手</strong><small>基于平台汇总数据</small></div></div>
        <button onClick={() => setOpen(false)} aria-label="关闭 AI 助手" title="关闭"><X size={18}/></button>
      </header>
      <div className="agent-messages" aria-live="polite">
        {messages.map(message => <article className={`agent-message ${message.role}`} key={message.id}>
          {message.role === "assistant" && <Bot size={15}/>}<div><p>{message.content}</p>{message.toolCalls?.map(tool => <span className={`agent-tool ${tool.status}`} key={`${message.id}-${tool.name}`}><Wrench size={11}/>{tool.name}</span>)}</div>
        </article>)}
        {sending && <article className="agent-message assistant"><LoaderCircle className="agent-spin" size={15}/><div><p>正在调用数据分析工具...</p></div></article>}
      </div>
      <div className="agent-suggestions">
        <span>推荐提问</span>{SUGGESTIONS.map(suggestion => <button disabled={sending} key={suggestion} onClick={() => submit(undefined, suggestion)}>{suggestion}<ChevronDown size={12}/></button>)}
      </div>
      <form className="agent-input" onSubmit={event => submit(event)}>
        <textarea value={input} onChange={event => setInput(event.target.value)} placeholder="请输入数据分析问题" maxLength={500} rows={2}/>
        <button disabled={!input.trim() || sending} aria-label="发送问题" title="发送"><Send size={16}/></button>
      </form>
    </aside>
    {open && <button className="agent-backdrop" onClick={() => setOpen(false)} aria-label="关闭 AI 助手"/>}
  </>;
}
